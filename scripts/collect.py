#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
경향 문화 멤버십 — 공연·전시 데이터 수집기

수집원
  1) KOPIS 공연예술통합전산망 OpenAPI   → 연극/뮤지컬/클래식/무용/국악
  2) 문화포털(문화체육관광부) OpenAPI    → 전시/미술

출력
  data/events.json   (플랫폼이 바로 읽는 정규화 형식)
  data/raw/*.xml     (원본 보관, 장애 시 재처리용)

사용
  export KOPIS_KEY=발급받은키
  export CULTURE_KEY=발급받은키
  python scripts/collect.py --days 90
"""

import os
import sys
import json
import argparse
import datetime as dt
import xml.etree.ElementTree as ET
from urllib import request, parse
from urllib.error import URLError, HTTPError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
RAW = os.path.join(DATA, "raw")

KOPIS_KEY = os.environ.get("KOPIS_KEY", "")
CULTURE_KEY = os.environ.get("CULTURE_KEY", "")

KOPIS_LIST = "http://www.kopis.or.kr/openApi/restful/pblprfr"
CULTURE_LIST = "http://www.culture.go.kr/openapi/rest/publicperformancedisplays/period"

# KOPIS 장르코드 → 우리 분류
GENRE = {
    "AAAA": "연극", "AAAB": "무용", "BBBC": "클래식",
    "BBBE": "국악", "GGGA": "뮤지컬",
}

# 다루는 장르: 연극 · 뮤지컬 · 클래식 · 무용 · 국악 (+ 전시는 문화포털에서 수집)
COLLECT_GENRES = ["AAAA", "AAAB", "BBBC", "BBBE", "GGGA"]

SIDO = {
    "11": "서울", "26": "부산", "27": "대구", "28": "인천", "29": "광주",
    "30": "대전", "31": "울산", "36": "세종", "41": "경기", "43": "충북",
    "44": "충남", "45": "전북", "46": "전남", "47": "경북", "48": "경남",
    "50": "제주", "51": "강원",
}


def log(msg):
    print("[collect] " + msg, flush=True)


def fetch(url, params, retries=3):
    """XML 응답을 문자열로 반환. 실패하면 None."""
    qs = parse.urlencode(params, doseq=True)
    full = url + "?" + qs
    for i in range(retries):
        try:
            req = request.Request(full, headers={"User-Agent": "kh-culture/1.0"})
            with request.urlopen(req, timeout=20) as r:
                return r.read().decode("utf-8", "replace")
        except (URLError, HTTPError) as e:
            log("  요청 실패 (%d/%d): %s" % (i + 1, retries, e))
    return None


def text(node, tag, default=""):
    el = node.find(tag)
    if el is None or el.text is None:
        return default
    return el.text.strip()


def norm_date(s):
    """20260813 또는 2026.08.13 → 2026-08-13"""
    s = (s or "").replace(".", "").replace("-", "").strip()
    if len(s) != 8 or not s.isdigit():
        return ""
    return "%s-%s-%s" % (s[0:4], s[4:6], s[6:8])


# ─────────────────────────────────────────────
# 1. KOPIS 공연
# ─────────────────────────────────────────────
def collect_kopis(start, end, sido=None):
    if not KOPIS_KEY:
        log("KOPIS_KEY 없음 — 공연 수집 건너뜀")
        return []

    out = []
    for gcode in COLLECT_GENRES:
        page = 1
        while True:
            params = {
                "service": KOPIS_KEY,
                "stdate": start.strftime("%Y%m%d"),
                "eddate": end.strftime("%Y%m%d"),
                "cpage": page,
                "rows": 100,
                "shcate": gcode,
            }
            if sido:
                params["signgucode"] = sido

            body = fetch(KOPIS_LIST, params)
            if not body:
                break

            save_raw("kopis_%s_p%d.xml" % (gcode, page), body)

            try:
                root = ET.fromstring(body)
            except ET.ParseError:
                log("  XML 파싱 실패: %s p%d" % (gcode, page))
                break

            rows = root.findall("db")
            if not rows:
                break

            for db in rows:
                out.append({
                    "id": "kopis:" + text(db, "mt20id"),
                    "source": "KOPIS",
                    "kind": "공연",
                    "genre": GENRE.get(gcode, "기타"),
                    "title": text(db, "prfnm"),
                    "venue": text(db, "fcltynm"),
                    "region": text(db, "area"),
                    "start": norm_date(text(db, "prfpdfrom")),
                    "end": norm_date(text(db, "prfpdto")),
                    "poster": text(db, "poster"),
                    "state": text(db, "prfstate"),
                    "openrun": text(db, "openrun") == "Y",
                })

            log("  KOPIS %s p%d — %d건" % (GENRE.get(gcode, gcode), page, len(rows)))
            if len(rows) < 100:
                break
            page += 1
            if page > 30:  # 안전장치
                break

    return out


# ─────────────────────────────────────────────
# 2. 문화포털 전시
# ─────────────────────────────────────────────
def collect_culture(start, end):
    if not CULTURE_KEY:
        log("CULTURE_KEY 없음 — 전시 수집 건너뜀")
        return []

    out = []
    page = 1
    while True:
        params = {
            "serviceKey": CULTURE_KEY,
            "from": start.strftime("%Y%m%d"),
            "to": end.strftime("%Y%m%d"),
            "cPage": page,
            "rows": 100,
            "sortStdr": "1",
        }
        body = fetch(CULTURE_LIST, params)
        if not body:
            break

        save_raw("culture_p%d.xml" % page, body)

        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            log("  XML 파싱 실패: 문화포털 p%d" % page)
            break

        rows = root.findall(".//perforList")
        if not rows:
            break

        for it in rows:
            realm = text(it, "realmName")
            # 전시·미술 계열만 취한다 (공연은 KOPIS가 더 정확)
            if realm not in ("미술", "전시"):
                continue
            out.append({
                "id": "culture:" + text(it, "seq"),
                "source": "문화포털",
                "kind": "전시",
                "genre": "전시",
                "title": text(it, "title"),
                "venue": text(it, "place"),
                "region": text(it, "area"),
                "start": norm_date(text(it, "startDate")),
                "end": norm_date(text(it, "endDate")),
                "poster": text(it, "thumbnail"),
                "state": "",
                "openrun": False,
            })

        log("  문화포털 p%d — %d건" % (page, len(rows)))
        if len(rows) < 100:
            break
        page += 1
        if page > 30:
            break

    return out


# ─────────────────────────────────────────────
# 후처리
# ─────────────────────────────────────────────
def save_raw(name, body):
    os.makedirs(RAW, exist_ok=True)
    with open(os.path.join(RAW, name), "w", encoding="utf-8") as f:
        f.write(body)


def dedupe(items):
    """같은 제목 + 같은 공간 + 같은 시작일이면 하나로 본다."""
    seen = {}
    for it in items:
        key = (it["title"].replace(" ", ""), it["venue"].replace(" ", ""), it["start"])
        if key in seen:
            continue
        seen[key] = it
    return list(seen.values())


def enrich(items):
    """플랫폼이 쓰는 필드를 붙인다. 큐레이션·할인율은 관리자가 편성 화면에서 채운다."""
    today = dt.date.today().isoformat()
    for it in items:
        it["curated"] = False        # 큐레이션 노출 여부
        it["curationNote"] = ""      # 선정 이유 (필수)
        it["discount"] = None        # 회원 할인율 (제휴 계약 후 입력)
        it["partner"] = False        # 제휴처 여부
        it["rating"] = 0.0           # 회원 평점 (후기 누적으로 계산)
        it["reviewCount"] = 0
        it["collectedAt"] = today
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90, help="오늘부터 며칠 뒤까지 수집할지")
    ap.add_argument("--sido", default=None, help="KOPIS 지역코드 (예: 11 서울)")
    ap.add_argument("--out", default=os.path.join(DATA, "events.json"))
    args = ap.parse_args()

    start = dt.date.today()
    end = start + dt.timedelta(days=args.days)
    log("수집 기간 %s ~ %s" % (start, end))

    items = []
    items += collect_kopis(start, end, args.sido)
    items += collect_culture(start, end)

    if not items:
        log("수집된 항목이 없습니다. API 키와 네트워크를 확인하세요.")
        sys.exit(1)

    items = enrich(dedupe(items))
    items.sort(key=lambda x: (x["start"] or "9999", x["title"]))

    os.makedirs(DATA, exist_ok=True)
    payload = {
        "updatedAt": dt.datetime.now().isoformat(timespec="seconds"),
        "range": {"from": start.isoformat(), "to": end.isoformat()},
        "count": len(items),
        "events": items,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    by_genre = {}
    for it in items:
        by_genre[it["genre"]] = by_genre.get(it["genre"], 0) + 1

    log("완료 — 총 %d건" % len(items))
    for g, n in sorted(by_genre.items(), key=lambda x: -x[1]):
        log("   %s %d" % (g, n))
    log("저장 → %s" % args.out)


if __name__ == "__main__":
    main()
