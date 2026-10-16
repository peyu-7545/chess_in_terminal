from enum import Enum

board = [
    [-4, -2, -3, -5, -6, -3, -2, -4],
    [-1, -1, -1, -1, -1, -1, -1, -1],
    [-0, -0, -0, -0, -0, -0, -0, -0],
    [-0, -0, -0, -0, -0, -0, -0, -0],
    [+0, +0, +0, +0, +0, +0, +0, +0],
    [+0, +0, +0, +0, +0, +0, +0, +0],
    [+1, +1, +1, +1, +1, +1, +1, +1],
    [+4, +2, +3, +5, +6, +3, +2, +4],
]


def in_board(i, j):
    return 0 <= i and i < 8 and 0 <= j and j < 8


# 探索する範囲, 伸ばす最大距離, 条件(距離の2乗)
def symmetry_piece_reachable(max_dist, cond):
    def fn(i, j, moving_piece):
        result = []

        for di in range(-2, 3):
            for dj in range(-2, 3):

                if di * di + dj * dj in cond:
                    for dist in range(1, max_dist + 1):
                        ni = i + di * dist
                        nj = j + dj * dist

                        if not in_board(ni, nj):
                            # 盤外
                            break

                        piece = id_to_piece[board[ni][nj]]

                        # 自分の駒があるなら進めないので終了
                        if piece is not None and piece.color() == moving_piece.color():
                            break

                        result.append((ni, nj))

                        # 相手の駒があるなら次へ進めないので終了
                        if piece is not None and piece.color() != moving_piece.color():
                            break

        return result

    return fn


def pawn_reachable(i, j, moving_piece):
    result = []

    forward = -1 if moving_piece.color() == Color.White else 1

    # 直進
    for dist in range(1, (1 if moving_piece.moved else 2) + 1):
        ni = i + forward * dist
        nj = j

        if not in_board(ni, nj):
            # 盤外
            continue

        if id_to_piece[board[ni][nj]] is None:
            # 何もなければ直進
            result.append((ni, nj))

    for dj in [-1, 1]:
        ni = i + forward
        nj = j + dj

        if not in_board(ni, nj):
            # 盤外
            continue

        forward_piece = id_to_piece[board[ni][nj]]

        if forward_piece is not None and forward_piece.color().opponent() == moving_piece.color():
            # 敵がいれば取って移動できる
            result.append((ni, nj))

    return result

def coord_to_index(rank, file):
    return (8 - int(rank), ord(file) - ord("a"))

def index_to_coord(i, j):
    return chr(ord("a") + j) + str(8 - i)

class Piece:
    def __init__(self, char, point, reachable, id):
        self.char = char
        self.point = point
        self.reachable = reachable
        self.id = id
        self.moved = False

    def color(self):
        return Color.White if self.char.isupper() else Color.Black


king_reachable = symmetry_piece_reachable(1, [1, 2])
queen_reachable = symmetry_piece_reachable(8, [1, 2])
rook_reachable = symmetry_piece_reachable(8, [1])
bishop_reachable = symmetry_piece_reachable(8, [2])
knight_reachable = symmetry_piece_reachable(1, [5])

id_to_piece = {
    -6: Piece("k", float("inf"), king_reachable, -6),
    -5: Piece("q", 9.0, queen_reachable, -5),
    -4: Piece("r", 5.0, rook_reachable, -4),
    -3: Piece("b", 3.0, bishop_reachable, -3),
    -2: Piece("n", 3.0, knight_reachable, -2),
    -1: Piece("p", 1.0, pawn_reachable, -1),
    0: None,
    +1: Piece("P", 1.0, pawn_reachable, +1),
    +2: Piece("N", 3.0, knight_reachable, +2),
    +3: Piece("B", 3.0, bishop_reachable, +3),
    +4: Piece("R", 5.0, rook_reachable, +4),
    +5: Piece("Q", 9.0, queen_reachable, +5),
    +6: Piece("K", float("inf"), king_reachable, +6),
}


class Color(Enum):
    White = 1
    Black = 2

    def opponent(self):
        return Color.Black if self == Color.White else Color.White


def render():

    print("")
    print("  abcdefgh")
    print("  --------")

    for i, line in enumerate(board):
        print(f"{8 - i}|", end="")

        for piece in line:
            if piece == 0:
                print(".", end="")
                continue

            print(id_to_piece[piece].char, end="")

        print("")

    print("")

def ask_place():

    file, rank = list(input())

    error = False

    if not (len(file) == 1 and ord("a") <= ord(file) <= ord("h")):
        print("File must be a lower alphabet between a and h.")
        error = True

    if not (rank.isdigit() and 1 <= int(rank) <= 8):
        print("Rank must be an integer between 1 and 8.")
        error = True

    if error:
        return None

    return coord_to_index(rank, file)


def select():

    print("Please input piece: ", end="")
    move_from = ask_place()

    if move_from is None:
        return False

    from_i, from_j = move_from

    selected_piece = id_to_piece[board[from_i][from_j]]

    if selected_piece is None:
        print("There is nothing where you selected")
        return False

    print(f"You selected: {selected_piece.char}")

    if selected_piece.color() != turn:
        print("The piece you choice is not yours")
        return False

    reachable_tiles = selected_piece.reachable(from_i, from_j, selected_piece)

    print("Please input where to move to: ", end="")
    move_to = ask_place()

    if move_to is None:
        return False

    to_i, to_j = move_to

    if (to_i, to_j) not in reachable_tiles:
        print(f"You cannot move it there!!")
        return False

    board[from_i][from_j] = 0
    board[to_i][to_j] = selected_piece.id

    print("")

    return True

turn = Color.White

while True:
    print(f"~~~ {turn.name}'s turn! ~~~")
    render()

    while not select():
        continue

    turn = turn.opponent()
