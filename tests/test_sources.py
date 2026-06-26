from pathlib import Path

import pytest

from wikidelta.sources import fetch_source, infer_source_config, transform_content


def test_file_fetch_and_markdown_transform(tmp_path: Path):
    source = tmp_path / "a.md"
    source.write_text("# A\n\nBody", encoding="utf-8")
    config = {"path": str(source)}

    raw = fetch_source("builtin.file", config, workspace=tmp_path, wd_id="a")
    transformed = transform_content("builtin.markdown", {}, raw)

    assert raw.content_type == "text/markdown"
    assert transformed.content == "# A\n\nBody"


def test_html_transform_uses_selector():
    raw = type("Raw", (), {"content": "<html><body><nav>Skip</nav><main><h1>Hello</h1><p>Body</p></main></body></html>", "content_type": "text/html", "metadata": {}})()

    transformed = transform_content("builtin.html_to_markdown", {"selector": "main"}, raw)

    assert "Hello" in transformed.content
    assert "Body" in transformed.content
    assert "Skip" not in transformed.content


def test_json_transform_renders_markdown_code_block():
    raw = type("Raw", (), {"content": '{"a": 1}', "content_type": "application/json", "metadata": {}})()

    transformed = transform_content("builtin.json_to_markdown", {}, raw)

    assert transformed.content.startswith("```json")
    assert '"a": 1' in transformed.content


def test_infer_source_config_for_url_and_markdown_file(tmp_path: Path):
    md = tmp_path / "a.md"
    md.write_text("# A", encoding="utf-8")

    assert infer_source_config(str(md))["transformer"] == "builtin.markdown"
    assert infer_source_config("https://example.com/page")["fetcher"] == "builtin.http"


def test_infer_source_config_preserves_local_html_as_raw_text(tmp_path: Path):
    html = tmp_path / "page.html"
    html.write_text("<!doctype html><html><body><h1>Hello</h1></body></html>", encoding="utf-8")

    config = infer_source_config(str(html))

    assert config["fetcher"] == "builtin.file"
    assert config["transformer"] == "builtin.text"


def test_unknown_transformer_raises_clear_error():
    raw = type("Raw", (), {"content": "x", "content_type": "text/plain", "metadata": {}})()
    with pytest.raises(ValueError, match="Unsupported transformer"):
        transform_content("builtin.unknown", {}, raw)
