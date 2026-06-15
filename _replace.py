import pathlib
import sys

fp = pathlib.Path(r"c:\Vibe Project\Songyan\src\songyan\workflows\_nodes.py")
c = fp.read_text(encoding="utf-8")
old = open(r"c:\Vibe Project\Songyan\_old.txt", encoding="utf-8").read()
new = open(r"c:\Vibe Project\Songyan\_new.txt", encoding="utf-8").read()
if old in c:
    c = c.replace(old, new, 1)
    fp.write_text(c, encoding="utf-8")
    print("OK")
else:
    print("NOT FOUND")
