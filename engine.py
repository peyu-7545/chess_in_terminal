from enum import Enum
from typing import Any
import copy

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
    Playing   = 0
    Checkmate = 1
    Stalemate = 2

# TODO: Gameのstaticmethodに移す & FEN の全てのデータを使う
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

class Action:
    def __init__(self):
        pass

    def do(self, game: Game):
        pass

    def __str__(self) -> str:
        return ""

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