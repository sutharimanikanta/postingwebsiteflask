import sys

res = []
for l in sys.stdin:
    if l.strip() == " ":
        break
    res.append(l.strip())
print("\n".join(res))
