from __future__ import annotations
from collections.abc import Callable
from enum import Enum
import signal
import sys
import copy
from typing import Any

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

def printErr(err: str):
    print(ansi.red + ansi.bold + err + ansi.reset)


class Color(Enum):
    White = 1
    Black = 2

    def opponent(self):
        return Color.Black if self == Color.White else Color.White

    def is_opponent(self, other: Color):
        return self != other


class Kind(Enum):
    Pawn   = 1
    Knight = 2
    Bishop = 3
    Rook   = 4
    Queen  = 5
    King   = 6

class Vec2:
    def __init__(self, i: int, j: int):
        self.i = i
        self.j = j

    def is_in_board(self):
        return 0 <= self.i and self.i < 8 and 0 <= self.j and self.j < 8

    def is_out_board(self):
        return not self.is_in_board()

    def __add__(self, other: Vec2):
        return Vec2(self.i + other.i, self.j + other.j)

    def __rmul__(self, other: int):
        return Vec2(other * self.i, other * self.j)

    def __hash__(self):
        return hash((self.i, self.j))

    def __eq__(self, other: Any):
        if not isinstance(other, Vec2):
            return NotImplemented

        return self.i == other.i and self.j == other.j


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

        # Kingの位置
        self.king_position: dict[Color, Vec2 | None] = {
            Color.White: None,
            Color.Black: None,
        }

        # 直前に2マス動いたPawnの位置
        self.can_en_passant: dict[Color, Vec2 | None] = {
            Color.White: None,
            Color.Black: None,
        }

        # 利いているマスの集合
        self.covered: dict[Color, set[Vec2]] = {
            Color.White: set(),
            Color.Black: set(),
        }

        for i in range(8):
            for j in range(8):
                piece = self.get(Vec2(i, j))
                if (piece is not None) and piece.kind == Kind.King:
                    self.king_position[piece.color] = Vec2(i, j)

        self.update_covered()

    def update_covered(self):
        self.covered[Color.White].clear()
        self.covered[Color.Black].clear()

        for i in range(8):
            for j in range(8):
                piece = self.get(Vec2(i, j))
                if piece is None:
                    continue
                for x in piece.reachable(self, piece, Vec2(i, j)):
                    self.covered[piece.color].add(x.place)

    def get(self, x: Vec2):
        return self.data[x.i][x.j]

    def set(self, x: Vec2, y: Piece | None):
        self.data[x.i][x.j] = y

    def render(self):

        print("")
        print(" abcdefgh")

        for i in range(8):
            print(8 - i, end="")

            for j in range(8):

                # マスの色は白と緑の市松模様
                bg_color = ansi.bg_white if (i + j) % 2 == 0 else ansi.bg_green

                piece = self.get(Vec2(i, j))

                if piece is None:
                    char = " " if ansi.support_ansi else "."
                else:
                    char = piece.symbol

                print(bg_color + ansi.bold + char + ansi.reset, end="")

            print("")

        print("")

    # 1ターン分の動作を行う
    # 正しく入力されるまで繰り返すのでエラーは起きない
    def game_cycle(self):

        print(f"\n--- {ansi.bold}{self.turn.name}{ansi.reset}'s turn ---")
        self.update_covered()
        self.render()

        while True:
            if self.move(lambda: self.ask_place("Please select piece: "), lambda: self.ask_place("Please select where to move: ")):
                break

    def move(self, move_from_fn: Callable[[], Vec2 | None], move_to_fn: Callable[[], Vec2 | None]):

        if (move_from := move_from_fn()) is None:
            return False

        selected_piece = self.get(move_from)

        if selected_piece is None:
            # 選んだ場所に何もなかった
            printErr("[Error] There is nothing where you selected.")
            return False

        if selected_piece.color.is_opponent(self.turn):
            # 選んだ駒は相手の駒だった
            printErr("[Error] The piece you selected is not yours.")
            return False

        if (move_to := move_to_fn()) is None:
            return False

        reachable_tiles = selected_piece.reachable(self, selected_piece, move_from)

        # reachable_tilesの中からmove_toを探す(なければNone)
        reachable_move_to = next((x for x in reachable_tiles if x.place == move_to), None)

        if reachable_move_to is None:
            # 選ばれた場所に行けない
            printErr("[Error] You cannot move it there.")
            return False

        next_state = copy.deepcopy(self)
        
        next_state.set(move_to, next_state.get(move_from))
        next_state.set(move_from, None)
        reachable_move_to.side_effect(next_state)

        if (move_piece := next_state.get(move_to)) is not None:
            move_piece.moved = True

            if move_piece.kind == Kind.King:
                next_state.king_position[next_state.turn] = move_to

        next_state.update_covered() # 利き範囲を更新

        if next_state.king_position[next_state.turn] in next_state.covered[next_state.turn.opponent()]: # 後でKingがCheckされているかに置き換える
            # ターン終了時にKingがcheckされている
            printErr("[Error] You cannot place your king in check.")
            return False

        self.__dict__.update(next_state.__dict__)
        self.turn = self.turn.opponent()
        self.can_en_passant[self.turn] = None

        return True

    # ユーザーに標準入力からマスの座標を入力させる
    @staticmethod
    def ask_place(msg: str):
        input_str = input(msg) # input_str: [file, rank]

        if len(input_str) != 2:
            printErr("[Error] You must input just 2 letters.")
            return None

        ok = True

        if not (ord("a") <= ord(input_str[0]) <= ord("h")):
            # fileがaからhの間の英子文字でない
            printErr("[Error] The file must be a lower case alphabet between a and h.")
            ok = False

        if not (input_str[1].isdigit() and 1 <= int(input_str[1]) <= 8):
            # rankが1から8の間の数字でない
            printErr("[Error] The rank must be an integer between 1 and 8.")
            ok = False

        return Game.str_to_idx(input_str) if ok else None

    @staticmethod
    def str_to_idx(coord: str):
        return Vec2(8 - int(coord[1]), ord(coord[0]) - ord("a"))


