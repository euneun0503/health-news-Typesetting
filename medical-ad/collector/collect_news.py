#!/usr/bin/env python3
"""의료광고 위반 관련 뉴스 기사를 모아 data/news_auto.js 를 갱신합니다.

- Google 뉴스 RSS: 키 없이 사용 (기본)
- 네이버 뉴스 검색 API: 환경변수 NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 이 있으면 함께 사용
- 저장 항목: 제목, 언론사, 날짜, 링크, 자동 분류(위반 유형). 기사 본문은 저장하지 않습니다(저작권).
- 기존 파일과 합쳐 링크 기준으로 중복을 제거하므로, 매일 돌리면 계속 쌓입니다.

사용법:  python collector/collect_news.py            (실제 수집)
         python collector/collect_news.py --rss FILE (저장된 RSS 파일로 시험)
"""
import json, os, re, sys, time, html, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "news_auto.js")

QUERIES = [
    "의료광고 위반", "불법 의료광고", "의료법 위반 광고", "의료광고 벌금", "의료광고 업무정지",
    "치료경험담 광고", "의료광고 사전심의", "전문병원 명칭 광고", "병원 거짓 광고", "병원 과장 광고",
    "성형외과 광고 적발", "피부과 광고 의료법", "치과 불법 광고", "한의원 광고 의료법", "안과 광고 의료법",
    "환자 유인 알선 의료법", "체험단 후기 의료법", "병원 후기 뒷광고", "의료광고 공정위", "비급여 할인 광고",
    "의료광고 모니터링 적발", "유튜브 의료광고", "인플루언서 병원 광고", "의료기관 간판 위반", "전문의약품 광고 병원",
]

# 제목 키워드 → 위반 유형
TYPE_KEYS = {
    "effect": ["후기", "경험담", "체험", "완치", "효과", "전후", "뒷광고", "인플루언서"],
    "exag": ["과장", "거짓", "허위", "최고", "최초", "과대"],
    "safety": ["부작용", "안전"],
    "compare": ["비교", "비방"],
    "lure": ["유인", "알선", "할인", "쿠폰", "공동구매", "수수료", "무료", "본인부담", "페이백"],
    "title": ["전문병원", "전문의", "명칭", "간판", "심의", "자격", "인증", "기사형", "신의료기술"],
}
MUST = re.compile(r"(광고|후기|간판|명칭|전문병원|유인|알선|심의)")
MEDICAL = re.compile(r"(의료|병원|의원|치과|한의|성형|피부과|안과|의사|한의사|치과의사|보건소|복지부|의료법)")


def classify(title):
    return [k for k, words in TYPE_KEYS.items() if any(w in title for w in words)]


def fetch(url, headers=None, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "medad-news-collector/1.0", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def parse_google_rss(xml_bytes):
    out = []
    root = ET.fromstring(xml_bytes)
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        src = it.find("source")
        press = (src.text or "").strip() if src is not None else ""
        if press and title.endswith(" - " + press):
            title = title[: -len(" - " + press)]
        try:
            date = parsedate_to_datetime(it.findtext("pubDate") or "").strftime("%Y-%m-%d")
        except Exception:
            date = ""
        out.append({"title": html.unescape(title), "url": link, "press": press, "date": date})
    return out


def google(q):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": q, "hl": "ko", "gl": "KR", "ceid": "KR:ko"})
    return parse_google_rss(fetch(url))


def naver(q):
    cid, sec = os.environ.get("NAVER_CLIENT_ID"), os.environ.get("NAVER_CLIENT_SECRET")
    if not (cid and sec):
        return []
    out = []
    for start in (1, 101):
        url = "https://openapi.naver.com/v1/search/news.json?" + urllib.parse.urlencode({"query": q, "display": 100, "start": start, "sort": "date"})
        data = json.loads(fetch(url, {"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": sec}))
        for it in data.get("items", []):
            title = re.sub(r"<[^>]+>", "", html.unescape(it.get("title", "")))
            link = it.get("originallink") or it.get("link")
            try:
                date = parsedate_to_datetime(it.get("pubDate", "")).strftime("%Y-%m-%d")
            except Exception:
                date = ""
            host = urllib.parse.urlparse(link).netloc.replace("www.", "")
            out.append({"title": title, "url": link, "press": host, "date": date})
        time.sleep(0.2)
    return out


def load_existing():
    if not os.path.exists(OUT):
        return []
    txt = open(OUT, encoding="utf-8").read()
    m = re.search(r"=\s*(\[.*\])\s*;?\s*$", txt, re.S)
    return json.loads(m.group(1)) if m else []


def save(items):
    items.sort(key=lambda x: x.get("date", ""), reverse=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("/* 자동 생성: collector/collect_news.py — 직접 수정하지 마세요 */\n")
        f.write("window.NEWS_AUTO = " + json.dumps(items, ensure_ascii=False, indent=0) + ";\n")


def keep(item):
    t = item["title"]
    return bool(MUST.search(t) and MEDICAL.search(t))


def main():
    found = []
    if "--rss" in sys.argv:  # 오프라인 시험
        found = parse_google_rss(open(sys.argv[sys.argv.index("--rss") + 1], "rb").read())
    else:
        for q in QUERIES:
            for fn in (google, naver):
                try:
                    found += fn(q)
                except Exception as e:
                    print(f"[warn] {fn.__name__}({q}): {e}", file=sys.stderr)
                time.sleep(0.5)
    existing = load_existing()
    seen = {x["url"] for x in existing}
    seen_title = {re.sub(r"\s", "", x["title"]) for x in existing}
    added = 0
    for it in found:
        key_t = re.sub(r"\s", "", it["title"])
        if not it["url"] or it["url"] in seen or key_t in seen_title or not keep(it):
            continue
        it["types"] = classify(it["title"])
        existing.append(it)
        seen.add(it["url"]); seen_title.add(key_t); added += 1
    save(existing)
    print(f"수집 {len(found)}건 → 신규 {added}건, 누적 {len(existing)}건")


if __name__ == "__main__":
    main()
