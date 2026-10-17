from enum import Enum
import signal
import sys

# Ctrl+Cが押されたら入力中でも強制終了する
signal.signal(signal.SIGINT, lambda *_: sys.exit(0))


# ANSI escape sequenceを直感的に扱うためのクラス
# ターミナルがANSIに対応していない場合は何もしない
class ANSI_SGR:

    _CODES = {
        "reset": "0",
        "bold": "1",
        "black": "30",
        "red": "31",
        "green": "32",
        "yellow": "33",
        "blue": "34",
        "magenta": "35",
        "cyan": "36",
        "white": "37",
        "bg_black": "40",
        "bg_red": "41",
        "bg_green": "42",
        "bg_yellow": "43",
        "bg_blue": "44",
        "bg_magenta": "45",
        "bg_cyan": "46",
        "bg_white": "47",
    }

    def __init__(self):
        self.support_ansi = sys.stdout.isatty()

    def __getattr__(self, name):
        if not self.support_ansi:
            return ""

        if name not in self._CODES:
            return ""

        return "\033[" + self._CODES[name] + "m"


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
                        if not board.is_in(ni, nj):
                            break

                        piece = board.get(ni, nj)

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

    forward_direction = -1 if moving_piece.color() == Color.White else 1
    move_range = [1] if moving_piece.moved else [1, 2]

    # 直進
    for dist in move_range:
        ni = i + forward_direction * dist
        nj = j

        # 盤外へは移動できない
        if not board.is_in(ni, nj):
            continue

        if board.get(ni, nj) is None:
            # 何もなければ直進
            result.append((ni, nj))

    # 駒を取るとき
    for dj in [-1, 1]:
        ni = i + forward_direction
        nj = j + dj

        # 盤外へは移動できない
        if not board.is_in(ni, nj):
            continue

        forward_piece = board.get(ni, nj)

        if forward_piece is not None and forward_piece.color() == moving_piece.color().opponent():
            # 敵がいれば取って移動できる
            result.append((ni, nj))

    return result


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


class Piece:
    def __init__(self, char, point, reachable):
        self.char = char
        self.point = point
        self.reachable = reachable
        self.moved = False

    def color(self):
        # 大文字は白, 小文字は黒
        return Color.White if self.char.isupper() else Color.Black


class Board:
    def __init__(self, data):
        for i, line in enumerate(data):
            for j, id in enumerate(line):
                if id == 0:
                    data[i][j] = None
                else:
                    data[i][j] = Piece(*id_to_piece[id])

        self.data = data

    def is_in(self, i, j):
        return 0 <= i and i < 8 and 0 <= j and j < 8

    def get(self, i, j):
        return self.data[i][j]

    def set(self, i, j, x):
        self.data[i][j] = x

    def index_to_coord(self, i, j):
        return chr(ord("a") + j) + str(8 - i)

    def coord_to_index(self, rank, file):
        return (8 - int(rank), ord(file) - ord("a"))


class Color(Enum):
    White = 1
    Black = 2

    def opponent(self):
        return Color.Black if self == Color.White else Color.White


def render():

    print("")
    print(" abcdefgh")

    for i in range(8):
        print(f"{8 - i}", end="")

        for j in range(8):

            # 市松模様になるように色を決める
            if (i, j) in reachable_tiles:
                # 到達可能マスなら水色系
                bg_color = ansi.bg_cyan if (i + j) % 2 == 0 else ansi.bg_blue
            else:
                # 通常マスなら白と黒
                bg_color = ansi.bg_white if (i + j) % 2 == 0 else ansi.bg_green

            piece = board.get(i, j)

            if piece is None:
                char = " " if ansi.support_ansi else "."
            else:
                char = piece.char

            print(bg_color + ansi.bold, end="")
            print(char, end="")
            print(ansi.reset, end="")

        print("")

    print("")


# ユーザーに標準入力からマスの座標を入力させる
def ask_place():

    input_chars = list(input())  # ユーザーの入力を1文字ずつ分割した配列

    file = ""
    rank = ""

    if len(input_chars) != 2:
        # 入力がちょうど2文字でないとfileとrankに分割できない
        printErr("[Error] You must input just 2 letters.")
        return None
    
    file, rank = input_chars

    if not (len(file) == 1 and ord("a") <= ord(file) <= ord("h")):
        # fileがaからhの間の英子文字でない
        printErr("[Error] The file must be a lower alphabet between a and h.")
        return None

    if not (rank.isdigit() and 1 <= int(rank) <= 8):
        # rankが1から8の間の数字でない
        printErr("[Error] The rank must be an integer between 1 and 8.")
        return None

    return board.coord_to_index(rank, file)


# 1ターン分の動作を行う. 最後まで実行できたらTrueを返し, 不正な入力などで失敗したらFalseを返す.
def game_cycle():

    global reachable_tiles

    reachable_tiles = []
    render()

    # 動かす駒を選ばせる
    print("Please select piece: ", end="")
    move_from = ask_place()

    # 不正な入力だった場合
    if move_from is None:
        return False

    from_i, from_j = move_from
    selected_piece = board.get(from_i, from_j)

    # 選ばれた座標に駒がない
    if selected_piece is None:
        printErr("[Error] There is nothing where you selected.")
        return False

    print(f"You selected: {ansi.bold}{selected_piece.char}{ansi.reset}")

    # 相手の駒を選んだ場合も終了
    if selected_piece.color() == turn.opponent():
        printErr("[Error] The piece that you choice is not yours.")
        return False

    reachable_tiles = selected_piece.reachable(from_i, from_j, selected_piece)

    # 動かせる先がない
    if len(reachable_tiles) == 0:
        printErr("[Error] The piece cannot move anywhere.")
        return False

    render()

    print(f"Please select where to move: ", end="")
    move_to = ask_place()

    if move_to is None:
        return False

    to_i, to_j = move_to

    if (to_i, to_j) not in reachable_tiles:
        printErr("[Error] You cannot move it there.")
        return False

    board.set(from_i, from_j, None)
    board.set(to_i, to_j, selected_piece)

    selected_piece.moved = True

    print("")

    return True


ansi = ANSI_SGR()
data = [
    [-4, -2, -3, -5, -6, -3, -2, -4],
    [-1, -1, -1, -1, -1, -1, -1, -1],
    [-0, -0, -0, -0, -0, -0, -0, -0],
    [-0, -0, -0, -0, -0, -0, -0, -0],
    [+0, +0, +0, +0, +0, +0, +0, +0],
    [+0, +0, +0, +0, +0, +0, +0, +0],
    [+1, +1, +1, +1, +1, +1, +1, +1],
    [+4, +2, +3, +5, +6, +3, +2, +4],
]

board = Board(data)
reachable_tiles = []

turn = Color.White

def printErr(str):
    print(ansi.red + ansi.bold + str + ansi.reset)

def cleanup():
    print("\n" * 100)

while True:

    print(f"--- {ansi.bold}{turn.name}'s turn{ansi.reset} ---")

    while True:
        is_success = game_cycle()

        if is_success:
            break

    turn = turn.opponent()

    cleanup()