class ReachableResult:
    def __init__(self, place: Vec2, side_effect: Callable[[Game], None] = lambda _: None):
        self.place = place
        self.side_effect = side_effect


def pawn_reachable(color: Color):
    forward = -1 if color == Color.White else 1

    def _(game: Game, self: Piece, move_from: Vec2):
        result: set[ReachableResult] = set()

        # 1マス進む
        move_one = move_from + Vec2(forward, 0)

        if move_one.is_in_board() and game.get(move_one) is None:
            result.add(ReachableResult(move_one))

            # 2マス進む
            move_two = move_one + Vec2(forward, 0)

            if not self.moved and move_two.is_in_board() and game.get(move_two) is None:
                # En Passantフラグを立てる副作用
                # lambdaの中でプロパティに代入することはできない
                def set_flag(game: Game):
                    game.can_en_passant[self.color] = move_two

                result.add(ReachableResult(move_two, set_flag))

        # 斜め前
        for dj in [-1, 1]:
            move_to = move_from + Vec2(forward, dj)

            if move_to.is_out_board():
                continue

            target = game.get(move_to)

            if (target is not None) and target.color.is_opponent(self.color):
                # 敵がいるなら進める
                result.add(ReachableResult(move_to))

        # En passant
        for dj in [-1, 1]:
            move_pass = move_from + Vec2(0, dj)

            if move_pass.is_out_board():
                continue

            target = game.get(move_pass)

            if (target is not None) and target.color.is_opponent(self.color) and move_pass == game.can_en_passant[target.color]:
                # 敵がいて、かつ敵が2マス動いた直後なら進める

                move_to = move_from + Vec2(forward, dj)

                # 残像を取る副作用を追加
                def capture_afterimage(game: Game):
                    game.set(move_pass, None)

                result.add(ReachableResult(move_to, capture_afterimage))

        return result

    return _


def knight_reachable(game: Game, self: Piece, move_from: Vec2):
    result: set[ReachableResult] = set()

    for d in [(-1, -2), (1, -2), (-2, -1), (2, -1), (-2, 1), (2, 1), (-1, 2), (1, 2)]:
        move_to = move_from + Vec2(*d)

        if move_to.is_out_board():
            continue

        target = game.get(move_to)

        if target is None or self.color.is_opponent(target.color):
            # 何もないか、敵がいるなら進める
            result.add(ReachableResult(move_to))

    return result


def bishop_reachable(game: Game, self: Piece, move_from: Vec2):
    result: set[ReachableResult] = set()

    for d in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
        for scale in range(1, 8):
            move_to = move_from + scale * Vec2(*d)

            if move_to.is_out_board():
                continue

            target = game.get(move_to)

            if (target is None) or target.color.is_opponent(self.color):
                # 何もないか, 敵がいるなら進める
                result.add(ReachableResult(move_to))

            if target is not None:
                # 敵か味方がいるなら進めない
                break

    return result


def rook_reachable(game: Game, self: Piece, move_from: Vec2):
    result: set[ReachableResult] = set()

    for d in [(0, -1), (-1, 0), (1, 0), (0, 1)]:
        for scale in range(1, 8):
            move_to = move_from + scale * Vec2(*d)

            if move_to.is_out_board():
                continue

            target = game.get(move_to)

            if (target is None) or target.color.is_opponent(self.color):
                # 何もないか, 敵がいるなら進める
                result.add(ReachableResult(move_to))

            if target is not None:
                # 敵か味方がいるなら進めない
                break

    return result


def queen_reachable(game: Game, self: Piece, move_from: Vec2):
    result: set[ReachableResult] = set()

    for d in [(-1, -1), (1, -1), (-1, 1), (1, 1), (0, -1), (-1, 0), (1, 0), (0, 1)]:
        for scale in range(1, 8):
            move_to = move_from + scale * Vec2(*d)

            if move_to.is_out_board():
                continue

            target = game.get(move_to)

            if (target is None) or target.color.is_opponent(self.color):
                # 何もないか, 敵がいるなら進める
                result.add(ReachableResult(move_to))

            if target is not None:
                # 敵か味方がいるならそれ以上進めない
                break
    return result


def king_reachable(game: Game, self: Piece, move_from: Vec2):
    result: set[ReachableResult] = set()

    for d in [(-1, -1), (1, -1), (-1, 1), (1, 1), (0, -1), (-1, 0), (1, 0), (0, 1)]:
        move_to = move_from + Vec2(*d)

        if move_to.is_out_board():
            continue

        target = game.get(move_to)

        if (target is None) or self.color.is_opponent(target.color):
            result.add(ReachableResult(move_to))

    return result

class Piece:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.color, self.kind, self.reachable = Piece.char_to_piece[symbol]
        self.moved = False

    char_to_piece: dict[
        str,
        tuple[Color, Kind, Callable[[Game, Piece, Vec2], set[ReachableResult]]],
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


ansi = ANSI_SGR()

game = Game("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR")

def move_wrapped(move_from: str, move_to: str):
    game.move(lambda: Game.str_to_idx(move_from), lambda: Game.str_to_idx(move_to))

# move_wrapped("d2", "d4")
# move_wrapped("e7", "e5")
# move_wrapped("d4", "e5")
# move_wrapped("f7", "f5")
# move_wrapped("e5", "f6")
# move_wrapped("e8", "e7")
# move_wrapped("e8", "f7")
# move_wrapped("d1", "d8")
# move_wrapped("d1", "d5")
# move_wrapped("a7", "a5")

while True:
    game.game_cycle()