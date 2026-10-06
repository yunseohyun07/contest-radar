"""수집기 테스트: python3 -m unittest discover tests"""
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "collector"))
import collect as C  # noqa: E402

NOW = datetime(2026, 10, 6, 3, 0, tzinfo=timezone.utc)

ATCODER_HTML = """
<div id="contest-table-upcoming"><h3>Upcoming Contests</h3><table><thead><tr><th>Start</th></tr></thead><tbody>
<tr>
<td class="text-center"><a href="http://www.timeanddate.com/worldclock/fixedtime.html?iso=20261011T2100&amp;p1=248" target="blank"><time class="fixtime-full">2026-10-11 21:00:00+0900</time></a></td>
<td><span aria-hidden="true" data-toggle="tooltip" data-placement="top" title="Algorithm">&#9398;</span><span class="user-blue">&#9673;</span> <a href="/contests/abc479">AtCoder Beginner Contest 479</a></td>
<td class="text-center">01:40</td>
<td class="text-center"> - 1999</td>
</tr>
<tr>
<td class="text-center"><a href="http://www.timeanddate.com/worldclock/fixedtime.html?iso=20261017T1500&amp;p1=248" target="blank"><time>x</time></a></td>
<td><span title="Heuristic">H</span> <a href="/contests/ahc073">AtCoder Heuristic Contest 073</a></td>
<td class="text-center">240:00</td>
<td class="text-center">-</td>
</tr>
</tbody></table></div>
"""

LINKAREER_HTML = '<html><script id="__NEXT_DATA__" type="application/json" crossorigin="anonymous">' + json.dumps({
    "props": {"pageProps": {"__APOLLO_STATE__": {
        "Activity:1": {"__typename": "Activity", "id": "1", "title": "2026 대학생 AI 앱 해커톤", "organizationName": "주최A", "recruitCloseAt": 1792940399999},
        "Activity:2": {"__typename": "Activity", "id": "2", "title": "[데이콘] 재료 물성 예측 AI 경진대회", "organizationName": "데이콘", "recruitCloseAt": 1792940399999},
        "Activity:3": {"__typename": "Activity", "id": "3", "title": "승강기 안전문화 확산 아이디어 공모전", "organizationName": "협회", "recruitCloseAt": 1792940399999},
        "Activity:4": {"__typename": "Activity", "id": "4", "title": "2026 동남 버그바운티 대회", "organizationName": "보안사", "recruitCloseAt": 1792940399999},
        "Activity:5": {"__typename": "Activity", "id": "5", "title": "공공데이터 활용 SW 공모전", "organizationName": "기관", "recruitCloseAt": 1792940399999},
    }}}
}, ensure_ascii=False) + "</script></html>"


