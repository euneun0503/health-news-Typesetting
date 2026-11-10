#!/usr/bin/env python3
"""data/reference.js, data/cases.js 를 index.html 안에 내장합니다.
index.html 하나만 열어도 동작하게 하기 위함입니다. 데이터 파일을 고친 뒤 실행하세요:
    python medical-ad/build.py
"""
import os, re

ROOT = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(ROOT, "index.html")


def embed(html, name):
    src = open(os.path.join(ROOT, "data", name), encoding="utf-8").read()
    marker = f"/* ==== data/{name} (내장) ==== */"
    pat = re.compile(re.escape(marker) + r"\n.*?\n</script>", re.S)
    if not pat.search(html):
        raise SystemExit(f"marker not found: {marker}")
    return pat.sub(lambda m: marker + "\n" + src + "\n</script>", html, count=1)


html = open(INDEX, encoding="utf-8").read()
for n in ("reference.js", "cases.js"):
    html = embed(html, n)
open(INDEX, "w", encoding="utf-8").write(html)
print("embedded reference.js, cases.js")
