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
        "reset":      "00",
        "bold":       "01",
        "black":      "30",
        "red":        "31",
        "green":      "32",
        "yellow":     "33",
        "blue":       "34",
        "magenta":    "35",
        "cyan":       "36",
        "white":      "37",
        "bg_black":   "40",
        "bg_red":     "41",
        "bg_green":   "42",
        "bg_yellow":  "43",
        "bg_blue":    "44",
        "bg_magenta": "45",
        "bg_cyan":    "46",
        "bg_white":   "47",
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

    # FEN形式の盤面を表す文字列を受け取ってゲームを初期化する
    def __init__(self, fen: str):
        self.data: list[list[Piece | None]] = [[None] * 8 for _ in range(8)]

        # FENではrankはスラッシュで区切られる
        for i, line in enumerate(fen.split("/")):
            j = 0  # 何マス目か

            for char in line:
                if char.isdigit():
                    # 連続する空マスはその長さで表される
                    j += int(char)
                else:
                    # 駒があるマスはアルファベットで表される
                    self.data[i][j] = Piece(char)
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
    reachable_tiles: dict[tuple[int, int], ReachableResult] = {}

    def render(self):

        print("")
        print(" abcdefgh")

        for i in range(8):
            print(f"{8 - i}", end="")

            for j in range(8):

                if any(x == (i, j) for x in self.reachable_tiles.keys()):
                    # 到達可能マス
                    bg_color = ansi.bg_blue
                else:
                    # 通常マスは白と黒(緑)の市松模様にする
                    bg_color = ansi.bg_white if (i + j) % 2 == 0 else ansi.bg_green

                piece = self.get(i, j)

                if piece is None:
                    char = " " if ansi.support_ansi else "."
                else:
                    char = piece.symbol

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

    # 1ターン分の動作を行う. 正しく入力されるまで繰り返すのでエラーは起きない.
    def game_cycle(self):

        print(f"--- {ansi.bold}{game.turn.name}'s turn{ansi.reset} ---")
        self.render()

        while True:

            # 動かす駒を選ばせる
            print("Please select piece: ", end="")
            move_from = self.ask_place()

            if move_from is None:
                # 正しく入力されなかった場合はやり直し
                continue

            from_i, from_j = move_from
            selected_piece = self.get(from_i, from_j)

            if selected_piece is None:
                # 選ばれた座標に駒がないときはエラー
                printErr("[Error] There is nothing where you selected.")
                continue

            if selected_piece.color == self.turn.opponent():
                # 相手の駒を選んだときもエラー
                printErr("[Error] The piece that you choice is not yours.")
                continue

            self.reachable_tiles = selected_piece.reachable(self, selected_piece, from_i, from_j)

            if len(self.reachable_tiles) == 0:
                # どこにも動かせない
                printErr("[Error] The piece cannot move anywhere.")
                continue

            break

        self.render()

        while True:

            # 移動先のマスを選ばせる
            print(f"Please select where to move: ", end="")
            move_to = self.ask_place()

            if move_to is None:
                # 正しく入力されなかったらやり直し
                continue

            to_i, to_j = move_to

            reachable_move_to = next((x for x in self.reachable_tiles.items() if x[0] == move_to), None)

            if not reachable_move_to:
                # 入力された場所に行けない場合はエラー
                printErr("[Error] You cannot move it there.")
                continue

            reachable_move_to[1].side_effect(self)

            self.set(from_i, from_j, None)
            self.set(to_i, to_j, selected_piece)

            selected_piece.moved = True

            break

        print("")

        self.turn = self.turn.opponent() # ターンを反転
        self.can_en_passant[self.turn] = None # アンパッサン可能駒を消去
        self.reachable_tiles = {} # 到達可能駒を消去

    def play(self):
        while True:
            self.game_cycle()


class ReachableResult:
    def __init__(self, side_effect: Callable[[Game], None] = lambda _: None):
        self.side_effect = side_effect


def pawn_reachable(color: Color):
    forward_direction = -1 if color == Color.White else 1

    def fn(game: Game, self: Piece, i: int, j: int):
        result: dict[tuple[int, int], ReachableResult] = {}

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
    result: dict[tuple[int, int], ReachableResult] = {}

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
    result: dict[tuple[int, int], ReachableResult] = {}

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
    result: dict[tuple[int, int], ReachableResult] = {}

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
    result: dict[tuple[int, int], ReachableResult] = {}

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
    result: dict[tuple[int, int], ReachableResult] = {}

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


class Piece:
    
    char_to_piece: dict[
        str,
        tuple[
            Color,
            Kind,
            Callable[[Game, Piece, int, int], dict[tuple[int, int], ReachableResult]],
        ],
    ] = {
        "P": (Color.White, Kind.Pawn,   pawn_reachable(Color.White)),
        "N": (Color.White, Kind.Knight, knight_reachable),
        "B": (Color.White, Kind.Bishop, bishop_reachable),
        "R": (Color.White, Kind.Rook,   rook_reachable),
        "Q": (Color.White, Kind.Queen,  queen_reachable),
        "K": (Color.White, Kind.King,   king_reachable),
        "p": (Color.Black, Kind.Pawn,   pawn_reachable(Color.Black)),
        "n": (Color.Black, Kind.Knight, knight_reachable),
        "b": (Color.Black, Kind.Bishop, bishop_reachable),
        "r": (Color.Black, Kind.Rook,   rook_reachable),
        "q": (Color.Black, Kind.Queen,  queen_reachable),
        "k": (Color.Black, Kind.King,   king_reachable),
    }

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.color, self.kind, self.reachable = Piece.char_to_piece[symbol]
        self.moved = False


ansi = ANSI_SGR()

def printErr(str: str):
    print(ansi.red + ansi.bold + str + ansi.reset)

game = Game("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR")

game.play()