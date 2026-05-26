import pygame as pg
import random
import sys
import os

pg.init()
WIDTH, HEIGHT = 900, 600
screen = pg.display.set_mode((WIDTH, HEIGHT))
pg.display.set_caption("大富豪（完全版）")
clock = pg.time.Clock()

font = pg.font.SysFont("meiryo", 24)

# -------------------------
# カードの準備
# -------------------------
suits = ["♠", "♥", "♦", "♣"]
ranks = list(range(3, 16))  # 3〜2（15を2とする）
rank_name = {11: "J", 12: "Q", 13: "K", 14: "A", 15: "2"}


def card_to_text(card):
    s, r = card
    return f"{s}{r if r <= 10 else rank_name[r]}"


def is_stronger(new_rank, base_rank, revolution):
    return new_rank > base_rank if not revolution else new_rank < base_rank


def create_deck():
    deck = [(s, r) for s in suits for r in ranks]
    random.shuffle(deck)
    return deck


def is_straight(cards):
    if len(cards) < 2:
        return False
    ranks_ = sorted(c[1] for c in cards)
    return all(ranks_[i] + 1 == ranks_[i + 1] for i in range(len(ranks_) - 1))


def find_straights(hand):
    straights = []
    hand_sorted = sorted(hand, key=lambda c: c[1])

    temp = [hand_sorted[0]]
    for i in range(1, len(hand_sorted)):
        if hand_sorted[i][1] == hand_sorted[i - 1][1] + 1:
            temp.append(hand_sorted[i])
        else:
            if len(temp) >= 2:
                straights.append(temp.copy())
            temp = [hand_sorted[i]]

    if len(temp) >= 2:
        straights.append(temp.copy())

    return straights


# -------------------------
# プレイヤーと同じ判定関数
# -------------------------
def can_play(selected, field, revolution, locked_suit):
    is_st = is_straight(selected)
    field_is_st = isinstance(field, list) and is_straight(field)

    # マーク縛り中は階段禁止
    if is_st and locked_suit is not None:
        return False

    # 場が複数枚 or 階段
    if isinstance(field, list):

        # 場が階段
        if field_is_st:
            if not is_st:
                return False
            if len(field) != len(selected):
                return False
            field_ranks = sorted(c[1] for c in field)
            max_f = field_ranks[-1]
            sel_ranks = sorted(c[1] for c in selected)
            return sel_ranks[0] == max_f + 1

        # 場が複数枚（同ランク）
        else:
            if is_st:
                return False
            ranks = [c[1] for c in selected]
            if len(set(ranks)) != 1:
                return False
            if len(field) != len(selected):
                return False
            return is_stronger(selected[0][1], field[0][1], revolution)

    # 場が1枚
    elif isinstance(field, tuple):
        if is_st:
            return False
        if len(selected) != 1:
            return False
        return is_stronger(selected[0][1], field[1], revolution)

    # 場が流れている
    else:
        if not is_st and len(selected) >= 2:
            ranks = [c[1] for c in selected]
            if len(set(ranks)) != 1:
                return False
        return True


# -------------------------
# CPU が出せる全ての手を生成
# -------------------------
def generate_all_moves(hand):
    moves = []

    # 1枚
    for c in hand:
        moves.append([c])

    # 複数枚
    groups = {}
    for c in hand:
        groups.setdefault(c[1], []).append(c)
    for g in groups.values():
        if len(g) >= 2:
            moves.append(g.copy())

    # 階段
    for s in find_straights(hand):
        moves.append(s)

    return moves


# -------------------------
# CPU（プレイヤーと完全同じ判定）
# -------------------------
def cpu_play(hand, field, revolution, locked_suit):
    moves = generate_all_moves(hand)

    legal = []
    for m in moves:
        if can_play(m, field, revolution, locked_suit):
            legal.append(m)

    if not legal:
        return None

    # CPU 戦略：最弱の手を出す（革命中は最強）
    if not revolution:
        best = min(legal, key=lambda mv: max(c[1] for c in mv))
    else:
        best = max(legal, key=lambda mv: max(c[1] for c in mv))

    # 手札から削除
    for c in best:
        hand.remove(c)

    return best if len(best) > 1 else best[0]


