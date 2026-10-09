"""인터넷 없이 화면을 확인할 때 쓰는 도구.

tests/fixtures 에 저장해둔 실제 응답(2026-10-06)으로 site/data/contests.json 을 만든다.
GitHub에서는 collector/collect.py 가 매일 실제 데이터로 덮어쓴다.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "collector"))
sys.path.insert(0, str(ROOT / "tests"))
import collect as C  # noqa: E402
from test_collect import fixture_sources  # noqa: E402

now = datetime(2026, 10, 6, 3, 0, tzinfo=timezone.utc)
sources = fixture_sources()
sources["연례 대회"] = C.SOURCES["연례 대회"]
data = C.collect(now, sources=sources)
data["annual"] = C.load_annual()
C.DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
C.DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
C.write_calendars(data["contests"], now)
print(len(data["contests"]), "contests")
