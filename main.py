from __future__ import annotations
import signal
import sys

from engine import Game, Piece, Vec, Color, Kind, Status

game = Game()

# Ctrl+Cが押されたら入力中でも強制終了する
signal.signal(signal.SIGINT, lambda _signum, _frame: exit(0))

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

def ask_place(msg: str):
    input_str = input(ansi.bold + msg + ansi.reset)

    if (len(input_str) == 2 and
        ord("a") <= ord(input_str[0]) <= ord("h") and
        ord("1") <= ord(input_str[1]) <= ord("8")
    ):
        return Vec.from_str(input_str)

    return None

def humanTurn(game: Game):

    print(f"\n {ansi.bold}{game.turn.name}{ansi.reset}'s turn \n")
    render(game.data)

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

        # Promotion
        if (
            (selected.kind == Kind.Pawn) and 
            ((to_.i == 0) if (selected.color == Color.White) else (to_.i == 7))
        ):
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

# FEN
# Piece Placement
# Active Color (w or b)
# Castling Rights (K, Q, k, q, or -)
# Possible En Passant Targets
# Halfmove Clock: Pawnの前進 / Capture からの両プレイヤーの手数 (100になると引き分け)
# Fullmove Number: 黒が動かすたび1増加 (最初は1)