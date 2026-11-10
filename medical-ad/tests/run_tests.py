#!/usr/bin/env python3
"""오탐/미탐 회귀 테스트. 필요: pip install playwright && playwright install chromium
    python medical-ad/tests/run_tests.py
"""
import json, os, sys
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = json.load(open(os.path.join(ROOT, "tests", "regression.json"), encoding="utf-8"))
fail = 0
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("file://" + os.path.join(ROOT, "index.html"))
    for s in T["neg"]:
        h = pg.evaluate("s=>analyze(s).hits.map(x=>x.text+' ['+x.rule.cat+']')", s)
        if h: fail += 1; print("오탐 ✗", s, "→", h)
    for s, want in T["pos"]:
        h = pg.evaluate("s=>analyze(s).hits.map(x=>x.text)", s)
        if not any(want in x for x in h): fail += 1; print("미탐 ✗", s, "→", h)
    for s in T["spellNeg"]:
        h = pg.evaluate("s=>analyze(s).sp.map(x=>x.text+'>'+x.rep)", s)
        if h: fail += 1; print("맞춤법 오탐 ✗", s, "→", h)
    for s, bad in T.get("badOpts", []):
        o = pg.evaluate("s=>analyze(s).hits.flatMap(x=>x.opts)", s)
        if bad in o: fail += 1; print("어색한 대치어 ✗", s, "→", o)
    if errs: fail += 1; print("JS 오류", errs)
    b.close()
total = len(T["neg"]) + len(T["pos"]) + len(T["spellNeg"]) + len(T.get("badOpts", []))
print(f"{total - fail}/{total} 통과")
sys.exit(1 if fail else 0)
