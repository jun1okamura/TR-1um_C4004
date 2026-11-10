import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IN_GUIDE = os.path.join(BASE_DIR, "openroad/route.guide")
OUT_GUIDE = os.path.join(BASE_DIR, "openroad/route_expanded.guide")

PAD = 81000
MAX_C = 1840000

with open(IN_GUIDE, "r") as f:
    lines = f.read().splitlines()

out = []
rect_re = re.compile(r"^(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(METAL[12])$")
for line in lines:
    m = rect_re.match(line.strip())
    if m:
        x1, y1, x2, y2, lay = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)), m.group(5)
        nx1 = max(0, x1 - PAD)
        ny1 = max(0, y1 - PAD)
        nx2 = min(MAX_C, x2 + PAD)
        ny2 = min(MAX_C, y2 + PAD)
        out.append(f"{nx1} {ny1} {nx2} {ny2} {lay}")
    else:
        out.append(line)

with open(OUT_GUIDE, "w") as f:
    f.write("\n".join(out) + "\n")
print(f"Wrote {OUT_GUIDE} ({len(out)} lines)")
