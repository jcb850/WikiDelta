from pathlib import Path

import pytest

from wikidelta.sources import fetch_source


def test_script_python_fetcher_receives_json_and_returns_artifact(tmp_path: Path):
    script = tmp_path / "fetcher.py"
    script.write_text(
        """
import json, sys
payload = json.load(sys.stdin)
print(json.dumps({"ok": True, "contentType": "text/plain", "content": payload["config"]["message"], "metadata": {"seen": payload["wdId"]}}))
""".strip(),
        encoding="utf-8",
    )

    artifact = fetch_source("script.python", {"entry": str(script), "args": {"message": "hello"}}, workspace=tmp_path, wd_id="script-doc")

    assert artifact.content == "hello"
    assert artifact.content_type == "text/plain"
    assert artifact.metadata["seen"] == "script-doc"


def test_script_python_failure_raises_clear_error(tmp_path: Path):
    script = tmp_path / "fetcher.py"
    script.write_text('import json; print(json.dumps({"ok": False, "error": {"code": "AUTH_FAILED", "message": "missing token", "retryable": False}}))', encoding="utf-8")

    with pytest.raises(RuntimeError, match="AUTH_FAILED: missing token"):
        fetch_source("script.python", {"entry": str(script)}, workspace=tmp_path, wd_id="script-doc")