class ParserTests(unittest.TestCase):
    def test_codeforces(self):
        items = [
            {"id": 2274, "name": "Codeforces Round (Div. 2)", "type": "CF", "phase": "BEFORE", "durationSeconds": 9000, "startTimeSeconds": 1791743700},
            {"id": 1, "name": "Old", "type": "CF", "phase": "FINISHED", "durationSeconds": 7200, "startTimeSeconds": 1000},
        ]
        out = C.parse_codeforces(items)
        self.assertEqual(len(out), 1)
        c = out[0]
        self.assertEqual(c["id"], "cf-2274")
        self.assertEqual(c["date"], "2026-10-11T18:35:00Z")  # 한국 시간 10.12 03:35
        self.assertIn({"label": "진행 시간", "value": "2시간 30분"}, c["meta"])
        self.assertIn("Div. 2", c["meta"][2]["value"])

    def test_atcoder(self):
        out = C.parse_atcoder(ATCODER_HTML)
        self.assertEqual([c["id"] for c in out], ["atc-abc479", "atc-ahc073"])
        self.assertEqual(out[0]["date"], "2026-10-11T12:00:00Z")  # 21:00 JST
        self.assertEqual(out[0]["meta"][0]["value"], "1시간 40분")
        self.assertEqual(out[0]["meta"][2]["value"], "- 1999")
        self.assertEqual(out[1]["meta"][0]["value"], "10일")
        self.assertEqual(out[1]["meta"][-1]["value"], "휴리스틱(최적화)")

    def test_atcoder_structure_change(self):
        with self.assertRaises(RuntimeError):
            C.parse_atcoder("<html>nothing</html>")

    def test_leetcode(self):
        out = C.parse_leetcode([{"title": "Weekly Contest 523", "titleSlug": "weekly-contest-523", "startTime": 1791685800, "duration": 5400}])
        self.assertEqual(out[0]["title"], "LeetCode Weekly Contest 523")
        self.assertEqual(out[0]["url"], "https://leetcode.com/contest/weekly-contest-523")
        self.assertEqual(out[0]["meta"][0]["value"], "1시간 30분")

    def test_ctftime(self):
        out = C.parse_ctftime([{
            "id": 3440, "title": "FortID CTF 2026", "start": "2026-10-09T18:00:00+00:00", "finish": "2026-10-11T18:00:00+00:00",
            "format": "Jeopardy", "onsite": False, "location": "", "restrictions": "Open", "prizes": "TBD", "weight": 45.0,
            "organizers": [{"name": "TBTL"}], "ctftime_url": "https://ctftime.org/event/3440/", "description": "Hello\r\nworld",
        }])
        c = out[0]
        self.assertEqual(c["cat"], "ai")
        self.assertEqual(c["tag"], "CTF")
        self.assertEqual(c["host"], "TBTL")
        vals = {m["label"]: m["value"] for m in c["meta"]}
        self.assertEqual(vals["진행 방식"], "온라인")
        self.assertEqual(vals["참가 자격"], "누구나")
        self.assertEqual(vals["상금"], "원문 확인")
        self.assertEqual(vals["진행 시간"], "2일")
        self.assertEqual(c["summary"], "Hello world")

    def test_linkareer_filter_and_classify(self):
        out = {c["id"]: c for c in C.parse_linkareer(LINKAREER_HTML)}
        self.assertNotIn("lk-3", out)  # IT와 관계없는 공모전은 뺀다
        self.assertEqual(out["lk-1"]["cat"], "hack")
        self.assertEqual(out["lk-2"]["cat"], "ai")
        self.assertEqual(out["lk-4"]["cat"], "ai")
        self.assertEqual(out["lk-4"]["tag"], "보안")
        self.assertEqual(out["lk-5"]["cat"], "contest")
        self.assertEqual(out["lk-1"]["kind"], "접수 마감")
        self.assertTrue(out["lk-1"]["allDay"])

    def test_duration_format(self):
        self.assertEqual(C.fmt_duration(5400), "1시간 30분")
        self.assertEqual(C.fmt_duration(7200), "2시간")
        self.assertEqual(C.fmt_duration(36 * 3600), "36시간")
        self.assertEqual(C.fmt_duration(3 * 86400), "3일")


class CollectTests(unittest.TestCase):
    def test_failed_source_keeps_previous_data(self):
        prev = {"contests": [C.make(id="x-1", source="B", title="old", date="2026-10-10T00:00:00Z")],
                "sources": {"B": {"ok": True, "lastSuccess": "2026-10-05T00:00:00Z"}}}

        def boom(now):
            raise RuntimeError("network down")

        data = C.collect(NOW, sources={
            "A": lambda now: [C.make(id="a-1", source="A", title="new", date="2026-10-08T00:00:00Z")],
            "B": boom,
        }, previous=prev)
        ids = [c["id"] for c in data["contests"]]
        self.assertEqual(ids, ["a-1", "x-1"])
        self.assertFalse(data["sources"]["B"]["ok"])
        self.assertEqual(data["sources"]["B"]["lastSuccess"], "2026-10-05T00:00:00Z")
        self.assertIn("network down", data["sources"]["B"]["error"])

    def test_sudden_zero_is_treated_as_failure(self):
        prev = {"contests": [C.make(id="x-1", source="B", title="old", date="2026-10-10T00:00:00Z")]}
        data = C.collect(NOW, sources={"B": lambda now: []}, previous=prev)
        self.assertFalse(data["sources"]["B"]["ok"])
        self.assertEqual([c["id"] for c in data["contests"]], ["x-1"])

    def test_past_and_far_future_removed(self):
        data = C.collect(NOW, sources={"A": lambda now: [
            C.make(id="past", source="A", date="2026-10-01T00:00:00Z", end="2026-10-01T02:00:00Z"),
            C.make(id="running", source="A", date="2026-10-05T00:00:00Z", end="2026-10-07T00:00:00Z"),
            C.make(id="soon", source="A", date="2026-10-20T00:00:00Z"),
            C.make(id="far", source="A", date="2027-06-01T00:00:00Z"),
        ]})
        self.assertEqual([c["id"] for c in data["contests"]], ["running", "soon"])


