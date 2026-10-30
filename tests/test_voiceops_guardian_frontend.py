"""Static guardrails for the VoiceOps-styled Nebius Guardian frontend.

Do not allow visual changes to silently bypass the tested public safety contract.
"""
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess
import tempfile

import pytest


WEB = Path(__file__).resolve().parents[1] / "web" / "index.html"


class Scanner(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name == "id":
                self.ids.append(value)


def test_voiceops_style_and_semantic_controls_are_present():
    page = WEB.read_text(encoding="utf-8")
    scanner = Scanner()
    scanner.feed(page)
    assert len(scanner.ids) == len(set(scanner.ids)), "Duplicate DOM IDs"
    assert 'data-release="guardian-voiceops-visual-v2"' in page
    for marker in (
        "guardian-stage", "orbit orbit-1", "orbit orbit-2", "orbit orbit-3",
        "signal-core", "orbit-card", "guardian-evidence", "guardian-live-log",
        "guardian-operator", "LIVE LAB INCIDENT", "NEBIUS",
    ):
        assert marker in page, marker
    for button_id in (
        "runCore", "runGuided", "diagnose", "plan", "verify",
        "fetchEvidence", "inspectCloud", "download", "reset",
    ):
        assert button_id in scanner.ids, button_id


def test_frontend_keeps_real_api_and_fail_closed_boundary():
    page = WEB.read_text(encoding="utf-8")
    for path in (
        "overview", "diagnose", "actions/plan", "recovery/verify", "evidence/",
    ):
        assert path in page
    assert "LOCAL_HEURISTIC" in page
    assert "simulation:true" in page
    assert "NOT VERIFIED" in page
    assert "No call is placed here" in page
    assert "Phone approvals were tested" not in page or "not connected" in page
    assert "fetch('/api/guardian/'+path" in page
    assert "NEBIUS_LIVE_SMOKE_AUTHORIZED" not in page
    assert "approval_token" not in page
    assert "phone" not in "".join(
        part for part in page.split("<script>")[1].split("</script>")[:1]
        if "call_owner" in part
    )


def test_inline_javascript_has_valid_syntax():
    if shutil.which("node") is None:
        pytest.skip("node is not available")
    doc = WEB.read_text(encoding="utf-8")
    assert doc.count("<script>") == doc.count("</script>") == 1
    js = doc.partition("<script>")[2].partition("</script>")[0]
    with tempfile.TemporaryDirectory() as directory:
        file = Path(directory) / "guardian-ui.js"
        file.write_text(js, encoding="utf-8")
        run = subprocess.run(
            ["node", "--check", str(file)],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        assert run.returncode == 0, run.stderr
