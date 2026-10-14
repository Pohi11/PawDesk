"""The demo samples' titles and descriptions follow the dashboard's copy rules (spec:
interface-copy; decision record 0018). They read the same shared list as the dashboard's
check, so one edit to the list covers both."""

import json
import re
from pathlib import Path

import pytest

from app.demo import SAMPLES

spec = pytest.mark.spec
RULES = Path(__file__).resolve().parents[2] / "docs" / "style" / "copy-rules.json"
REQUIREMENT = "Demo sample descriptions follow the same rules"


def banned_list() -> list[str]:
    return json.loads(RULES.read_text(encoding="utf-8"))["banned"]


def copy_issues(text: str, banned: list[str]) -> list[str]:
    """Banned words (whole words, any case) and em dashes, in the order found."""
    words = re.compile(r"\b(?:" + "|".join(map(re.escape, banned)) + r")\b", re.IGNORECASE)
    text = text.replace("’", "'")
    issues = [m.group(0) for m in words.finditer(text)]
    if "—" in text and text.strip() != "—":
        issues.append("—")
    return issues


@spec("interface-copy", REQUIREMENT)
def test_every_sample_title_and_description_passes():
    banned = banned_list()

    found = {
        sample.id: copy_issues(f"{sample.title}\n{sample.expect}", banned)
        for sample in SAMPLES.values()
    }

    assert found == {sample_id: [] for sample_id in SAMPLES}


@spec("interface-copy", REQUIREMENT)
def test_the_check_rejects_what_the_shared_list_bans():
    banned = banned_list()

    assert copy_issues("Simply send it", banned) == ["Simply"]
    assert copy_issues("It’s worth noting the cost", banned) == ["It's worth noting"]
    assert copy_issues("Costs — as reported", banned) == ["—"]
    assert copy_issues("Pick a sample and send it.", banned) == []
