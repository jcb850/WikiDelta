from pathlib import Path

from wikidelta.repository import Repository, find_workspace


def test_repository_creates_wikidelta_layout(tmp_path: Path):
    repo = Repository(tmp_path)

    repo.ensure_layout(mode="llmwiki_project")

    assert (tmp_path / ".wikidelta" / "config.yaml").exists()
    assert (tmp_path / ".wikidelta" / "cache").is_dir()
    assert (tmp_path / ".wikidelta" / "reviews").is_dir()
    assert (tmp_path / ".wikidelta" / "errors").is_dir()
    assert (tmp_path / ".wikidelta" / "ingest").is_dir()


def test_iter_wd_files_ignores_wikidelta_cache(tmp_path: Path):
    (tmp_path / "raw_sources").mkdir()
    (tmp_path / "raw_sources" / "a.wd").write_text("a", encoding="utf-8")
    (tmp_path / ".wikidelta" / "cache" / "x").mkdir(parents=True)
    (tmp_path / ".wikidelta" / "cache" / "x" / "ignored.wd").write_text("ignored", encoding="utf-8")

    paths = list(Repository(tmp_path).iter_wd_files())

    assert paths == [tmp_path / "raw_sources" / "a.wd"]


def test_find_workspace_uses_parent_wikidelta(tmp_path: Path):
    (tmp_path / ".wikidelta").mkdir()
    nested = tmp_path / "raw_sources" / "policy"
    nested.mkdir(parents=True)

    assert find_workspace(nested) == tmp_path
