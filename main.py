from enum import Enum
import signal
import sys
# Ctrl+Cが押されたら入力中でも強制終了する
signal.signal(signal.SIGINT, lambda signum, frame: sys.exit(0))

# ANSI escape sequenceを直感的に扱うためのクラス
# ターミナルがANSIに対応していない場合は何もしない
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

def in_board(i, j):
    return 0 <= i and i < 8 and 0 <= j and j < 8


# 探索する範囲, 伸ばす最大距離, 条件(距離の2乗)
def symmetry_piece_reachable(max_dist, cond):
    def fn(i, j, moving_piece):
        result = []

        for di in [-2, -1, 0, 1, 2]:
            for dj in [-2, -1, 0, 1, 2]:

                if di * di + dj * dj in cond:
                    for dist in range(1, max_dist + 1):
                        ni = i + di * dist
                        nj = j + dj * dist

                        # 盤外へは移動できない
                        if not in_board(ni, nj):
                            break

                        piece = board[ni][nj]

                        # 自分の駒があるなら進めない
                        if piece is not None and piece.color() == moving_piece.color():
                            break

                        result.append((ni, nj))

                        # 相手の駒があるなら次へ進めない
                        if piece is not None and piece.color() != moving_piece.color():
                            break

        return result

    return fn


def pawn_reachable(i, j, moving_piece):
    result = []

    forward = -1 if moving_piece.color() == Color.White else 1

    if moving_piece.moved:
        move_range = [1]
    else:
        move_range = [1, 2]

    # 直進
    for dist in move_range:
        ni = i + forward * dist
        nj = j

        # 盤外へは移動できない
        if not in_board(ni, nj):
            break

        if board[ni][nj] is None:
            # 何もなければ直進
            result.append((ni, nj))

    for dj in [-1, 1]:
        ni = i + forward
        nj = j + dj

        if not in_board(ni, nj):
            # 盤外
            continue

        forward_piece = board[ni][nj]

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
    def __init__(self, char, point, reachable):
        self.char = char
        self.point = point
        self.reachable = reachable
        self.moved = False

    def color(self):
        return Color.White if self.char.isupper() else Color.Black


king_reachable = symmetry_piece_reachable(1, [1, 2])
queen_reachable = symmetry_piece_reachable(8, [1, 2])
rook_reachable = symmetry_piece_reachable(8, [1])
bishop_reachable = symmetry_piece_reachable(8, [2])
knight_reachable = symmetry_piece_reachable(1, [5])

id_to_piece = {
    -6: ["k", float("inf"), king_reachable],
    -5: ["q", 9.0, queen_reachable],
    -4: ["r", 5.0, rook_reachable],
    -3: ["b", 3.0, bishop_reachable],
    -2: ["n", 3.0, knight_reachable],
    -1: ["p", 1.0, pawn_reachable],
    +1: ["P", 1.0, pawn_reachable],
    +2: ["N", 3.0, knight_reachable],
    +3: ["B", 3.0, bishop_reachable],
    +4: ["R", 5.0, rook_reachable],
    +5: ["Q", 9.0, queen_reachable],
    +6: ["K", float("inf"), king_reachable],
}

initial_board_data = [
    [-4, -2, -3, -5, -6, -3, -2, -4],
    [-1, -1, -1, -1, -1, -1, -1, -1],
    [-0, -0, -0, -0, -0, -0, -0, -0],
    [-0, -0, -0, -0, -0, -0, -0, -0],
    [+0, +0, +0, +0, +0, +0, +0, +0],
    [+0, +0, +0, +0, +0, +0, +0, +0],
    [+1, +1, +1, +1, +1, +1, +1, +1],
    [+4, +2, +3, +5, +6, +3, +2, +4],
]

board = [list(map(lambda x: Piece(*id_to_piece[x]) if x != 0 else None, line)) for line in initial_board_data]

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
                bg_color = ansi.bg_cyan if (i + j) % 2 == 0 else ansi.bg_blue
            else:
                # 白と緑の市松模様にする
                bg_color = ansi.bg_white if (i + j) % 2 == 0 else ansi.bg_green

            piece = piece

            if piece is None:
                char = " " if ansi.support_ansi else "."
            else:
                char = piece.char

            print(bg_color + ansi.bold, end="")
            print(char, end="")
            print(ansi.reset, end="")

        print("")

    print("")


def ask_place():

    input_chars = list(input()) # ユーザーの入力を1文字ずつ分割した配列
    error = False # この関数でエラーが発生したか

    file = ""
    rank = ""

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

    # 選ばれなかった場合はここで終了
    if move_from is None:
        return False

    from_i, from_j = move_from

    selected_piece = board[from_i][from_j]

    # 選ばれた座標に駒がない場合も終了
    if selected_piece is None:
        print(f"{ansi.red}{ansi.bold}[Error] There is nothing where you selected.{ansi.reset}")
        return False

    print(f"You selected: {ansi.bold}{selected_piece.char}{ansi.reset}")

    # 相手の駒を選んだ場合も終了
    if selected_piece.color() == turn.opponent():
        print(f"{ansi.red}{ansi.bold}[Error] The piece that you choice is not yours.{ansi.reset}")
        return False

    reachable_tiles = selected_piece.reachable(from_i, from_j, selected_piece)

    if len(reachable_tiles) == 0:
        print(f"{ansi.red}{ansi.bold}[Error] The piece cannot be moved anywhere.{ansi.reset}")
        return False

    render()

    print(f"Please select where to move: ", end="")
    move_to = ask_place()

    if move_to is None:
        return False

    to_i, to_j = move_to

    if (to_i, to_j) not in reachable_tiles:
        print(f"{ansi.red}{ansi.bold}[Error] You cannot move it there.")
        return False

    board[from_i][from_j] = None
    board[to_i][to_j] = selected_piece

    selected_piece.moved = True

    print("")

    return True

turn = Color.White

while True:
    print(f"--- {ansi.bold}{turn.name}'s turn{ansi.reset} ---")

    while True:
        is_success = game_cycle()

        if is_success:
            break

    turn = turn.opponent()

    print('\n' * 100)