class CalendarTests(unittest.TestCase):
    def test_ics_output(self):
        c = C.make(id="cf-1", source="Codeforces", title="Round, with; comma", host="Codeforces", url="https://x",
                   date="2026-10-07T14:35:00Z", start="2026-10-07T14:35:00Z", end="2026-10-07T17:05:00Z")
        d = C.make(id="lk-1", source="링커리어", title="해커톤", host="주최", url="https://y", kind="접수 마감",
                   date="2026-10-14T14:59:59Z", end="2026-10-14T14:59:59Z", allDay=True)
        text = C.ics_calendar("test", [c, d], "20261006T000000Z", alarms=True)
        self.assertIn("DTSTART:20261007T143500Z", text)
        self.assertIn("SUMMARY:Round\\, with\\; comma", text)
        self.assertIn("DTSTART;VALUE=DATE:20261014", text)  # 한국 날짜 기준
        self.assertIn("DTEND;VALUE=DATE:20261015", text)
        self.assertEqual(text.count("BEGIN:VALARM"), 4)
        self.assertTrue(all(len(l.encode()) <= 75 for l in text.split("\r\n")))

    def test_fold_long_korean(self):
        line = "SUMMARY:" + "가" * 60
        folded = C.ics_fold(line)
        self.assertTrue(all(len(p.encode()) <= 75 for p in folded.split("\r\n")))
        self.assertEqual(folded.replace("\r\n ", ""), line)


if __name__ == "__main__":
    unittest.main()


FIX = Path(__file__).resolve().parent / "fixtures"


def fixture_sources():
    """실제 사이트에서 2026-10-06에 받아둔 응답으로 수집기를 돌린다 (인터넷 없이 테스트)."""
    return {
        "Codeforces": lambda now: C.parse_codeforces(json.loads((FIX / "codeforces.json").read_text())["result"]),
        "AtCoder": lambda now: C.parse_atcoder((FIX / "atcoder.html").read_text()),
        "LeetCode": lambda now: C.parse_leetcode(json.loads((FIX / "leetcode.json").read_text())["data"]["upcomingContests"]),
        "CTFtime": lambda now: C.parse_ctftime(json.loads((FIX / "ctftime.json").read_text())),
        "링커리어": lambda now: C.parse_linkareer((FIX / "linkareer_page1.html").read_text()),
    }


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.data = C.collect(NOW, sources=fixture_sources())
        self.by_id = {c["id"]: c for c in self.data["contests"]}

    def test_all_sources_ok(self):
        self.assertTrue(all(s["ok"] for s in self.data["sources"].values()), self.data["sources"])
        counts = {k: v["count"] for k, v in self.data["sources"].items()}
        self.assertEqual(counts["Codeforces"], 5)
        self.assertEqual(counts["AtCoder"], 6)
        self.assertEqual(counts["LeetCode"], 2)
        self.assertEqual(counts["CTFtime"], 10)

    def test_linkareer_real_titles(self):
        self.assertNotIn("lk-348279", self.by_id)  # Qualcomm in your life: 'it' 오탐 방지
        self.assertNotIn("lk-353034", self.by_id)  # 승강기 공모전
        self.assertNotIn("lk-344134", self.by_id)  # 논문 공모전
        self.assertNotIn("lk-350237", self.by_id)  # 스피치 대회
        self.assertEqual(self.by_id["lk-351992"]["cat"], "contest")  # IT코딩 경시대회
        self.assertEqual(self.by_id["lk-353364"]["cat"], "hack")
        self.assertEqual(self.by_id["lk-353657"]["cat"], "ai")
        self.assertEqual(self.by_id["lk-352004"]["tag"], "보안")
        self.assertEqual(self.by_id["lk-342034"]["cat"], "ai")  # DATA·AI 분석 경진대회
        self.assertIn("lk-349058", self.by_id)  # AX 경진대회

    def test_ctftime_prize_placeholders(self):
        vals = {m["label"]: m["value"] for m in self.by_id["ctf-3456"]["meta"]}
        self.assertEqual(vals["상금"], "원문 확인")  # "To be announced soon..."
        vals = {m["label"]: m["value"] for m in self.by_id["ctf-3409"]["meta"]}
        self.assertEqual(vals["진행 방식"], "오프라인 · Indonesia, Bali")
        self.assertEqual(vals["참가 자격"], "예선 통과팀")

    def test_sorted_by_date(self):
        dates = [c["date"] for c in self.data["contests"]]
        self.assertEqual(dates, sorted(dates))
