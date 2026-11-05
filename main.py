from __future__ import annotations
from collections.abc import Callable
from enum import Enum
import signal
import sys
import copy
from typing import Any

# Ctrl+Cが押されたら入力中でも強制終了する
signal.signal(signal.SIGINT, lambda _signum, _frame: exit(0))

# ANSI Select Graphics Renditionを直感的に扱うためのクラス
# ターミナルがANSIに対応していない場合は何もしない
class ANSI_SGR:

    def __init__(self):
        self.support_ansi = sys.stdout.isatty()

    def __getattr__(self, name: str):
        if self.support_ansi and name in self.Codes:
            return f"\033[{self.Codes[name]}m"
        else:
            return ""

    Codes = {
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

class Vec:
    def __init__(self, i: int, j: int):
        self.i = i
        self.j = j

    def is_in_board(self):
        return 0 <= self.i and self.i < 8 and 0 <= self.j and self.j < 8

    def is_out_board(self):
        return not self.is_in_board()

    def __add__(self, other: Vec):
        return Vec(self.i + other.i, self.j + other.j)

    def __rmul__(self, other: int):
        return Vec(other * self.i, other * self.j)

    def __hash__(self):
        return hash((self.i, self.j))

    def __eq__(self, other: Any):
        if not isinstance(other, Vec):
            return NotImplemented

        return self.i == other.i and self.j == other.j

    def __str__(self):
        return chr(self.j + ord('a')) + str(8 - self.i)

    @staticmethod
    def from_str(coord: str):
        return Vec(8 - int(coord[1]), ord(coord[0]) - ord("a"))

def FEN_to_array(fen: str):
    result: list[list[Piece | None]] = [[None] * 8 for _ in range(8)]

    for i, line in enumerate(fen.split("/")):
        j = 0

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
    def __init__(self):

        self.data = FEN_to_array("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR")        
        self.turn = Color.White

        # Kingの位置
        self.king_position: dict[Color, Vec] = {
            Color.White: Vec(7, 4),
            Color.Black: Vec(0, 4),
        }

        # 直前に2マス動いたPawnの位置
        self.can_en_passant: dict[Color, Vec | None] = {
            Color.White: None,
            Color.Black: None,
        }

        # 利いているマスの集合
        self.covered: dict[Color, set[Vec]] = {
            Color.White: set(),
            Color.Black: set(),
        }

        self.update_covered()

    def update_covered(self):
        self.covered[Color.White].clear()
        self.covered[Color.Black].clear()

        for i in range(8):
            for j in range(8):
                piece = self.get(Vec(i, j))

                if piece:
                    # この駒から到達可能なマスを追加
                    for x in piece.reachable(self, piece, Vec(i, j)):
                        self.covered[piece.color].add(x.to_)

    def get(self, x: Vec):
        return self.data[x.i][x.j]

    def set(self, x: Vec, y: Piece | None):
        self.data[x.i][x.j] = y

    def render_board(self):

        print("\n abcdefgh")

        for i in range(8):
            print(8 - i, end="")

            for j in range(8):

                # マスの色は白と緑の市松模様
                bg_color = ansi.bg_white if (i + j) % 2 == 0 else ansi.bg_green

                piece = self.get(Vec(i, j))

                if piece:
                    char = piece.symbol
                else:
                    char = " " if ansi.support_ansi else "."

                print(f"{bg_color}{ansi.bold}{char}{ansi.reset}", end="")

            print("")

        print("")

    def player_turn(self):

        print(f"\n--- {ansi.bold}{self.turn.name}{ansi.reset}'s turn ---")
        self.render_board()

        get_move_from = lambda: self.ask_place("Please select piece: ")
        get_move_to   = lambda: self.ask_place("Please select where to move: ")

        while True:
            if self.move(get_move_from, get_move_to):
                break

    def move(self, get_move_from: Callable[[], Vec | None], get_move_to: Callable[[], Vec | None]):

        if not (from_ := get_move_from()):
            return False

        selected_piece = self.get(from_)

        if (not selected_piece) or selected_piece.color.is_opponent(self.turn):
            printErr("There is not your piece.")
            return False

        if not (to_ := get_move_to()):
            return False

        reachable_tiles = selected_piece.reachable(self, selected_piece, from_)

        # reachable_tilesの中からmove_toを探す(なければNone)
        reachable_move_to = next((x for x in reachable_tiles if x.to_ == to_), None)

        if not reachable_move_to:
            printErr("You cannot move it there.")
            return False
        
        if not (next_state := self.simulate_move(reachable_move_to)):
            printErr("You cannot place your king in check.")
            return False

        self.__dict__.update(next_state.__dict__)
        self.turn = self.turn.opponent()
        self.can_en_passant[self.turn] = None

        is_opponent_checked = self.is_covered(self.king_position[self.turn], self.turn.opponent())

        has_legal_move = False

        for i in range(8):
            for j in range(8):
                piece = self.get(Vec(i, j))

                if piece and piece.color == self.turn:
                    for move in piece.reachable(self, piece, Vec(i, j)):   
                        if self.simulate_move(move):
                            has_legal_move = True

        if not has_legal_move:
            if is_opponent_checked:
                print(f"\n{ansi.bold}Checkmate!!{ansi.reset}")
            else:
                print(f"\n{ansi.bold}Stalemate!!{ansi.reset}")

            exit(0)

        return True

    def is_covered(self, pos: Vec, by: Color):
        return pos in self.covered[by]

    # コピーした盤面で動きをシミュレートする
    # 動いた後にCheckされていなければその盤面を返す
    def simulate_move(self, move: Move):
        parallel = copy.deepcopy(self)
        parallel.set(move.to_, parallel.get(move.from_))
        parallel.set(move.from_, None)
        move.action(parallel)

        moved_piece = parallel.get(move.to_)
        assert moved_piece is not None

        moved_piece.moved = True

        if moved_piece.kind == Kind.King:
            parallel.king_position[parallel.turn] = move.to_

        parallel.update_covered()

        if parallel.is_covered(parallel.king_position[parallel.turn], parallel.turn.opponent()):
            return None

        return parallel

    @staticmethod
    def ask_place(msg: str):
        input_str = input(msg)

        if len(input_str) != 2:
            printErr("You must input just 2 letters.")
            return None

        ok = True

        if not (ord("a") <= ord(input_str[0]) <= ord("h")):
            printErr("The file must be a lower case alphabet between a and h.")
            ok = False

        if not (input_str[1].isdigit() and 1 <= int(input_str[1]) <= 8):
            printErr("The rank must be an integer between 1 and 8.")
            ok = False

        return Vec.from_str(input_str) if ok else None
    
class Move:
    def __init__(self, from_: Vec, to_: Vec, action: Callable[[Game], None] = lambda _: None):
        self.from_ = from_
        self.to_ = to_
        self.action = action

def pawn_reachable(color: Color):
    forward = -1 if color == Color.White else 1
    promotion_line = 0 if color == Color.White else 7

    def promotion(pos: Vec):
        def _(game: Game):
            while True:
                piece = input("Please select which piece you want to promote from N,B,R,Q: ")

                if piece not in ("N", "B", "R", "Q"):
                    printErr("You must select from N,B,R,Q.")
                else:
                    break

            promoted = Piece(piece, True)

            game.set(pos, promoted)

        return _

    def _(game: Game, self: Piece, from_: Vec):
        result: set[Move] = set()

        # 1マス進む
        move_one = from_ + Vec(forward, 0)

        if move_one.is_in_board() and (not game.get(move_one)):
            if move_one.i == promotion_line:
                result.add(Move(from_, move_one, promotion(move_one)))
            else:
                result.add(Move(from_, move_one))

            # 2マス進む
            move_two = from_ + Vec(2 * forward, 0)

            if (not self.moved) and move_two.is_in_board() and (not game.get(move_two)):
                # 一度も動いていなく、1マス先と2マス先に何もないとき

                def set_flag(game: Game):
                    game.can_en_passant[self.color] = move_two

                result.add(Move(from_, move_two, set_flag))

        # 斜め前
        for dj in -1, 1:
            move_pass = from_ + Vec(0, dj)
            to_ = from_ + Vec(forward, dj)

            if to_.is_in_board():
                if (target := game.get(to_)) and target.color.is_opponent(self.color):
                    # 斜め前に相手の駒があるとき
                    if to_.i == promotion_line:
                        result.add(Move(from_, to_, promotion(to_)))
                    else:
                        result.add(Move(from_, to_))

                if (target := game.get(move_pass)) and target.color.is_opponent(self.color) and move_pass == game.can_en_passant[target.color]:
                    # 横にEn passant可能な相手の駒があるとき

                    def en_passant(game: Game):
                        game.set(move_pass, None)

                    result.add(Move(from_, to_, en_passant))

        return result

    return _

def knight_reachable(game: Game, self: Piece, from_: Vec):
    result: set[Move] = set()

    for d in (-1, -2), (1, -2), (-2, -1), (2, -1), (-2, 1), (2, 1), (-1, 2), (1, 2):
        to_ = from_ + Vec(*d)

        if to_.is_out_board():
            continue

        target = game.get(to_)

        if (not target) or self.color.is_opponent(target.color):
            result.add(Move(from_, to_))

    return result

def bishop_reachable(game: Game, self: Piece, from_: Vec):
    result: set[Move] = set()

    for d in (-1, -1), (1, -1), (-1, 1), (1, 1):
        for scale in range(1, 8):
            to_ = from_ + scale * Vec(*d)

            if to_.is_out_board():
                continue

            target = game.get(to_)

            if (not target) or target.color.is_opponent(self.color):
                result.add(Move(from_, to_))

            if target:
                break

    return result

def rook_reachable(game: Game, self: Piece, from_: Vec):
    result: set[Move] = set()

    for d in (0, -1), (-1, 0), (1, 0), (0, 1):
        for scale in range(1, 8):
            to_ = from_ + scale * Vec(*d)

            if to_.is_out_board():
                continue

            target = game.get(to_)

            if (not target) or target.color.is_opponent(self.color):
                result.add(Move(from_, to_))

            if target:
                break

    return result

def queen_reachable(game: Game, self: Piece, from_: Vec):
    result: set[Move] = set()

    for d in (-1, -1), (1, -1), (-1, 1), (1, 1), (0, -1), (-1, 0), (1, 0), (0, 1):
        for scale in range(1, 8):
            to_ = from_ + scale * Vec(*d)

            if to_.is_out_board():
                continue

            target = game.get(to_)

            if (not target) or target.color.is_opponent(self.color):
                result.add(Move(from_, to_))

            if target:
                break

    return result

def king_reachable(game: Game, self: Piece, from_: Vec):
    result: set[Move] = set()

    for d in (-1, -1), (1, -1), (-1, 1), (1, 1), (0, -1), (-1, 0), (1, 0), (0, 1):
        to_ = from_ + Vec(*d)

        if to_.is_out_board():
            continue

        target = game.get(to_)

        if (not target) or self.color.is_opponent(target.color):
            result.add(Move(from_, to_))

    for dj, rook_j in (-1, 0), (1, 7):

        to_ = from_ + Vec(0, dj * 2)
        rook_pos = Vec(from_.i, rook_j)
        rook = game.get(rook_pos)

        # Castlingできるか判定
        if (
            not self.moved and # Kingが一度も動いていない
            rook and (rook.kind == Kind.Rook) and (not rook.moved) and # Rookが一度も動いていない
            all(not game.get(Vec(from_.i, j)) for j in range(from_.j + dj, rook_j, dj)) and # 間に駒がない
            all(not game.is_covered(Vec(from_.i, j), self.color.opponent()) for j in range(from_.j, from_.j + dj * 3, dj)) # 移動中に攻撃されない
        ):
            def castling(game: Game):
                game.get(rook_pos).moved = True # type: ignore
                game.set(from_ + Vec(0, dj), game.get(rook_pos))
                game.set(rook_pos, None)

            result.add(Move(from_, to_, castling))
                
    return result

class Piece:
    def __init__(self, symbol: str, default_moved: bool = False):
        self.color, self.kind, self.reachable = Piece.char_to_piece[symbol]
        self.symbol = symbol
        self.moved = default_moved

    char_to_piece: dict[
        str,
        tuple[Color, Kind, Callable[[Game, Piece, Vec], set[Move]]],
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

game = Game()

while True:
    game.player_turn()