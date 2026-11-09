#!/usr/bin/env python3
"""(선택) 국가법령정보 공동활용 Open API로 의료광고 관련 판례를 모아 data/cases_auto.js 를 만듭니다.

- https://open.law.go.kr 에서 OC(사용자 ID)를 신청한 뒤 환경변수 LAW_OC 로 넘기세요.
- 판결 요지(판시사항·판결요지)만 짧게 저장하고, 인명·기관명은 ○○로 가립니다.
"""
import json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "cases_auto.js")
OC = os.environ.get("LAW_OC")
QUERIES = ["의료광고", "치료경험담", "환자유인", "전문병원 명칭", "의료법 제56조"]
TYPE_KEYS = {"effect": ["치료경험담", "치료효과", "효과"], "exag": ["과장", "거짓", "허위"], "safety": ["부작용"],
             "compare": ["비교", "비방"], "lure": ["유인", "알선", "본인부담금", "할인"], "title": ["전문병원", "자격", "명칭", "심의", "신의료기술"]}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "medad-prec-collector/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def strip(s, n=400):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = re.sub(r"(피고인|원고|피고)\s?[가-힣]{2,4}", r"\1 ○○", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n] + ("…" if len(s) > n else "")


def main():
    if not OC:
        print("LAW_OC 환경변수가 없어 판례 수집을 건너뜁니다."); return
    seen, out = set(), []
    for q in QUERIES:
        for page in range(1, 6):
            url = "https://www.law.go.kr/DRF/lawSearch.do?" + urllib.parse.urlencode({"OC": OC, "target": "prec", "type": "JSON", "query": q, "display": 100, "page": page})
            try:
                res = get(url).get("PrecSearch", {})
            except Exception as e:
                print("[warn]", e, file=sys.stderr); break
            items = res.get("prec") or []
            if isinstance(items, dict): items = [items]
            if not items: break
            for it in items:
                sid = it.get("판례일련번호")
                if not sid or sid in seen: continue
                seen.add(sid)
                try:
                    d = get("https://www.law.go.kr/DRF/lawService.do?" + urllib.parse.urlencode({"OC": OC, "target": "prec", "ID": sid, "type": "JSON"})).get("PrecService", {})
                except Exception:
                    continue
                law = d.get("참조조문", "") or ""
                if "의료법" not in law and "의료광고" not in (d.get("판시사항", "") or ""): continue
                text = (d.get("판시사항", "") or "") + (d.get("판결요지", "") or "")
                out.append({"id": "p" + sid, "src": "auto", "out": "note", "news": False, "dept": "-", "media": [],
                            "types": [k for k, w in TYPE_KEYS.items() if any(x in text for x in w)] or ["title"],
                            "title": strip(d.get("사건명", ""), 80), "ref": f'{d.get("법원명", "")} {d.get("사건번호", "")} ({d.get("선고일자", "")})',
                            "date": str(d.get("선고일자", ""))[:7], "place": "-", "phrases": [], "ad": "",
                            "law": strip(law, 160), "fact": strip(d.get("판시사항", "")), "ruling": strip(d.get("판결요지", "")),
                            "lesson": "", "url": f"https://www.law.go.kr/precInfoP.do?precSeq={sid}"})
                time.sleep(0.2)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("/* 자동 생성: collector/collect_prec.py */\nwindow.CASES_AUTO = " + json.dumps(out, ensure_ascii=False) + ";\n")
    print(f"판례 {len(out)}건 저장")


if __name__ == "__main__":
    main()
