from __future__ import annotations
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

class Color(Enum):
    White = 1
    Black = 2

    def enemy(self):
        return Color.Black if self == Color.White else Color.White

    def is_enemy(self, other: Color):
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

    def is_in(self):
        return 0 <= self.i and self.i < 8 and 0 <= self.j and self.j < 8

    def is_out(self):
        return not self.is_in()

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

class Status(Enum):
    Playing   = 0,
    Checkmate = 1,
    Stalemate = 2,

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

def ask_place(msg: str):
    input_str = input(ansi.bold + msg + ansi.reset)

    if (len(input_str) == 2 and
        ord("a") <= ord(input_str[0]) <= ord("h") and
        ord("1") <= ord(input_str[1]) <= ord("8")
    ):
        return Vec.from_str(input_str)

    return None

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

        self.status: Status = Status.Playing

        self.calc_covered_tiles()

    def calc_covered_tiles(self):
        self.covered[Color.White].clear()
        self.covered[Color.Black].clear()

        for i in range(8):
            for j in range(8):
                piece = self.get(Vec(i, j))

                if piece:
                    # この駒から到達可能なマスを追加
                    for x in piece.reachable(self, Vec(i, j)):
                        self.covered[piece.color].add(x.to_)

    def update_turn(self, next_turn: Game):
        current_turn = self.turn
        current_enemy = self.turn.enemy()

        self.__dict__.update(next_turn.__dict__)
        self.turn = current_enemy
        self.can_en_passant[current_enemy] = None

        enemy_checked = self.is_covered(self.king_position[current_enemy], current_turn)

        if len(self.get_all_legal_moves(current_enemy)) == 0:
            if enemy_checked:
                self.status = Status.Checkmate
            else:
                self.status = Status.Stalemate

    def get(self, x: Vec):
        return self.data[x.i][x.j]

    def set(self, x: Vec, y: Piece | None):
        self.data[x.i][x.j] = y

    def is_covered(self, pos: Vec, by: Color):
        return pos in self.covered[by]

    # コピーした盤面で動きをシミュレートする
    # 動いた後にCheckされていなければその盤面を返す
    def test_move(self, move: Move):
        parallel = copy.deepcopy(self)
        parallel.set(move.to_, parallel.get(move.from_))
        parallel.set(move.from_, None)

        move.action.do(parallel)

        moved_piece = parallel.get(move.to_)
        assert moved_piece is not None

        moved_piece.moved = True

        if moved_piece.kind == Kind.King:
            parallel.king_position[parallel.turn] = move.to_

        parallel.calc_covered_tiles()

        if parallel.is_covered(parallel.king_position[parallel.turn], parallel.turn.enemy()):
            return None

        return parallel

    def get_all_legal_moves(self, color: Color):
        legal_moves: list[tuple[Move, Game]] = []

        for i in range(8):
            for j in range(8):
                piece = self.get(Vec(i, j))

                if piece and piece.color == color:
                    for move in piece.reachable(self, Vec(i, j)):
                        if (next := self.test_move(move)):
                            legal_moves.append((move, next))

        return legal_moves

class Action:
    def __init__(self):
        pass

    def do(self, game: Game):
        pass

    def __str__(self) -> str:
        return ""
    
class Move:
    def __init__(self, from_: Vec, to_: Vec, action: Action = Action()):
        self.from_  = from_
        self.to_    = to_
        self.action = action

    def __str__(self):
        return f"{self.from_} -> {self.to_} {self.action}"