# -------------------------
# カード描画
# -------------------------
def draw_card(x, y, card):
    s, r = card
    rect = pg.Rect(x, y, 60, 90)

    pg.draw.rect(screen, (255, 255, 255), rect)
    pg.draw.rect(screen, (0, 0, 0), rect, 3)

    color = (0, 0, 0) if s in ["♠", "♣"] else (200, 0, 0)
    rank_text = str(r) if r <= 10 else rank_name[r]

    text1 = font.render(f"{s}{rank_text}", True, color)
    screen.blit(text1, (x + 3, y + 2))

    text2 = font.render(f"{s}{rank_text}", True, color)
    tw, th = text2.get_size()
    screen.blit(text2, (x + 60 - tw - 3, y + 90 - th - 2))

    return rect


def draw_player_hand(hand, selected_cards):
    rects = []
    for i, card in enumerate(hand):
        row = i // 10
        col = i % 10
        x = 50 + col * 70
        y = 400 + row * 100

        if card in selected_cards:
            y -= 20

        rect = draw_card(x, y, card)
        rects.append((rect, card))
    return rects


# -------------------------
# ボタン
# -------------------------
def draw_pass_button():
    rect = pg.Rect(700, 450, 150, 60)
    pg.draw.rect(screen, (200, 50, 50), rect)
    pg.draw.rect(screen, (255, 255, 255), rect, 3)
    screen.blit(font.render("PASS", True, (255, 255, 255)), (740, 470))
    return rect


def draw_play_button():
    rect = pg.Rect(700, 380, 150, 60)
    pg.draw.rect(screen, (50, 150, 50), rect)
    pg.draw.rect(screen, (255, 255, 255), rect, 3)
    screen.blit(font.render("出す", True, (255, 255, 255)), (740, 400))
    return rect


# -------------------------
# リザルト画面
# -------------------------
rank_name_list = ["あなた", "CPU1", "CPU2", "CPU3"]


