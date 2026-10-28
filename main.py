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

    def __init__(self):
        self.support_ansi = sys.stdout.isatty()

    def __getattr__(self, name: str):
        if not self.support_ansi:
            return ""

        if name not in self._CODES:
            return ""

        return "\033[" + self._CODES[name] + "m"

    _CODES = {
        "reset": "00", "bold": "01",
        "black": "30", "red": "31", "green": "32", "yellow": "33", "blue": "34", "magenta": "35", "cyan": "36", "white": "37",
        "bg_black": "40", "bg_red": "41", "bg_green": "42", "bg_yellow": "43", "bg_blue": "44", "bg_magenta": "45", "bg_cyan": "46", "bg_white": "47",
    }


class Color(Enum):
    White = 1
    Black = 2

    def opponent(self):
        return Color.Black if self == Color.White else Color.White


class Kind(Enum):
    Pawn   = 1
    Knight = 2
    Bishop = 3
    Rook   = 4
    Queen  = 5
    King   = 6

class Place:
    def __init__(self, i: int, j: int):
        self.i = i
        self.j = j

    def is_in(self):
        return 0 <= self.i and self.i < 8 and 0 <= self.j and self.j < 8

    def is_out(self):
        return not self.is_in()

    def __iter__(self):
        yield self.i
        yield self.j

    def __add__(self, other: Place):
        return Place(self.i + other.i, self.j + other.j)

    def __rmul__(self, other: int):
        return Place(other * self.i, other * self.j)


def FEN_to_array(fen: str):
    result: list[list[Piece | None]] = [[None] * 8 for _ in range(8)]

    # FENではrankはスラッシュで区切られる
    for i, line in enumerate(fen.split("/")):
        j = 0 # 左から何マス目か

        for char in line:
            if char.isdigit():
                # 連続する空マスはその長さで表される
                j += int(char)
            else:
                # 駒があるマスはアルファベットで表される
                result[i][j] = Piece(char)
                j += 1

    return result