class Piece:
    def __init__(self, symbol: str):
        self.color, self.kind = Piece.char_to_piece[symbol]
        self.symbol = symbol
        self.moved = False

    char_to_piece: dict[
        str,
        tuple[Color, Kind],
    ] = {
        "P": (Color.White, Kind.Pawn),
        "N": (Color.White, Kind.Knight),
        "B": (Color.White, Kind.Bishop),
        "R": (Color.White, Kind.Rook),
        "Q": (Color.White, Kind.Queen),
        "K": (Color.White, Kind.King),
        "p": (Color.Black, Kind.Pawn),
        "n": (Color.Black, Kind.Knight),
        "b": (Color.Black, Kind.Bishop),
        "r": (Color.Black, Kind.Rook),
        "q": (Color.Black, Kind.Queen),
        "k": (Color.Black, Kind.King),
    }

    def is_enemy(self, other: Piece):
        return self.color.is_enemy(other.color)

    def reachable(self, game: Game, from_: Vec):
        result: set[Move] = set()

        if self.kind == Kind.Pawn:
            # Pawn

            forward      =     -1 if self.color == Color.White else 1
            promote_line =      0 if self.color == Color.White else 7
            promote_opt  = "NBRQ" if self.color == Color.White else "nbrq"

            m1 = from_ + Vec(forward, 0)

            if m1.is_in() and game.get(m1) is None:
                if m1.i == promote_line:
                    for k in promote_opt:
                        result.add(Move(from_, m1, Promote(m1, k)))
                else:
                    result.add(Move(from_, m1))

                if not self.moved:
                    m2 = from_ + Vec(2 * forward, 0)

                    if m2.is_in() and game.get(m2) is None:
                        # 前提: 2マス進むのと昇格は同時に起こらない
                        result.add(Move(from_, m2, SetEnpassantFlag(m2, self.color)))

            for dj in -1, 1:
                pass_ = from_ + Vec(0,       dj)
                to_   = from_ + Vec(forward, dj)

                if to_.is_in():
                    if (target := game.get(to_)) and target.is_enemy(self):
                        # 斜め前に敵がいるなら取れる
                        if to_.i == promote_line:
                            for k in promote_opt:
                                result.add(Move(from_, to_, Promote(to_, k)))
                        else:
                            result.add(Move(from_, to_))

                    if (target := game.get(pass_)) and target.is_enemy(self) and pass_ == game.can_en_passant[target.color]:
                        # 横にEn passant可能な駒がいるなら斜め前に移動しながら取れる
                        result.add(Move(from_, to_, Enpassant(pass_)))

        elif self.kind == Kind.Knight:
            # Knight

            for d in (-1, -2), (1, -2), (-2, -1), (2, -1), (-2, 1), (2, 1), (-1, 2), (1, 2):
                to_ = from_ + Vec(*d)

                if to_.is_in():
                    target = game.get(to_)

                    if target is None or target.is_enemy(self):
                        result.add(Move(from_, to_))

        elif self.kind != Kind.King:
            # Bishop, Rook, Queen

            if self.kind == Kind.Bishop:
                direction = (-1, -1), (1, -1), (-1, 1), (1, 1)
            elif self.kind == Kind.Rook:
                direction = (0, -1), (-1, 0), (1, 0), (0, 1)
            else:
                direction = (-1, -1), (1, -1), (-1, 1), (1, 1), (0, -1), (-1, 0), (1, 0), (0, 1)

            for d in direction:
                for scale in range(1, 8):
                    to_ = from_ + scale * Vec(*d)

                    if to_.is_in():
                        target = game.get(to_)

                        if target is None or target.is_enemy(self):
                            result.add(Move(from_, to_))

                        if target:
                            break

        else:
            # King
            direction = (-1, -1), (1, -1), (-1, 1), (1, 1), (0, -1), (-1, 0), (1, 0), (0, 1)

            for d in direction:
                to_ = from_ + Vec(*d)

                if to_.is_in():
                    target = game.get(to_)

                    if target is None or target.is_enemy(self):
                        result.add(Move(from_, to_))

            for dj, rook_j in (-1, 0), (1, 7):
                to_ = from_ + Vec(0, dj * 2)
                rook_pos = Vec(from_.i, rook_j)
                rook = game.get(rook_pos)

                # Castlingできるか判定
                if (
                    not self.moved and # Kingが一度も動いていない
                    rook and rook.kind == Kind.Rook and not rook.moved and # Rookが一度も動いていない
                    all(game.get(Vec(from_.i, j)) is None for j in range(from_.j + dj, rook_j, dj)) and # 間に駒がない
                    all(not game.is_covered(Vec(from_.i, j), self.color.enemy()) for j in range(from_.j, from_.j + dj * 3, dj)) # 移動中に攻撃されない
                ):
                    result.add(Move(from_, to_, Castling(rook_pos, from_ + Vec(0, dj))))

        return result
                
