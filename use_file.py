from pathlib import Path
from engine import Engine, Vec, Color

data_file = Path("data.fen")

# ファイルが存在しないか空
if not data_file.exists() or data_file.stat().st_size == 0:
    data_file.write_text(Engine().to_fen(), encoding="utf-8")

engine = Engine(data_file.read_text())

iccf = input()
nums = [int(x) for x in iccf]

legal = engine.get_all_legal_moves(engine.turn)

from_ = Vec(8 - nums[1], nums[0] - 1)
to_   = Vec(8 - nums[3], nums[2] - 1)

legal = [x for x in legal if x[0].from_ == from_ and x[0].to_ == to_]

if len(nums) == 5:
    opt = ("N", "B", "R", "Q") if engine.turn == Color.White else ("n", "b", "r", "q")
    promote_to = opt[nums[4]]

    legal = [x for x in legal if x[0].action.to_ == promote_to] # type: ignore

next = engine.simulate_move(legal[0][0])

assert next

engine.update_turn(next)

data_file.write_text(engine.to_fen())