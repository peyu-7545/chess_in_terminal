from __future__ import annotations
from collections.abc import Callable
from enum import Enum
import signal
import sys

# Ctrl+Cが押されたら入力中でも強制終了する
signal.signal(signal.SIGINT, lambda _signum, _frame: sys.exit(0))


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

    def __getattr__(self, name: str):
        if not self.support_ansi:
            return ""

        if name not in self._CODES:
            return ""

        return "\033[" + self._CODES[name] + "m"


class Color(Enum):
    White = 1
    Black = 2

    def opponent(self):
        return Color.Black if self == Color.White else Color.White


class Kind(Enum):
    Pawn = 1
    Knight = 2
    Bishop = 3
    Rook = 4
    Queen = 5
    King = 6


class Game:
    def __init__(self, fen: str):
        self.data: list[list[Piece | None]] = [[None] * 8 for _ in range(8)]

        # FENではrankはスラッシュで区切られる
        for i, line in enumerate(fen.split("/")):
            j = 0

            for char in line:

                # 連続する何もないマスはその長さで表される
                if char.isdigit():
                    j += int(char)
                else:
                    self.data[i][j] = Piece(char, *char_to_piece[char])
                    j += 1

        self.turn = Color.White

    def is_in(self, i: int, j: int):
        return 0 <= i and i < 8 and 0 <= j and j < 8

    def get(self, i: int, j: int):
        return self.data[i][j]

    def set(self, i: int, j: int, x: Piece | None):
        self.data[i][j] = x

    def coord_to_index(self, rank: str, file: str):
        return (8 - int(rank), ord(file) - ord("a"))

    # 直前に2マス動いた駒
    can_en_passant: dict[Color, Piece | None] = {
        Color.White: None,
        Color.Black: None,
    }

    # 選択中の駒が動ける領域
    reachable_tiles: dict[Tile, ReachableResult] = {}

    def render(self):

        print("")
        print(" abcdefgh")

        for i in range(8):
            print(f"{8 - i}", end="")

            for j in range(8):

                # 市松模様になるように背景色を決める
                if any(x == (i, j) for x in self.reachable_tiles.keys()):
                    # 到達可能マスなら水色系
                    bg_color = ansi.bg_cyan if (i + j) % 2 == 0 else ansi.bg_blue
                else:
                    # 通常マスなら白と黒
                    bg_color = ansi.bg_white if (i + j) % 2 == 0 else ansi.bg_green

                piece = self.get(i, j)

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
    def ask_place(self):

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

        return self.coord_to_index(rank, file)

    # 1ターン分の動作を行う. 最後まで実行できたらTrueを返し, 不正な入力などで失敗したらFalseを返す.
    def game_cycle(self):

        self.can_en_passant[self.turn] = None
        self.reachable_tiles = {}

        self.render()

        # 動かす駒を選ばせる
        print("Please select piece: ", end="")
        move_from = self.ask_place()

        # 不正な入力だった場合
        if move_from is None:
            return False

        from_i, from_j = move_from
        selected_piece = self.get(from_i, from_j)

        # 選ばれた座標に駒がないときはエラー
        if selected_piece is None:
            printErr("[Error] There is nothing where you selected.")
            return False

        print(f"You selected: {ansi.bold}{selected_piece.char}{ansi.reset}")

        # 相手の駒を選んだ場合もエラー
        if selected_piece.color == self.turn.opponent():
            printErr("[Error] The piece that you choice is not yours.")
            return False

        self.reachable_tiles = selected_piece.reachable(
            self, selected_piece, from_i, from_j
        )

        # 動かせる先がない
        if len(self.reachable_tiles) == 0:
            printErr("[Error] The piece cannot move anywhere.")
            return False

        self.render()

        print(f"Please select where to move: ", end="")
        move_to = self.ask_place()

        if move_to is None:
            return False

        to_i, to_j = move_to

        reachable_move_to = [x for x in self.reachable_tiles.items() if x[0] == move_to]

        if len(reachable_move_to) == 0:
            printErr("[Error] You cannot move it there.")
            return False

        reachable_move_to[0][1].side_effect(self)

        self.set(from_i, from_j, None)
        self.set(to_i, to_j, selected_piece)

        selected_piece.moved = True

        print("")

        return True


class Piece:

    def __init__(
        self,
        char: str,
        kind: Kind,
        color: Color,
        reachable: Callable[[Game, Piece, int, int], dict[Tile, ReachableResult]],
    ):
        self.char = char
        self.kind = kind
        self.color = color
        self.reachable = reachable
        self.moved = False


class ReachableResult:
    def __init__(self, side_effect: Callable[[Game], None] = lambda _: None):
        self.side_effect = side_effect


def pawn_reachable(color: Color):
    forward_direction = -1 if color == Color.White else 1

    def fn(game: Game, self: Piece, i: int, j: int):
        result: dict[Tile, ReachableResult] = {}

        # 直進
        for di in [1] if self.moved else [1, 2]:
            ni = i + di * forward_direction
            nj = j

            if game.is_in(ni, nj) and game.get(ni, nj) is None:
                # 何もないなら進める
                if di == 1:
                    result[(ni, nj)] = ReachableResult()
                else:
                    # 2マス進んだ場合は、en_passantフラグを立てる
                    def set_flag(game: Game):
                        game.can_en_passant[self.color] = self

                    result[(ni, nj)] = ReachableResult(set_flag)
            else:
                # 何かあったら進めない
                break

        # 斜め前
        for dj in [-1, 1]:
            ni = i + forward_direction
            nj = j + dj

            if not game.is_in(ni, nj):
                # 盤外
                continue

            target = game.get(ni, nj)

            if target is not None and target.color == self.color.opponent():
                # 敵がいるなら進める
                result[(ni, nj)] = ReachableResult()

        # En passant
        for dj in [-1, 1]:
            mi, mj = (i, j + dj)

            if not game.is_in(mi, mj):
                continue

            target = game.get(mi, mj)

            if (
                target is not None
                and target.color == self.color.opponent()
                and target == game.can_en_passant[target.color]
            ):

                # 敵がいて、かつ敵が2マス動いた直後なら進める
                ni, nj = (mi + forward_direction, mj)

                def capture_afterimage(game: Game):
                    game.set(mi, mj, None)

                result[(ni, nj)] = ReachableResult(capture_afterimage)

        return result

    return fn


