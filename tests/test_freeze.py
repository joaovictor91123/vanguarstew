"""Tests for benchmark.freeze — the leakage-safe, knowable-at-T context builder."""

import os
import shutil
import subprocess
import sys
import tempfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from benchmark.freeze import build_context  # noqa: E402


def _commit_and_tag(repo, tag, date):
    with open(os.path.join(repo, "f.txt"), "a", encoding="utf-8") as f:
        f.write(f"{tag}\n")
    env = dict(os.environ, GIT_COMMITTER_DATE=date, GIT_AUTHOR_DATE=date)
    subprocess.run(["git", "-C", repo, "add", "-A"], check=True)
    subprocess.run(["git", "-C", repo, "commit", "-q", "-m", f"release {tag}"],
                   check=True, env=env)
    subprocess.run(["git", "-C", repo, "tag", tag], check=True, env=env)


@pytest.mark.skipif(shutil.which("git") is None, reason="git required")
def test_releases_ordered_chronologically_not_lexicographically():
    d = tempfile.mkdtemp()
    try:
        subprocess.run(["git", "init", "-q", d], check=True)
        subprocess.run(["git", "-C", d, "config", "user.email", "t@t"], check=True)
        subprocess.run(["git", "-C", d, "config", "user.name", "t"], check=True)

        # Created in this chronological order. Lexicographically, "v1.10.0" and
        # "v1.11.0" sort *before* "v1.9.0" (string comparison of "1" < "9"), so a
        # naive refname sort would misreport recency for any repo with
        # double-digit version tags.
        _commit_and_tag(d, "v1.9.0", "2024-01-01 12:00:00")
        _commit_and_tag(d, "v1.10.0", "2024-01-02 12:00:00")
        _commit_and_tag(d, "v1.11.0", "2024-01-03 12:00:00")

        ctx = build_context(d, "HEAD")
        tags = [r["tag"] for r in ctx["releases"]]

        assert tags == ["v1.9.0", "v1.10.0", "v1.11.0"]
    finally:
        shutil.rmtree(d, ignore_errors=True)