class Game:

    # FEN形式の盤面を表す文字列を受け取ってゲームを初期化する
    def __init__(self, fen: str):

        self.data = FEN_to_array(fen)

        self.turn = Color.White

        # 直前に2マス動いたPawn
        self.can_en_passant: dict[Color, Piece | None] = {
            Color.White: None,
            Color.Black: None,
        }

        # 選択中の駒が動けるマスの集合
        self.reachable_tiles: set[ReachableResult] = set()

        # 相手のKingが入れないマスの集合
        self.coverd: dict[Color, list[list[bool]]] = {
            Color.White: [[False] * 8 for _ in range(8)],
            Color.Black: [[False] * 8 for _ in range(8)],
        }

        self.update_coverd()

    def update_coverd(self):

        self.coverd[Color.White] = [[False] * 8 for _ in range(8)]
        self.coverd[Color.Black] = [[False] * 8 for _ in range(8)]

        for i, line in enumerate(self.data):
            for j, piece in enumerate(line):

                if piece is None:
                    continue

                for x in piece.reachable(self, piece, Place(i, j)):
                    if not x.move_only:
                        self.coverd[piece.color][x.place.i][x.place.j] = True

    def get(self, x: Place):
        return self.data[x.i][x.j]

    def set(self, x: Place, y: Piece | None):
        self.data[x.i][x.j] = y

    def coord_to_index(self, rank: str, file: str):
        return Place(8 - int(rank), ord(file) - ord("a"))

    def render(self):

        print("")
        print(" abcdefgh")

        for i in range(8):
            print(f"{8 - i}", end="")

            for j in range(8):

                if any(x.place == Place(i, j) for x in self.reachable_tiles):
                    # 到達可能マス
                    bg_color = ansi.bg_blue
                else:
                    # 通常マスは白と黒(緑)の市松模様にする
                    bg_color = ansi.bg_white if (i + j) % 2 == 0 else ansi.bg_green

                piece = self.get(Place(i, j))

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

        ok = True

        if not (len(file) == 1 and ord("a") <= ord(file) <= ord("h")):
            # fileがaからhの間の英子文字でない
            printErr("[Error] The file must be a lower alphabet between a and h.")
            ok = False

        if not (rank.isdigit() and 1 <= int(rank) <= 8):
            # rankが1から8の間の数字でない
            printErr("[Error] The rank must be an integer between 1 and 8.")
            ok = False

        return self.coord_to_index(rank, file) if ok else None

    # 1ターン分の動作を行う. 正しく入力されるまで繰り返すのでエラーは起きない.
    def game_cycle(self):

        self.update_coverd()

        print(f"--- {ansi.bold}{game.turn.name}'s turn{ansi.reset} ---")
        self.render()

        while True:

            # 動かす駒を選ばせる
            print("Please select piece: ", end="")
            move_from = self.ask_place()

            if move_from is None:
                # 正しく入力されなかった場合はやり直し
                continue

            selected_piece = self.get(move_from)

            if selected_piece is None:
                # 選ばれた座標に駒がないときはエラー
                printErr("[Error] There is nothing where you selected.")
                continue

            if selected_piece.color == self.turn.opponent():
                # 相手の駒を選んだときもエラー
                printErr("[Error] The piece that you choice is not yours.")
                continue

            self.reachable_tiles = set(x for x in selected_piece.reachable(self, selected_piece, move_from) if not x.cover_only)

            if len(self.reachable_tiles) == 0:
                # どこにも動かせない
                printErr("[Error] The piece cannot move anywhere.")
                continue

            self.render()

            # 移動先のマスを選ばせる
            print(f"Please select where to move: ", end="")
            move_to = self.ask_place()

            if move_to is None:
                # 正しく入力されなかったらやり直し
                continue

            reachable_move_to = next((x for x in self.reachable_tiles if x.place == move_to), None)

            if not reachable_move_to:
                # 入力された場所に行けない場合はエラー
                printErr("[Error] You cannot move it there.")
                continue

            # 副作用を実行
            reachable_move_to.side_effect(self)

            # 移動
            self.set(move_from, None)
            self.set(move_to, selected_piece)

            # 移動済みにする
            selected_piece.moved = True

            break

        print("")

        self.turn = self.turn.opponent() # ターンを反転
        self.can_en_passant[self.turn] = None # アンパッサン可能駒を消去
        self.reachable_tiles.clear() # 到達可能駒を消去

    def play(self):
        while True:
            self.game_cycle()


class ReachableResult:

    def __init__(self, place: Place, side_effect: Callable[[Game], None] = lambda _: None, move_only: bool = False, cover_only: bool = False):
        self.place = place
        self.side_effect = side_effect
        self.move_only = move_only
        self.cover_only = cover_only


def pawn_reachable(color: Color):
    forward_direction = -1 if color == Color.White else 1

    def fn(game: Game, self: Piece, move_from: Place):
        result: set[ReachableResult] = set()

        # 直進
        for di in ([1] if self.moved else [1, 2]):

            move_to = move_from + Place(di * forward_direction, 0)

            if move_to.is_in() and game.get(move_to) is None:
                # 何もないなら進める
                if di == 1:
                    result.add(ReachableResult(move_to, move_only = True))
                else:
                    # 2マス進んだ場合は、en_passantフラグを立てる
                    def set_flag(game: Game):
                        game.can_en_passant[self.color] = self

                    result.add(ReachableResult(move_to, set_flag, move_only = True))
            else:
                # 何かあったら進めない
                break

        # 斜め前
        for dj in [-1, 1]:
            move_to = move_from + Place(forward_direction, dj)

            if move_to.is_out():
                continue

            target = game.get(move_to)

            if target is not None and target.color == self.color.opponent():
                # 敵がいるなら進める
                result.add(ReachableResult(move_to))
            else:
                result.add(ReachableResult(move_to, cover_only = True))

        # En passant
        for dj in [-1, 1]:
            move_pass = move_from + Place(0, dj)

            if not move_pass.is_in():
                continue

            target = game.get(move_pass)

            if (
                target is not None
                and target.color == self.color.opponent()
                and target == game.can_en_passant[target.color]
            ):

                # 敵がいて、かつ敵が2マス動いた直後なら進める
                move_to = move_from + Place(forward_direction, dj)

                def capture_afterimage(game: Game):
                    game.set(move_pass, None)

                result.add(ReachableResult(move_to, capture_afterimage))

        return result

    return fn


