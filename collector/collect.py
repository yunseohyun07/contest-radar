"""대회 레이더 수집기.

여러 사이트에서 앞으로 열릴 대회를 모아 site/data/contests.json 과
캘린더 파일(site/feeds/*.ics, site/ics/<id>.ics)을 만든다.

- 파이썬 기본 라이브러리만 사용한다 (설치할 것 없음).
- 출처 하나가 실패해도 나머지는 계속 수집하고,
  실패한 출처는 지난번에 모아둔 데이터를 그대로 유지한다.

실행:  python3 collector/collect.py
"""
from __future__ import annotations

import html
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DATA_FILE = SITE / "data" / "contests.json"

KST = timezone(timedelta(hours=9))
JST = KST  # 일본 표준시는 한국 시간과 같다
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0 Safari/537.36 contest-radar/1.0"
)
LOOKAHEAD_DAYS = 90  # 이 기간 안에 있는 대회만 보여준다


# ---------------------------------------------------------------- helpers

def http_get(url: str, *, data: bytes | None = None, headers: dict | None = None, timeout: int = 25) -> str:
    h = {"User-Agent": UA, "Accept-Language": "ko,en;q=0.8"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method="POST" if data else "GET")
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")
        except Exception as e:  # noqa: BLE001 - 어떤 오류든 재시도
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"{url} 요청 실패: {last}")


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def from_ts(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def fmt_duration(seconds: int) -> str:
    seconds = int(seconds)
    if seconds >= 86400 and seconds % 3600 == 0 and seconds // 3600 >= 48:
        return f"{seconds // 86400}일" + (f" {seconds % 86400 // 3600}시간" if seconds % 86400 else "")
    h, m = divmod(seconds // 60, 60)
    if h and m:
        return f"{h}시간 {m}분"
    return f"{h}시간" if h else f"{m}분"


def clean_text(s: str, limit: int = 400) -> str:
    s = re.sub(r"\s+", " ", html.unescape(s or "")).strip()
    return s if len(s) <= limit else s[: limit - 1].rstrip() + "…"


def make(**kw) -> dict:
    """대회 하나를 앱이 쓰는 공통 모양으로 만든다."""
    base = {
        "id": "",
        "source": "",
        "cat": "algo",  # algo | hack | contest | ai
        "title": "",
        "host": "",
        "url": "",
        "kind": "대회일",  # 목록에서 날짜 옆에 붙는 말 (대회일 / 접수 마감)
        "date": "",  # 목록 정렬과 D-day 기준이 되는 날짜 (UTC ISO)
        "start": None,
        "end": None,
        "allDay": False,
        "meta": [],  # [{"label": "참가 자격", "value": "누구나"}, ...]
        "summary": "",
    }
    base.update(kw)
    return base


# ---------------------------------------------------------------- sources

def codeforces() -> list[dict]:
    raw = json.loads(http_get("https://codeforces.com/api/contest.list?gym=false"))
    if raw.get("status") != "OK":
        raise RuntimeError(f"Codeforces 응답 이상: {raw.get('comment')}")
    return parse_codeforces(raw["result"])


def parse_codeforces(items: list[dict]) -> list[dict]:
    out = []
    for c in items:
        if c.get("phase") != "BEFORE" or not c.get("startTimeSeconds"):
            continue
        start = from_ts(c["startTimeSeconds"])
        dur = int(c.get("durationSeconds") or 0)
        name = c["name"]
        div = re.search(r"Div\.\s*[1-4](?:\s*\+\s*Div\.\s*[1-4])?", name)
        out.append(make(
            id=f"cf-{c['id']}", source="Codeforces", cat="algo", title=name, host="Codeforces",
            url=f"https://codeforces.com/contests/{c['id']}",
            date=iso(start), start=iso(start), end=iso(start + timedelta(seconds=dur)),
            meta=[
                {"label": "진행 시간", "value": fmt_duration(dur)},
                {"label": "진행 방식", "value": "온라인"},
                {"label": "참가 자격", "value": f"누구나 ({div.group(0)})" if div else "누구나"},
                {"label": "팀 구성", "value": "개인"},
            ],
        ))
    return out


def atcoder() -> list[dict]:
    return parse_atcoder(http_get("https://atcoder.jp/contests/?lang=en"))


def parse_atcoder(page: str) -> list[dict]:
    m = re.search(r'id="contest-table-upcoming"(.*?)</table>', page, re.S)
    if not m:
        raise RuntimeError("AtCoder 예정 대회 표를 찾지 못했어요 (사이트 구조 변경?)")
    out = []
    for row in re.findall(r"<tr>(.*?)</tr>", m.group(1), re.S):
        t = re.search(r"iso=(\d{8}T\d{4})", row)
        a = re.search(r'href="/contests/([\w-]+)"[^>]*>(.*?)</a>', row, re.S)
        if not (t and a):
            continue
        start = datetime.strptime(t.group(1), "%Y%m%dT%H%M").replace(tzinfo=JST)
        tds = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        dur_txt = clean_text(re.sub(r"<[^>]+>", "", tds[2])) if len(tds) > 2 else ""
        rated = clean_text(re.sub(r"<[^>]+>", "", tds[3])) if len(tds) > 3 else ""
        kind = re.search(r'data-original-title="(\w+)"', row) or re.search(r'title="(\w+)"', row)
        dur = 0
        dm = re.match(r"(\d+):(\d+)", dur_txt)
        if dm:
            dur = int(dm.group(1)) * 3600 + int(dm.group(2)) * 60
        meta = [
            {"label": "진행 시간", "value": fmt_duration(dur) if dur else dur_txt or "원문 확인"},
            {"label": "진행 방식", "value": "온라인"},
            {"label": "레이팅 범위", "value": rated if rated and rated != "-" else "Unrated"},
            {"label": "팀 구성", "value": "개인"},
        ]
        if kind and kind.group(1) == "Heuristic":
            meta.append({"label": "종류", "value": "휴리스틱(최적화)"})
        out.append(make(
            id=f"atc-{a.group(1)}", source="AtCoder", cat="algo",
            title=clean_text(re.sub(r"<[^>]+>", "", a.group(2))), host="AtCoder",
            url=f"https://atcoder.jp/contests/{a.group(1)}",
            date=iso(start), start=iso(start), end=iso(start + timedelta(seconds=dur)), meta=meta,
        ))
    return out


def leetcode() -> list[dict]:
    body = json.dumps({"query": "{ upcomingContests { title titleSlug startTime duration } }"}).encode()
    raw = json.loads(http_get(
        "https://leetcode.com/graphql", data=body,
        headers={"Content-Type": "application/json", "Referer": "https://leetcode.com/contest/"},
    ))
    return parse_leetcode(raw["data"]["upcomingContests"])


def parse_leetcode(items: list[dict]) -> list[dict]:
    out = []
    for c in items:
        start = from_ts(c["startTime"])
        dur = int(c.get("duration") or 0)
        out.append(make(
            id=f"lc-{c['titleSlug']}", source="LeetCode", cat="algo", title=f"LeetCode {c['title']}",
            host="LeetCode", url=f"https://leetcode.com/contest/{c['titleSlug']}",
            date=iso(start), start=iso(start), end=iso(start + timedelta(seconds=dur)),
            meta=[
                {"label": "진행 시간", "value": fmt_duration(dur)},
                {"label": "진행 방식", "value": "온라인"},
                {"label": "참가 자격", "value": "누구나"},
                {"label": "팀 구성", "value": "개인"},
            ],
        ))
    return out


def ctftime(now: datetime) -> list[dict]:
    start = int(now.timestamp())
    finish = int((now + timedelta(days=LOOKAHEAD_DAYS)).timestamp())
    raw = json.loads(http_get(f"https://ctftime.org/api/v1/events/?limit=200&start={start}&finish={finish}"))
    return parse_ctftime(raw)


def parse_ctftime(items: list[dict]) -> list[dict]:
    out = []
    for e in items:
        start = datetime.fromisoformat(e["start"])
        end = datetime.fromisoformat(e["finish"])
        restr = {"Open": "누구나", "Academic": "학생", "High-school": "고등학생", "Prequalified": "예선 통과팀",
                 "Individual": "개인 참가"}.get(e.get("restrictions") or "", e.get("restrictions") or "원문 확인")
        prizes = clean_text(e.get("prizes") or "", 80)
        meta = [
            {"label": "형식", "value": e.get("format") or "원문 확인"},
            {"label": "진행 방식", "value": "오프라인" + (f" · {e['location']}" if e.get("location") else "") if e.get("onsite") else "온라인"},
            {"label": "참가 자격", "value": restr},
            {"label": "진행 시간", "value": fmt_duration((end - start).total_seconds())},
            {"label": "상금", "value": prizes if prizes and not NO_PRIZE.match(prizes) else "원문 확인"},
        ]
        if e.get("weight"):
            meta.append({"label": "CTFtime 가중치", "value": f"{float(e['weight']):g}"})
        orgs = ", ".join(o.get("name", "") for o in e.get("organizers") or []) or "CTFtime"
        out.append(make(
            id=f"ctf-{e['id']}", source="CTFtime", cat="ai", title=e["title"], host=orgs,
            url=e.get("ctftime_url") or e.get("url") or "https://ctftime.org/",
            date=iso(start), start=iso(start), end=iso(end), meta=meta,
            summary=clean_text(e.get("description") or "", 360), tag="CTF",
        ))
    return out


# 영어 약어(AI, IT 등)는 대문자로, 다른 영어 단어 속에 끼어 있지 않을 때만 인정한다
# ("Qualcomm in your life" 같은 제목이 'it' 때문에 걸리지 않도록)
_EN = r"(?<![A-Za-z])(?:AI|AX|IT|ICT|SW|S/W|CTF|LLM|DATA|DACON|App|APP)(?![A-Za-z])"
IT_WORDS = re.compile(
    _EN + r"|인공지능|소프트웨어|코딩|프로그래밍|알고리즘|해커톤|[Hh]ackathon|개발|앱|어플|데이터|보안|해킹|버그바운티|"
    r"메타버스|로봇|게임|웹|블록체인|클라우드|디지털|데이콘|머신러닝|딥러닝|에이전트|자율주행|드론|핀테크"
)
NO_PRIZE = re.compile(r"^\s*(TBD|TBA|TDB|N/?A|-|to be (announced|determined).*)\s*$", re.I | re.S)


def classify_kr(title: str) -> tuple[str, str | None]:
    """국내 공모전 제목으로 종류(cat)와 작은 태그를 정한다."""
    if re.search(r"해커톤|hackathon", title, re.I):
        return "hack", None
    if re.search(r"보안|해킹|CTF|버그바운티", title, re.I):
        return "ai", "보안"
    if re.search(r"데이콘|DACON|경진대회|챌린지", title, re.I) and re.search(
        r"(?<![A-Za-z])(AI|LLM|DATA)(?![A-Za-z])|인공지능|데이터|머신러닝|딥러닝|예측|모델|에이전트", title
    ):
        return "ai", "AI"
    return "contest", None


def linkareer(now: datetime) -> list[dict]:
    out, seen = [], set()
    for page in range(1, 6):
        url = (
            "https://linkareer.com/list/contest?filterBy_categoryIDs=35&filterType=CATEGORY"
            f"&orderBy_direction=DESC&orderBy_field=CREATED_AT&page={page}"
        )
        items = parse_linkareer(http_get(url))
        new = [c for c in items if c["id"] not in seen]
        if not new:
            break
        for c in new:
            seen.add(c["id"])
        out.extend(new)
        time.sleep(1.5)  # 사이트에 부담 주지 않게 천천히
    return out


def parse_linkareer(page: str) -> list[dict]:
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', page, re.S)
    if not m:
        raise RuntimeError("링커리어 데이터(__NEXT_DATA__)를 찾지 못했어요 (사이트 구조 변경?)")
    state = json.loads(m.group(1))["props"]["pageProps"].get("__APOLLO_STATE__") or {}
    out = []
    for v in state.values():
        if not isinstance(v, dict) or v.get("__typename") != "Activity":
            continue
        title = clean_text(v.get("title") or "", 200)
        if not title or not IT_WORDS.search(title) or not v.get("recruitCloseAt"):
            continue
        close = from_ts(v["recruitCloseAt"] / 1000)
        cat, tag = classify_kr(title)
        host = v.get("organizationName") or "원문 확인"
        out.append(make(
            id=f"lk-{v['id']}", source="링커리어", cat=cat, title=title, host=host,
            url=f"https://linkareer.com/activity/{v['id']}", kind="접수 마감",
            date=iso(close), start=None, end=iso(close), allDay=True,
            meta=[
                {"label": "상금", "value": "원문 확인"},
                {"label": "참가 자격", "value": "원문 확인"},
                {"label": "팀 구성", "value": "원문 확인"},
            ],
            tag=tag,
        ))
    return out


SOURCES = {
    "Codeforces": lambda now: codeforces(),
    "AtCoder": lambda now: atcoder(),
    "LeetCode": lambda now: leetcode(),
    "CTFtime": ctftime,
    "링커리어": linkareer,
}


# ---------------------------------------------------------------- calendar files

def ics_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def ics_fold(line: str) -> str:
    raw = line.encode()
    if len(raw) <= 74:
        return line
    parts, cur = [], b""
    for ch in line:
        b = ch.encode()
        if len(cur) + len(b) > 73:
            parts.append(cur.decode())
            cur = b""
        cur += b
    parts.append(cur.decode())
    return "\r\n ".join(parts)


def ics_dt(s: str) -> str:
    return s.replace("-", "").replace(":", "")


def ics_event(c: dict, stamp: str, alarms: bool) -> list[str]:
    lines = ["BEGIN:VEVENT", f"UID:{c['id']}@contest-radar", f"DTSTAMP:{stamp}"]
    if c.get("allDay"):
        d = datetime.fromisoformat(c["date"].replace("Z", "+00:00")).astimezone(KST).date()
        lines += [f"DTSTART;VALUE=DATE:{d:%Y%m%d}", f"DTEND;VALUE=DATE:{d + timedelta(days=1):%Y%m%d}"]
        summary = f"[{c['kind']}] {c['title']}"
    else:
        lines += [f"DTSTART:{ics_dt(c['start'])}", f"DTEND:{ics_dt(c['end'] or c['start'])}"]
        summary = c["title"]
    lines += [f"SUMMARY:{ics_escape(summary)}", f"URL:{c['url']}",
              f"DESCRIPTION:{ics_escape(c['host'] + chr(10) + c['url'])}"]
    if alarms:
        for trig, label in (("-P3D", "3일 전"), ("-P1D", "하루 전")):
            lines += ["BEGIN:VALARM", "ACTION:DISPLAY", f"TRIGGER:{trig}",
                      f"DESCRIPTION:{ics_escape(label + ': ' + c['title'])}", "END:VALARM"]
    lines.append("END:VEVENT")
    return lines


def ics_calendar(name: str, events: list[dict], stamp: str, alarms: bool) -> str:
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//contest-radar//KO", "CALSCALE:GREGORIAN",
             f"X-WR-CALNAME:{ics_escape(name)}", "X-WR-TIMEZONE:Asia/Seoul",
             "REFRESH-INTERVAL;VALUE=DURATION:PT12H", "X-PUBLISHED-TTL:PT12H"]
    for c in events:
        lines += ics_event(c, stamp, alarms)
    lines.append("END:VCALENDAR")
    return "\r\n".join(ics_fold(l) for l in lines) + "\r\n"


def write_calendars(contests: list[dict], now: datetime) -> None:
    stamp = ics_dt(iso(now))
    feeds, single = SITE / "feeds", SITE / "ics"
    feeds.mkdir(parents=True, exist_ok=True)
    single.mkdir(parents=True, exist_ok=True)
    for old in single.glob("*.ics"):
        old.unlink()
    names = {"all": "대회 레이더 · 전체", "algo": "대회 레이더 · 알고리즘", "hack": "대회 레이더 · 해커톤",
             "contest": "대회 레이더 · 공모전", "ai": "대회 레이더 · CTF·AI"}
    for key, name in names.items():
        evs = [c for c in contests if key == "all" or c["cat"] == key]
        (feeds / f"{key}.ics").write_text(ics_calendar(name, evs, stamp, alarms=False), encoding="utf-8")
    for c in contests:
        (single / f"{c['id']}.ics").write_text(ics_calendar(c["title"], [c], stamp, alarms=True), encoding="utf-8")


# ---------------------------------------------------------------- main

def collect(now: datetime | None = None, sources: dict | None = None, previous: dict | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    sources = sources or SOURCES
    previous = previous or {}
    prev_by_source: dict[str, list] = {}
    for c in previous.get("contests", []):
        prev_by_source.setdefault(c["source"], []).append(c)
    prev_status = previous.get("sources", {})

    contests, status = [], {}
    for name, fn in sources.items():
        try:
            items = fn(now)
            if not items and prev_by_source.get(name):
                # 갑자기 0개면 구조가 바뀐 것일 수 있으니 의심한다
                raise RuntimeError("대회가 0개로 나왔어요 (사이트 구조 변경 가능성)")
            status[name] = {"ok": True, "count": len(items), "checkedAt": iso(now), "lastSuccess": iso(now)}
            contests.extend(items)
            print(f"  ✓ {name}: {len(items)}개")
        except Exception as e:  # noqa: BLE001
            kept = prev_by_source.get(name, [])
            status[name] = {
                "ok": False, "count": len(kept), "checkedAt": iso(now), "error": str(e)[:300],
                "lastSuccess": prev_status.get(name, {}).get("lastSuccess"),
            }
            contests.extend(kept)
            print(f"  ✗ {name}: 실패 → 이전 데이터 {len(kept)}개 유지 ({e})", file=sys.stderr)

    lo = now - timedelta(hours=3)
    hi = now + timedelta(days=LOOKAHEAD_DAYS)
    uniq = {}
    for c in contests:
        d = datetime.fromisoformat(c["date"].replace("Z", "+00:00"))
        end = datetime.fromisoformat((c.get("end") or c["date"]).replace("Z", "+00:00"))
        if end >= lo and d <= hi:
            uniq[c["id"]] = c
    result = sorted(uniq.values(), key=lambda c: (c["date"], c["title"]))
    return {"updatedAt": iso(now), "sources": status, "contests": result}


def main() -> int:
    now = datetime.now(timezone.utc)
    previous = {}
    if DATA_FILE.exists():
        try:
            previous = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except ValueError:
            previous = {}
    print("대회 수집 시작")
    data = collect(now, previous=previous)
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    write_calendars(data["contests"], now)
    ok = sum(1 for s in data["sources"].values() if s["ok"])
    print(f"완료: 대회 {len(data['contests'])}개, 출처 {ok}/{len(data['sources'])}개 성공")
    return 0 if ok else 1  # 전부 실패했을 때만 실패로 표시


if __name__ == "__main__":
    sys.exit(main())
