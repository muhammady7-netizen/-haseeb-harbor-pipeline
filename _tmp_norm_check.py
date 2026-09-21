msg = """| room | messages | replies | threads answered |
| --- | --- | --- | --- |
| general-meshworks-security | 11 | 3 | 2 |
| security-095 | 11 | 4 | 2 |
| security-v1-041 | 15 | 7 | 6 |
| security-v3-065 | 19 | 11 | 7 |
| TOTAL | 56 | 25 | 17 |
"""
n = msg.lower()
for ch in list("\t\n\r -_#.,:*") + ["`"]:
    n = n.replace(ch, "")
print(repr(n))
for s in [
    "total|56",
    "|total|56|25|17|",
    "generalmeshworkssecurity|11",
    "security095|11",
    "securityv1041|15",
    "securityv3065|19",
]:
    print(s, s in n)