def knight_reachable(game: Game, self: Piece, i: int, j: int):
    result: dict[Tile, ReachableResult] = {}

    for di, dj in [
        (-1, -2),
        (1, -2),
        (-2, -1),
        (2, -1),
        (-2, 1),
        (2, 1),
        (-1, 2),
        (1, 2),
    ]:
        ni, nj = (i + di, j + dj)

        if not game.is_in(ni, nj):
            # 盤外
            continue

        target = game.get(ni, nj)

        if target is None or target.color == self.color.opponent():
            # 何もないか、敵がいるなら進める
            result[(ni, nj)] = ReachableResult()

    return result


def bishop_reachable(game: Game, self: Piece, i: int, j: int):
    result: dict[Tile, ReachableResult] = {}

    for di, dj in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
        for scale in range(1, 8):
            ni, nj = (i + di * scale, j + dj * scale)

            if not game.is_in(ni, nj):
                # 盤外
                continue

            target = game.get(ni, nj)

            if target is None or target.color == self.color.opponent():
                # 何もないか、敵がいるならそのマスに進める
                result[(ni, nj)] = ReachableResult()

            if target is not None:
                # 何かいるならそれ以上進めない
                break

    return result


def rook_reachable(game: Game, self: Piece, i: int, j: int):
    result: dict[Tile, ReachableResult] = {}

    for di, dj in [(0, -1), (-1, 0), (1, 0), (0, 1)]:
        for scale in range(1, 8):
            ni, nj = (i + di * scale, j + dj * scale)

            if not game.is_in(ni, nj):
                # 盤外
                continue

            target = game.get(ni, nj)

            if target is None or target.color == self.color.opponent():
                # 何もないか、敵がいるならそのマスに進める
                result[(ni, nj)] = ReachableResult()

            if target is not None:
                # 何かいるならそれ以上進めない
                break

    return result


def queen_reachable(game: Game, self: Piece, i: int, j: int):
    result: dict[Tile, ReachableResult] = {}

    for di, dj in [
        (-1, -1),
        (1, -1),
        (-1, 1),
        (1, 1),
        (0, -1),
        (-1, 0),
        (1, 0),
        (0, 1),
    ]:
        for scale in range(1, 8):
            ni, nj = (i + di * scale, j + dj * scale)

            if not game.is_in(ni, nj):
                # 盤外
                continue

            target = game.get(ni, nj)

            if target is None or target.color == self.color.opponent():
                # 何もないか、敵がいるならそのマスに進める
                result[(ni, nj)] = ReachableResult()

            if target is not None:
                # 何かいるならそれ以上進めない
                break

    return result


def king_reachable(game: Game, self: Piece, i: int, j: int):
    result: dict[Tile, ReachableResult] = {}

    for di, dj in [
        (-1, -1),
        (1, -1),
        (-1, 1),
        (1, 1),
        (0, -1),
        (-1, 0),
        (1, 0),
        (0, 1),
    ]:
        ni, nj = (i + di, j + dj)

        if not game.is_in(ni, nj):
            # 盤外
            continue

        target = game.get(ni, nj)

        if target is None or target.color == self.color.opponent():
            # 何もないか、敵がいるならそのマスに進める
            result[(ni, nj)] = ReachableResult()

    return result


char_to_piece: dict[
    str,
    tuple[Kind, Color, Callable[[Game, Piece, int, int], dict[Tile, ReachableResult]]],
] = {
    "P": (Kind.Pawn, Color.White, pawn_reachable(Color.White)),
    "N": (Kind.Knight, Color.White, knight_reachable),
    "B": (Kind.Bishop, Color.White, bishop_reachable),
    "R": (Kind.Rook, Color.White, rook_reachable),
    "Q": (Kind.Queen, Color.White, queen_reachable),
    "K": (Kind.King, Color.White, king_reachable),
    "p": (Kind.Pawn, Color.Black, pawn_reachable(Color.Black)),
    "n": (Kind.Knight, Color.Black, knight_reachable),
    "b": (Kind.Bishop, Color.Black, bishop_reachable),
    "r": (Kind.Rook, Color.Black, rook_reachable),
    "q": (Kind.Queen, Color.Black, queen_reachable),
    "k": (Kind.King, Color.Black, king_reachable),
}

Tile = tuple[int, int]

ansi = ANSI_SGR()

game = Game("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR")


def printErr(str: str):
    print(ansi.red + ansi.bold + str + ansi.reset)


def cleanup():
    print("\n" * 100)


while True:

    print(f"--- {ansi.bold}{game.turn.name}'s turn{ansi.reset} ---")

    while True:
        is_success = game.game_cycle()

        if is_success:
            break

    game.turn = game.turn.opponent()

    cleanup()