class Promote(Action):
    def __init__(self, pos: Vec, to_: str):
        self.pos = pos
        self.to_ = to_

    def do(self, game: Game):
        x = Piece(self.to_)
        x.moved = True
        game.set(self.pos, x)

    def __str__(self):
        return f"Promote to {self.to_}"

class SetEnpassantFlag(Action):
    def __init__(self, pos: Vec, color: Color):
        self.pos   = pos
        self.color = color

    def do(self, game: Game):
        game.can_en_passant[self.color] = self.pos

    def __str__(self):
        return "Set Enpassant Flag"

class Enpassant(Action):
    def __init__(self, pos: Vec):
        self.pos = pos

    def do(self, game: Game):
        game.set(self.pos, None)

    def __str__(self):
        return "Enpassant"

class Castling(Action):
    def __init__(self, rook_from: Vec, rook_to: Vec):
        self.rook_from = rook_from
        self.rook_to   = rook_to

    def do(self, game: Game):
        game.set(self.rook_to, game.get(self.rook_from))
        game.set(self.rook_from, None)

        x = game.get(self.rook_to)
        assert x is not None
        x.moved = True

    def __str__(self):
        return "Castling"

game = Game()

ansi = ANSI_SGR()

def printErr(err: str):
    print(ansi.red + ansi.bold + err + ansi.reset)

def render(data: list[list[Piece | None]]):
    print(" abcdefgh")

    for i in range(8):
        print(str(8 - i), end="")

        for j in range(8):
            d = data[i][j]

            print(ansi.bg_green if (i + j) % 2 == 0 else ansi.bg_white, end="")
            print(ansi.bold, end="")

            if d is None:
                print(" " if ansi.support_ansi else ".", end="")
            else:
                print(d.symbol, end="")

            print(ansi.reset, end="")

        print("")

def can_promote(pos: Vec, color: Color, kind: Kind):
    return (kind == Kind.Pawn) and ((pos.i == 0) if (color == Color.White) else (pos.i == 7))

def humanTurn(game: Game):

    print(f"\n {ansi.bold}{game.turn.name}{ansi.reset}'s turn \n")
    render(game.data)

    # Debug Info (消す)
    for x in game.get_all_legal_moves(game.turn):
        print(x[0])

    while True:

        legal_moves = game.get_all_legal_moves(game.turn)

        if (from_ := ask_place("from: ")) is None:
            printErr("Wrong Input")
            continue

        # 入力された座標に駒がないか、相手の駒だったとき
        if (selected := game.get(from_)) is None or selected.color.is_enemy(game.turn):
            printErr("There is not your piece")
            continue

        if (to_ := ask_place("to: ")) is None:
            printErr("Wrong Input")
            continue

        # 合法手のうち、入力された移動前と移動後に一致するものだけ取り出す
        legal_moves = [x for x in legal_moves if x[0].from_ == from_ and x[0].to_ == to_]

        if len(legal_moves) == 0:
            printErr("You cannot move it there")
            continue

        if can_promote(to_, selected.color, selected.kind):
            opt = ("N", "B", "R", "Q") if game.turn == Color.White else ("n", "b", "r", "q")
            char = input(f"Promote to: ")

            if char not in opt:
                printErr("You must select from" + ", ".join(opt))
                continue

            legal_moves = [x for x in legal_moves if x[0].action.to_ == char] # type: ignore

        assert len(legal_moves) == 1, "[Bug] 合法手が一通りに定まっていない"

        game.update_turn(legal_moves[0][1])
        break

while game.status == Status.Playing:
    humanTurn(game)

# TODO
# [x] 人間の入力とゲーム内の処理の分離
# [ ] ファイルにゲームの進行を保持(Shortcutで動かすため)
# [ ] MoveとGame(移動後の盤面)は一体化させていいのか？
# [ ] tuple[Move, Game]に対してindexでアクセスすると可読性が悪そう
# [ ] can_en_passantって常に白黒のどちらかだけ？ FENを見る限り多分そう