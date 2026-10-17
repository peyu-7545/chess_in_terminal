from enum import Enum

import sys

class ANSI_SGR:

    _CODES = {
        "reset": "0",
        "bold": "1",

        "black": "30", "red": "31", "green": "32", "yellow": "33",
        "blue": "34", "magenta": "35", "cyan": "36", "white": "37",

        "bg_black": "40", "bg_red": "41", "bg_green": "42", "bg_yellow": "43",
        "bg_blue": "44", "bg_magenta": "45", "bg_cyan": "46", "bg_white": "47"
    }

    def __init__(self):
        self.support_ansi = sys.stdout.isatty()

    def __getattr__(self, name):
        if not self.support_ansi:
            return ""

        if name not in self._CODES:
            return ""

        return "\033[" + self._CODES[name] + "m"

ansi = ANSI_SGR()

board = [
    [-4, -2, -3, -5, -6, -3, -2, -4],
    [-1, -1, -1, -1, -1, -1, -1, -1],
    [-0, -0, -0, -0, -0, -0, -0, -0],
    [-0, -0, -0, -0, -0, -0, -0, -0],
    [+0, +0, +0, +0, +0, +0, +0, +0],
    [+0, +0, +0, +0, +0, +0, +0, +0],
    [+1, +1, +1, +1, +1, +1, +1, +1],
    [+4, +2, +3, +5, +6, +3, +2, +4],
]


def in_board(i, j):
    return 0 <= i and i < 8 and 0 <= j and j < 8


# 探索する範囲, 伸ばす最大距離, 条件(距離の2乗)
def symmetry_piece_reachable(max_dist, cond):
    def fn(i, j, moving_piece):
        result = []

        for di in range(-2, 3):
            for dj in range(-2, 3):

                if di * di + dj * dj in cond:
                    for dist in range(1, max_dist + 1):
                        ni = i + di * dist
                        nj = j + dj * dist

                        if not in_board(ni, nj):
                            # 盤外
                            break

                        piece = id_to_piece[board[ni][nj]]

                        # 自分の駒があるなら進めないので終了
                        if piece is not None and piece.color() == moving_piece.color():
                            break

                        result.append((ni, nj))

                        # 相手の駒があるなら次へ進めないので終了
                        if piece is not None and piece.color() != moving_piece.color():
                            break

        return result

    return fn


def pawn_reachable(i, j, moving_piece):
    result = []

    forward = -1 if moving_piece.color() == Color.White else 1

    # 直進
    for dist in range(1, (1 if moving_piece.moved else 2) + 1):
        ni = i + forward * dist
        nj = j

        if not in_board(ni, nj):
            # 盤外
            continue

        if id_to_piece[board[ni][nj]] is None:
            # 何もなければ直進
            result.append((ni, nj))

    for dj in [-1, 1]:
        ni = i + forward
        nj = j + dj

        if not in_board(ni, nj):
            # 盤外
            continue

        forward_piece = id_to_piece[board[ni][nj]]

        if (
            forward_piece is not None
            and forward_piece.color().opponent() == moving_piece.color()
        ):
            # 敵がいれば取って移動できる
            result.append((ni, nj))

    return result


def coord_to_index(rank, file):
    return (8 - int(rank), ord(file) - ord("a"))


def index_to_coord(i, j):
    return chr(ord("a") + j) + str(8 - i)


class Piece:
    def __init__(self, char, point, reachable, id):
        self.char = char
        self.point = point
        self.reachable = reachable
        self.id = id
        self.moved = False

    def color(self):
        return Color.White if self.char.isupper() else Color.Black


king_reachable = symmetry_piece_reachable(1, [1, 2])
queen_reachable = symmetry_piece_reachable(8, [1, 2])
rook_reachable = symmetry_piece_reachable(8, [1])
bishop_reachable = symmetry_piece_reachable(8, [2])
knight_reachable = symmetry_piece_reachable(1, [5])