def knight_reachable(game: Game, self: Piece, move_from: Place):
    result: set[ReachableResult] = set()

    for d in [(-1, -2), (1, -2), (-2, -1), (2, -1), (-2, 1), (2, 1), (-1, 2), (1, 2)]:
        move_to = move_from + Place(*d)

        if move_to.is_out():
            continue

        target = game.get(move_to)

        if target is None or self.is_opponent(target):
            # 何もないか、敵がいるなら進める
            result.add(ReachableResult(move_to))

    return result


def bishop_reachable(game: Game, self: Piece, move_from: Place):
    result: set[ReachableResult] = set()

    for d in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
        for scale in range(1, 8):
            move_to = move_from + scale * Place(*d)

            if move_to.is_out():
                continue

            target = game.get(move_to)

            if target is None or self.is_opponent(target):
                # 何もないか、敵がいるならそのマスに進める
                result.add(ReachableResult(move_to))

            if target is not None:
                # 何かいるならそれ以上進めない
                break

    return result


def rook_reachable(game: Game, self: Piece, move_from: Place):
    result: set[ReachableResult] = set()

    for d in [(0, -1), (-1, 0), (1, 0), (0, 1)]:
        for scale in range(1, 8):
            move_to = move_from + scale * Place(*d)

            if move_to.is_out():
                continue

            target = game.get(move_to)

            if target is None or self.is_opponent(target):
                # 何もないか、敵がいるならそのマスに進める
                result.add(ReachableResult(move_to))

            if target is not None:
                # 何かいるならそれ以上進めない
                break

    return result


def queen_reachable(game: Game, self: Piece, move_from: Place):
    result: set[ReachableResult] = set()

    for d in [(-1, -1), (1, -1), (-1, 1), (1, 1), (0, -1), (-1, 0), (1, 0), (0, 1)]:
        for scale in range(1, 8):
            move_to = move_from + scale * Place(*d)

            if move_to.is_out():
                continue

            target = game.get(move_to)

            if target is None or self.is_opponent(target):
                # 何もないか、敵がいるならそのマスに進める
                result.add(ReachableResult(move_to))

            if target is not None:
                # 何かいるならそれ以上進めない
                break

    return result


def king_reachable(game: Game, self: Piece, move_from: Place):
    result: set[ReachableResult] = set()

    for d in [(-1, -1), (1, -1), (-1, 1), (1, 1), (0, -1), (-1, 0), (1, 0), (0, 1)]:
        move_to = move_from + Place(*d)

        if move_to.is_out():
            continue

        target = game.get(move_to)

        if (target is None) or self.is_opponent(target):

            if game.coverd[self.color.opponent()][move_to.i][move_to.j]:
                # 相手の駒が利いているマスには進めない
                continue

            result.add(ReachableResult(move_to))

    return result


class Piece:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.color, self.kind, self.reachable = Piece.char_to_piece[symbol]
        self.moved = False

    char_to_piece: dict[
        str,
        tuple[Color, Kind, Callable[[Game, Piece, Place], set[ReachableResult]]],
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

    def is_opponent(self, other: Piece):
        return self.color.opponent() == other.color


ansi = ANSI_SGR()

def printErr(str: str):
    print(ansi.red + ansi.bold + str + ansi.reset)

game = Game("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR")

game.play()

# coverされているマスにキングがいるなら何らかの駒を動かしてKingをcoverから外さなければならない