def show_result_screen(finished):
    running = True

    if finished[0] == 0:
        result_text = "YOU WIN!"
        result_color = (255, 215, 0)
    else:
        result_text = "YOU LOSE..."
        result_color = (255, 80, 80)

    while running:
        screen.fill((20, 20, 20))

        title = font.render("GAME RESULT", True, (255, 255, 255))
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 80))

        result = font.render(result_text, True, result_color)
        screen.blit(result, (WIDTH // 2 - result.get_width() // 2, 140))

        y = 220
        for i, p in enumerate(finished):
            text = font.render(f"{i+1}位：{rank_name_list[p]}", True, (255, 255, 255))
            screen.blit(text, (WIDTH // 2 - text.get_width() // 2, y))
            y += 50

        ok_rect = pg.Rect(WIDTH // 2 - 75, 500, 150, 50)
        pg.draw.rect(screen, (80, 80, 200), ok_rect)
        pg.draw.rect(screen, (255, 255, 255), ok_rect, 3)
        screen.blit(font.render("OK", True, (255, 255, 255)), (WIDTH // 2 - 20, 515))

        pg.display.update()

        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg.quit()
                sys.exit()
            if event.type == pg.MOUSEBUTTONDOWN:
                if ok_rect.collidepoint(event.pos):
                    running = False


# -------------------------
# メインゲーム
# -------------------------
def play_game():
    deck = create_deck()

    hands = [
        deck[0:13],
        deck[13:26],
        deck[26:39],
        deck[39:52],
    ]

    for h in hands:
        h.sort(key=lambda c: c[1])

    field = None
    locked_suit = None
    message = ""
    finished = []
    selected_cards = []
    revolution = False

    turn = 0
    last_player = 0
    pass_count = 0

    while True:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg.quit()
                sys.exit()

            if turn == 0 and event.type == pg.MOUSEBUTTONDOWN:
                mx, my = event.pos

                play_rect = draw_play_button()
                if play_rect.collidepoint(mx, my):

                    if not selected_cards:
                        message = "カードを選択してください"
                        continue

                    if not can_play(selected_cards, field, revolution, locked_suit):
                        message = "そのカードは出せません"
                        continue

                    # 出す処理
                    for c in selected_cards:
                        hands[0].remove(c)

                    field = selected_cards[0] if len(selected_cards) == 1 else selected_cards.copy()

                    # マーク縛り更新
                    new_suit = selected_cards[0][0]
                    if locked_suit is None:
                        locked_suit = new_suit
                    else:
                        if new_suit != locked_suit:
                            locked_suit = None

                    # 革命判定（4枚出し）
                    if len(selected_cards) == 4 and not is_straight(selected_cards):
                        revolution = not revolution
                        message = "革命発動！" if revolution else "革命返し！"
                    else:
                        message = "カードを出した"

                    selected_cards.clear()
                    last_player = 0
                    pass_count = 0
                    turn = 1
                    continue

                # PASS
                pass_rect = draw_pass_button()
                if pass_rect.collidepoint(mx, my):
                    message = "あなたはパスした"
                    pass_count += 1
                    selected_cards.clear()
                    turn = 1
                    continue

                # カード選択
                rects = draw_player_hand(hands[0], selected_cards)
                for rect, card in rects:
                    if rect.collidepoint(mx, my):
                        if card in selected_cards:
                            selected_cards.remove(card)
                        else:
                            selected_cards.append(card)
                        break

        # CPUターン
        if turn != 0:

            if not hands[turn]:
                turn = (turn + 1) % 4
                continue

            pg.time.wait(300)

            card = cpu_play(hands[turn], field, revolution, locked_suit)

            if card:
                field = card

                # 革命判定
                if isinstance(card, list) and len(card) == 4 and not is_straight(card):
                    revolution = not revolution
                    message = "革命発動！" if revolution else "革命返し！"

                if isinstance(card, list):
                    text = " ".join(card_to_text(c) for c in card)
                    message = f"CPU{turn} は {text} を出した"
                else:
                    message = f"CPU{turn} は {card_to_text(card)} を出した"

                last_player = turn
                pass_count = 0

            else:
                message = f"CPU{turn} はパスした"
                pass_count += 1

            turn = (turn + 1) % 4

        # 場流し
        if pass_count >= 3:
            field = None
            locked_suit = None
            message = "場が流れた！"
            turn = last_player
            pass_count = 0

        # 上がり判定
        for i in range(4):
            if not hands[i] and i not in finished:
                finished.append(i)

        if len(finished) == 3:
            for i in range(4):
                if i not in finished:
                    finished.append(i)
                    break
            show_result_screen(finished)
            break

        # 描画
        screen.fill((0, 120, 0))

        rev_text = font.render("革命中" if revolution else "通常", True, (255, 50, 50) if revolution else (255, 255, 255))
        screen.blit(rev_text, (700, 50))

        if field:
            if isinstance(field, list):
                x = WIDTH // 2 - (len(field) * 35)
                for c in field:
                    draw_card(x, HEIGHT // 2 - 45, c)
                    x += 70
            else:
                draw_card(WIDTH // 2 - 30, HEIGHT // 2 - 45, field)

        draw_player_hand(hands[0], selected_cards)

        screen.blit(font.render(f"CPU1：{len(hands[1])}枚", True, (255, 255, 255)), (WIDTH // 2 - 80, 30))
        screen.blit(font.render(f"CPU2：{len(hands[2])}枚", True, (255, 255, 255)), (50, 150))
        screen.blit(font.render(f"CPU3：{len(hands[3])}枚", True, (255, 255, 255)), (WIDTH - 180, 150))

        draw_pass_button()
        draw_play_button()

        msg = font.render(message, True, (255, 255, 255))
        screen.blit(msg, (50, 300))

        pg.display.update()
        clock.tick(60)


# -------------------------
# 実行
# -------------------------
play_game()
