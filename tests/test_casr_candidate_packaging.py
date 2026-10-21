"""Collector packaging rejects bad inputs and excludes untracked/runtime data."""

import importlib.util
import json
from pathlib import Path
from unittest.mock import patch
import zipfile

import pytest


spec = importlib.util.spec_from_file_location(
    "casr_builder", Path(__file__).resolve().parents[1] / "scripts/build_casr_candidate.py"
)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def fixture(tmp_path, csv=b"trip_id,stop_id,stop_sequence,arrival_time,departure_time\nT,S,1,09:00:00,09:00:00\n"):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "production.db").write_bytes(b"must not ship")
    (repo / ".env").write_text("must not ship")
    static = tmp_path / "static.zip"
    with zipfile.ZipFile(static, "w") as archive:
        archive.writestr("stop_times.txt", csv)
    return repo, static


def git_output(arguments, **kwargs):
    if arguments[1] == "rev-parse":
        return "a" * 40 + "\n"
    if arguments[-1].endswith(":scripts/build_casr_candidate.py"):
        return Path(builder.__file__).read_bytes()
    return b"# committed source only\n"


def test_allowlist_and_manifest_exclude_local_data(tmp_path):
    repo, static = fixture(tmp_path)
    output = tmp_path / "candidate.zip"
    with patch.object(builder.subprocess, "check_output", side_effect=git_output):
        builder.build(repo, "main", static, output)
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == set(builder.FILES) | {
            "candidate-manifest.json", "data/static_gtfs/stop_times.txt"
        }
        manifest = json.loads(archive.read("candidate-manifest.json"))
        assert manifest["source_commit"] == "a" * 40
        assert manifest["stop_time_rows"] == 1
        assert "production.db" not in manifest["files"]


def test_refuses_overwrite(tmp_path):
    repo, static = fixture(tmp_path)
    output = tmp_path / "existing.zip"
    output.write_bytes(b"preserve")
    with pytest.raises(FileExistsError):
        builder.build(repo, "main", static, output)
    assert output.read_bytes() == b"preserve"


def test_final_manifest_requires_main_and_records_provenance(tmp_path):
    repo, static = fixture(tmp_path)
    output = tmp_path / "final.zip"
    with patch.object(builder.subprocess, "check_output", side_effect=git_output):
        builder.build(repo, "a" * 40, static, output, release="final")
    with zipfile.ZipFile(output) as archive:
        assert "candidate-manifest.json" not in archive.namelist()
        manifest = json.loads(archive.read("release-manifest.json"))
        assert manifest["release_kind"] == "final"
        assert manifest["release"] == "CASR Windows Deployment v2.1"
        assert manifest["source_commit"] == "a" * 40
        assert manifest["built_at_utc"].endswith("+00:00")
        assert set(archive.namelist()) == set(manifest["files"]) | {"release-manifest.json"}


def test_final_rejects_commit_different_from_fetched_main(tmp_path):
    repo, static = fixture(tmp_path)
    output = tmp_path / "unreviewed.zip"
    with patch.object(builder.subprocess, "check_output", side_effect=["a" * 40, "b" * 40]):
        with pytest.raises(ValueError, match="exact fetched origin/main"):
            builder.build(repo, "a" * 40, static, output, release="final")
    assert not output.exists()


def test_final_rejects_unreviewed_build_script(tmp_path):
    repo, static = fixture(tmp_path)
    output = tmp_path / "unreviewed-builder.zip"
    with patch.object(builder.subprocess, "check_output", side_effect=["a" * 40, "a" * 40, b"old builder"]):
        with pytest.raises(ValueError, match="script must match the reviewed main"):
            builder.build(repo, "a" * 40, static, output, release="final")
    assert not output.exists()


def test_refuses_repository_output(tmp_path):
    repo, static = fixture(tmp_path)
    with pytest.raises(ValueError, match="outside"):
        builder.build(repo, "main", static, repo / "candidate.zip")


@pytest.mark.parametrize("csv", [
    b"wrong,columns\n1,2\n",
    b"trip_id,stop_id,stop_sequence,arrival_time,departure_time\n",
])
def test_rejects_missing_static_columns_or_empty_data(tmp_path, csv):
    repo, static = fixture(tmp_path, csv)
    output = tmp_path / "invalid.zip"
    with patch.object(builder.subprocess, "check_output", side_effect=git_output):
        with pytest.raises(ValueError):
            builder.build(repo, "main", static, output)
    assert not output.exists()