id_to_piece = {
    -6: Piece("k", float("inf"), king_reachable, -6),
    -5: Piece("q", 9.0, queen_reachable, -5),
    -4: Piece("r", 5.0, rook_reachable, -4),
    -3: Piece("b", 3.0, bishop_reachable, -3),
    -2: Piece("n", 3.0, knight_reachable, -2),
    -1: Piece("p", 1.0, pawn_reachable, -1),
     0: None,
    +1: Piece("P", 1.0, pawn_reachable, +1),
    +2: Piece("N", 3.0, knight_reachable, +2),
    +3: Piece("B", 3.0, bishop_reachable, +3),
    +4: Piece("R", 5.0, rook_reachable, +4),
    +5: Piece("Q", 9.0, queen_reachable, +5),
    +6: Piece("K", float("inf"), king_reachable, +6),
}


class Color(Enum):
    White = 1
    Black = 2

    def opponent(self):
        return Color.Black if self == Color.White else Color.White

reachable_tiles = []

def render():

    print("")
    print(" abcdefgh")

    for i, line in enumerate(board):
        print(f"{8 - i}", end="")

        for j, piece in enumerate(line):

            if (i, j) in reachable_tiles:
                bg_color = ansi.bg_cyan
            else:
                # 白と緑の市松模様にする
                bg_color = ansi.bg_white if (i + j) % 2 == 0 else ansi.bg_green

            if piece == 0:
                char = " " if ansi.support_ansi else "."
            else:
                char = id_to_piece[piece].char

            print(bg_color + ansi.bold, end="")
            print(char, end="")
            print(ansi.reset, end="")

        print("")

    print("")


def ask_place():

    input_chars = list(input()) # ユーザーの入力を1文字ずつ分割した配列
    error = False # この関数でエラーが発生したか

    if len(input_chars) != 2:
        # 入力がちょうど2文字でないとfileとrankに分割できない
        print(f"{ansi.red}{ansi.bold}[Error] You must input just 2 letters.{ansi.reset}")
        error = True
    else:
        file, rank = input_chars

        if not (len(file) == 1 and ord("a") <= ord(file) <= ord("h")):
            # fileがaからhの間の英子文字でない
            print(f"{ansi.red}{ansi.bold}[Error] The file must be a lower alphabet between a and h.{ansi.reset}")
            error = True

        if not (rank.isdigit() and 1 <= int(rank) <= 8):
            # rankが1から8の間の数字でない
            print(f"{ansi.red}{ansi.bold}[Error] The rank must be an integer between 1 and 8.{ansi.reset}")
            error = True

    if error:
        print(f"{ansi.red}{ansi.bold}Please try again.{ansi.reset}")
        return None

    return coord_to_index(rank, file)


def game_cycle():

    global reachable_tiles

    reachable_tiles = []
    render()

    # 動かす駒を選ばせる
    print("Please select piece: ", end="")
    move_from = ask_place()

    if move_from is None:
        return False

    from_i, from_j = move_from

    selected_piece = id_to_piece[board[from_i][from_j]]

    if selected_piece is None:
        print(f"{ansi.bold}[Info] There is nothing where you selected!{ansi.reset}")
        return False

    print(f"You selected: {ansi.bold}{selected_piece.char}{ansi.reset}")

    if selected_piece.color() != turn:
        print(f"{ansi.bold}[Info] The piece that you choice is not yours!{ansi.reset}")
        return False

    reachable_tiles = selected_piece.reachable(from_i, from_j, selected_piece)

    if len(reachable_tiles) == 0:
        print(f"{ansi.bold}[Info] The piece cannot be moved anywhere!{ansi.reset}")
        return False

    render()

    print("Please select where to move: ", end="")
    move_to = ask_place()

    if move_to is None:
        return False

    to_i, to_j = move_to

    if (to_i, to_j) not in reachable_tiles:
        print(f"You cannot move it there!!")
        return False

    board[from_i][from_j] = 0
    board[to_i][to_j] = selected_piece.id

    print("")

    return True

turn = Color.White

while True:
    print(f"~~~ {turn.name}'s turn! ~~~")

    while True:
        is_success = game_cycle()

        if is_success:
            break

    turn = turn.opponent()


# TODO: reachable_tilesの背景色をcyan単色ではなく後ろのwhite/greenを透過しているような色にする