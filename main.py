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
    def fn(i, j, piece_color):
        result = []

        for di in range(-2, 3):
            for dj in range(-2, 3):

                if di * di + dj * dj in cond:
                    for dist in range(1, max_dist + 1):
                        ni = i + di * dist
                        nj = j + dj * dist

                        if in_board(ni, nj):
                            piece = id_to_piece[board[ni][nj]]

                            # 自分の駒があるなら進めないので終了
                            if piece is not None and piece.color() == piece_color:
                                break

                            result.append((ni, nj))

                            # 相手の駒があるなら次へ進めないので終了
                            if piece is not None and piece.color() != piece_color:
                                break

                        else:
                            # 盤外
                            break

        return result

    return fn


king_reachable = symmetry_piece_reachable(1, [1, 2])
queen_reachable = symmetry_piece_reachable(8, [1, 2])
rook_reachable = symmetry_piece_reachable(8, [1])
bishop_reachable = symmetry_piece_reachable(8, [2])
knight_reachable = symmetry_piece_reachable(1, [5])


def pawn_reachable(i, j, piece_color):
    result = []

    for dj in range(-1, 2):
        ni = i + (-1 if piece_color else 1)
        nj = j + dj

        if not(in_board(ni, nj)):
            # 盤外
            continue

        if dj == 0:
            # 何もなければ直進
            if id_to_piece[board[ni][nj]] is None:
                result.append((ni, nj))
        else:
            # 敵がいれば取って移動できる
            if id_to_piece[board[ni][nj]] is not None and id_to_piece[board[ni][nj]].color() != piece_color:
                result.append((ni, nj))

    return result

class Piece:
    def __init__(self, char, point, reachable):
        self.char = char
        self.point = point
        self.reachable = reachable

    def color(self):
        return self.char.isupper()
    
id_to_piece = {
    -6: Piece("k", float("inf"), king_reachable),
    -5: Piece("q", 9.0, queen_reachable),
    -4: Piece("r", 5.0, rook_reachable),
    -3: Piece("b", 3.0, bishop_reachable),
    -2: Piece("n", 3.0, knight_reachable),
    -1: Piece("p", 1.0, pawn_reachable),
    0:  None,
    +1: Piece("p", 1.0, pawn_reachable),
    +2: Piece("n", 3.0, knight_reachable),
    +3: Piece("b", 3.0, bishop_reachable),
    +4: Piece("r", 5.0, rook_reachable),
    +5: Piece("q", 9.0, queen_reachable),
    +6: Piece("k", float("inf"), king_reachable),
}

def render():
    for line in board:
        for piece in line:

            if piece == 0:
                print(".", end="")
                continue

            print(id_to_piece[piece].char, end="")

        print("\n", end="")


is_white_turn = True


def select():

    file = input("file (a~h): ")

    if not (len(file) == 1 and ord("a") <= ord(file) <= ord("h")):
        print("Error! File must be a letter between a and h.")
        return False

    rank = input("rank (1~8): ")

    if not (rank.isdigit() and 1 <= int(rank) <= 8):
        print("Error! Rank must be an integer between 1 and 8.")
        return False

    i = 8 - int(rank)
    j = ord(file) - ord("a")

    selected_piece = id_to_piece[board[i][j]]

    if selected_piece is None:
        print("There is nothing where you selected!!")
        return False

    print(f"Your select: {i}, {j}: {selected_piece.char}")

    if selected_piece.color() != is_white_turn:
        print("The piece you choice is not yours!!")
        return False

    reachable_tiles = selected_piece["reachable"](i, j, is_white_turn)

    print(f"Places that you can move: {reachable_tiles}")

    return True


while True:
    render()

    while not (select()):
        continue

    print("")
    print("-" * 30)
    print("")
