# Copyright (c) 2026, Narpati Wisjnu Ari Pradana ("Kunderemp")
# All rights reserved.
#
# Concept and strategy by : Narpati Wisjnu Ari Pradana ("Kunderemp")
# Code authored by         : Claude Sonnet 4.6 (Anthropic)
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER "AS IS" AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN
# NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Commit:
    commit_hash: str
    author: str
    commit_date: datetime
    message: str
    commit_hash_base: Optional[str] = None
    commit_hash_source: Optional[str] = None


@dataclass
class MatchedCommit:
    source: Commit
    base: Commit
    similarity: float


@dataclass
class ClassificationResult:
    merged: list[MatchedCommit] = field(default_factory=list)
    pending: list[Commit] = field(default_factory=list)
    needs_manual_review: list[Commit] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core git helpers (original)
# ---------------------------------------------------------------------------

def git_log(branch: str, minimum_date: date) -> str:
    result = subprocess.run(
        [
            "git", "--no-pager", "log", "--first-parent",
            f"--since={minimum_date.isoformat()}",
            branch,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout


def parse_commit(commit_str: str) -> Commit:
    lines = commit_str.strip().splitlines()
    commit_hash = None
    author = None
    commit_date = None
    commit_hash_base = None
    commit_hash_source = None
    message_lines = []
    in_message = False

    for line in lines:
        if line.startswith("commit "):
            commit_hash = line.split()[1]
        elif line.startswith("Merge: "):
            parts = line.split()
            commit_hash_base = parts[1]
            commit_hash_source = parts[2]
        elif line.startswith("Author: "):
            author = line[len("Author: "):].strip()
        elif line.startswith("Date: "):
            date_str = line[len("Date:"):].strip()
            commit_date = datetime.strptime(date_str, "%a %b %d %H:%M:%S %Y %z")
        elif in_message:
            message_lines.append(line.strip())
        elif line == "":
            in_message = True

    return Commit(
        commit_hash=commit_hash,
        author=author,
        commit_date=commit_date,
        message="\n".join(message_lines).strip(),
        commit_hash_base=commit_hash_base,
        commit_hash_source=commit_hash_source,
    )


def parse_commits(log: str) -> list[Commit]:
    raw_commits = re.split(r'(?=^commit [0-9a-f]+$)', log, flags=re.MULTILINE)
    raw_commits = [c for c in raw_commits if c.strip()]
    return [parse_commit(c) for c in raw_commits]


def git_diff_name_status(commit_a: Commit, commit_b: Commit) -> list[str]:
    result = subprocess.run(
        [
            "git", "--no-pager", "diff", "--name-status",
            commit_a.commit_hash, commit_b.commit_hash,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout.splitlines()


def find_the_closest_commits_between_branch(
    source_commits: list[Commit],
    base_commits: list[Commit],
) -> Optional[list[Commit]]:
    # Newest to oldest
    sorted_base = sorted(base_commits, key=lambda c: c.commit_date, reverse=True)
    sorted_source = sorted(source_commits, key=lambda c: c.commit_date, reverse=True)

    best_pair: Optional[list[Commit]] = None

    for base_commit in sorted_base:
        # Closest source commit whose date is <= base_commit date
        source_commit = next(
            (c for c in sorted_source if c.commit_date <= base_commit.commit_date),
            None,
        )
        if source_commit is None:
            continue

        diff_lines = git_diff_name_status(source_commit, base_commit)
        changed_files = [line.split("\t", 1)[1] for line in diff_lines if "\t" in line]
        all_outside_src = all(not f.startswith("src/") for f in changed_files)

        best_pair = [source_commit, base_commit]

        if all_outside_src:
            return best_pair

    return best_pair


# ---------------------------------------------------------------------------
# New git helpers
# ---------------------------------------------------------------------------

def git_log_between(ref_start: str, ref_end: str) -> list[Commit]:
    result = subprocess.run(
        ["git", "--no-pager", "log", "--first-parent", f"{ref_start}..{ref_end}"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return parse_commits(result.stdout)


def git_diff_commit(commit_hash: str) -> str:
    try:
        result = subprocess.run(
            ["git", "--no-pager", "diff", f"{commit_hash}^..{commit_hash}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        return result.stdout or ""
    except (subprocess.CalledProcessError, UnicodeDecodeError):
        return ""


def git_diff_range(ref_start: str, ref_end: str, file_path: Optional[str] = None) -> str:
    cmd = ["git", "--no-pager", "diff", f"{ref_start}..{ref_end}"]
    if file_path:
        cmd += ["--", file_path]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=True)
    return result.stdout


def git_blame_file(commit_hash: str, file_path: str) -> list[tuple[str, str]]:
    """Return [(blame_commit_hash, stripped_line_content), ...] for every line."""
    try:
        result = subprocess.run(
            ["git", "--no-pager", "blame", "--porcelain", commit_hash, "--", file_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
    except (subprocess.CalledProcessError, UnicodeDecodeError):
        return []

    entries: list[tuple[str, str]] = []
    current_hash: Optional[str] = None

    for line in result.stdout.splitlines():
        if re.match(r'^[0-9a-f]{40} ', line):
            current_hash = line.split()[0]
        elif line.startswith("\t") and current_hash:
            entries.append((current_hash, line[1:].strip()))

    return entries


# Module-level cache so repeated calls for the same blame commit are free.
_first_parent_merge_cache: dict[tuple[str, str], Optional[str]] = {}


def find_first_parent_merge(blame_commit: str, source_latest: str) -> Optional[str]:
    """
    Return the first-parent merge commit in source_latest's ancestry that
    contains blame_commit.  The result is the oldest such commit on the
    first-parent chain — i.e. the PR merge that originally brought in the
    individual commit returned by git blame.
    """
    key = (blame_commit, source_latest)
    if key in _first_parent_merge_cache:
        return _first_parent_merge_cache[key]

    result = subprocess.run(
        [
            "git", "--no-pager", "log",
            "--ancestry-path", f"{blame_commit}^..{source_latest}",
            "--first-parent", "--format=%H",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    lines = [ln for ln in result.stdout.strip().splitlines() if ln]
    merge_commit = lines[-1] if lines else None  # full 40-char hash
    _first_parent_merge_cache[key] = merge_commit
    return merge_commit


# ---------------------------------------------------------------------------
# Diff analysis
# ---------------------------------------------------------------------------

_TRIVIAL = re.compile(r'^\s*[\{\}\(\)\[\];,]?\s*$')


def parse_added_lines(diff_str: str) -> dict[str, set[str]]:
    """
    Parse a unified diff and return {filename: {non-trivial added lines}}.
    Lines shorter than 4 chars or matching only punctuation are filtered out.
    """
    result: dict[str, set[str]] = {}
    current_file: Optional[str] = None

    for line in diff_str.splitlines():
        if line.startswith("diff --git "):
            parts = line.split(" b/", 1)
            current_file = parts[1] if len(parts) > 1 else None
        elif line.startswith("+") and not line.startswith("+++"):
            if current_file is None:
                continue
            content = line[1:].strip()
            if len(content) < 4 or _TRIVIAL.match(content):
                continue
            result.setdefault(current_file, set()).add(content)

    return result


def diff_similarity(
    diff_a: dict[str, set[str]],
    diff_b: dict[str, set[str]],
) -> float:
    """
    Jaccard similarity over shared files.
    Returns 0.0 when there are no shared files or no non-trivial lines.
    """
    shared_files = set(diff_a.keys()) & set(diff_b.keys())
    if not shared_files:
        return 0.0

    total_intersection = 0
    total_union = 0

    for f in shared_files:
        intersection = diff_a[f] & diff_b[f]
        union = diff_a[f] | diff_b[f]
        total_intersection += len(intersection)
        total_union += len(union)

    return total_intersection / total_union if total_union else 0.0


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def classify_source_commits(
    source_closest: str,
    source_latest: str,
    base_closest: str,
    base_latest: str,
    similarity_threshold: float = 0.6,
) -> ClassificationResult:
    result = ClassificationResult()

    # ---- Fetch commit lists ------------------------------------------------
    print("Fetching commit lists...")
    source_commits = git_log_between(source_closest, source_latest)
    base_commits = git_log_between(base_closest, base_latest)
    print(f"  Source commits : {len(source_commits)}")
    print(f"  Base commits   : {len(base_commits)}")

    # ---- Pre-compute base commit diffs -------------------------------------
    print("\nComputing base commit diffs...")
    base_diffs: list[tuple[Commit, dict[str, set[str]]]] = []
    for bc in base_commits:
        parsed = parse_added_lines(git_diff_commit(bc.commit_hash))
        base_diffs.append((bc, parsed))
        print(f"  {bc.commit_hash[:8]} | {bc.message[:70]}")

    # ---- Phase 1: merged (content similarity) -------------------------
    print(f"\nPhase 1: Comparing {len(source_commits)} source × {len(base_commits)} base commits...")
    merged_source_hashes: set[str] = set()

    for i, sc in enumerate(source_commits, 1):
        sc_diff = parse_added_lines(git_diff_commit(sc.commit_hash))
        if not sc_diff:
            if i % 10 == 0:
                print(f"  Progress: {i}/{len(source_commits)}")
            continue

        best_score = 0.0
        best_base: Optional[Commit] = None

        for bc, bc_diff in base_diffs:
            if not bc_diff:
                continue
            score = diff_similarity(sc_diff, bc_diff)
            if score > best_score:
                best_score = score
                best_base = bc

        if best_score >= similarity_threshold and best_base is not None:
            result.merged.append(MatchedCommit(sc, best_base, best_score))
            merged_source_hashes.add(sc.commit_hash)

        if i % 10 == 0:
            print(f"  Progress: {i}/{len(source_commits)}")

    print(f"  Found: {len(result.merged)} 'merged' commit(s)")

    # ---- Phase 2: pending (diff subtract + blame) ----------------------
    print("\nPhase 2: Computing aggregate diffs for subtract...")
    source_all = parse_added_lines(git_diff_range(source_closest, source_latest))
    base_all = parse_added_lines(git_diff_range(base_closest, base_latest))

    pending_lines: dict[str, set[str]] = {
        f: lines - base_all.get(f, set())
        for f, lines in source_all.items()
        if lines - base_all.get(f, set())
    }
    print(f"  Files with pending lines: {len(pending_lines)}")
    print("  Running git blame per file...")

    pending_hashes: set[str] = set()

    for file_path, pending in pending_lines.items():
        blame_result = git_blame_file(source_latest, file_path)
        for blame_commit, line_content in blame_result:
            if line_content not in pending:
                continue
            merge_hash = find_first_parent_merge(blame_commit, source_latest)
            if merge_hash and merge_hash not in merged_source_hashes:
                pending_hashes.add(merge_hash)

    # Map hashes back to Commit objects, preserving newest-first order
    hash_to_commit: dict[str, Commit] = {}
    for c in source_commits:
        hash_to_commit[c.commit_hash] = c
        hash_to_commit[c.commit_hash[:8]] = c

    seen_pending: set[str] = set()
    for h in pending_hashes:
        commit = hash_to_commit.get(h) or hash_to_commit.get(h[:8])
        if commit and commit.commit_hash not in seen_pending:
            result.pending.append(commit)
            seen_pending.add(commit.commit_hash)

    result.pending.sort(key=lambda c: c.commit_date, reverse=True)
    print(f"  Found: {len(result.pending)} 'pending' commit(s)")

    # ---- Phase 3: needs-manual-review (everything else) ------------------------
    classified = merged_source_hashes | {c.commit_hash for c in result.pending}
    result.needs_manual_review = [c for c in source_commits if c.commit_hash not in classified]
    print(f"  Found: {len(result.needs_manual_review)} 'needs-manual-review' commit(s)")

    return result


def print_classification(result: ClassificationResult) -> None:
    SEP = "=" * 72

    print(f"\n{SEP}")
    print(f"MERGED — {len(result.merged)} commit")
    print(SEP)
    for m in result.merged:
        print(f"  [source] {m.source.commit_hash[:8]} | {m.source.message[:62]}")
        print(f"  [base  ] {m.base.commit_hash[:8]} | {m.base.message[:62]}")
        print(f"  similarity : {m.similarity:.2f}")
        print()

    print(f"\n{SEP}")
    print(f"PENDING — {len(result.pending)} commit")
    print(SEP)
    for c in result.pending:
        print(f"  {c.commit_hash[:8]} | {c.commit_date.strftime('%Y-%m-%d')} | {c.message[:60]}")

    print(f"\n{SEP}")
    print(f"NEEDS MANUAL REVIEW — {len(result.needs_manual_review)} commit")
    print(SEP)
    for c in result.needs_manual_review:
        print(f"  {c.commit_hash[:8]} | {c.commit_date.strftime('%Y-%m-%d')} | {c.message[:60]}")


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def main_find_closest() -> None:
    if len(sys.argv) != 5:
        print("Usage: python extract_commit.py find-closest <source_branch> <base_branch> <minimum_date>")
        print("  minimum_date format: yyyy-mm-dd")
        sys.exit(1)

    source_branch = sys.argv[2]
    base_branch = sys.argv[3]
    minimum_date_str = sys.argv[4]

    try:
        minimum_date = datetime.strptime(minimum_date_str, "%Y-%m-%d").date()
    except ValueError:
        print(f"Error: minimum_date '{minimum_date_str}' is not in yyyy-mm-dd format")
        sys.exit(1)

    print(f"source_branch : {source_branch}")
    print(f"base_branch   : {base_branch}")
    print(f"minimum_date  : {minimum_date}")

    source_log = git_log(source_branch, minimum_date)
    base_log = git_log(base_branch, minimum_date)
    source_commits = parse_commits(source_log)
    base_commits = parse_commits(base_log)

    pair = find_the_closest_commits_between_branch(source_commits, base_commits)

    if pair is None:
        print("No matching commit pair found.")
    else:
        source_commit, base_commit = pair
        print(f"\nClosest pair:")
        print(f"  source: {source_commit.commit_hash} | {source_commit.commit_date} | {source_commit.message[:60]}")
        print(f"  base  : {base_commit.commit_hash} | {base_commit.commit_date} | {base_commit.message[:60]}")


def main_classify() -> None:
    if len(sys.argv) not in (6, 7):
        print("Usage: python extract_commit.py classify"
              " <source_closest> <source_latest> <base_closest> <base_latest> [threshold]")
        print("  threshold: similarity threshold 0.0-1.0, default 0.6")
        sys.exit(1)

    source_closest = sys.argv[2]
    source_latest = sys.argv[3]
    base_closest = sys.argv[4]
    base_latest = sys.argv[5]
    threshold = float(sys.argv[6]) if len(sys.argv) == 7 else 0.6

    print(f"source_closest : {source_closest}")
    print(f"source_latest  : {source_latest}")
    print(f"base_closest   : {base_closest}")
    print(f"base_latest    : {base_latest}")
    print(f"threshold      : {threshold}")
    print()

    result = classify_source_commits(
        source_closest, source_latest, base_closest, base_latest, threshold
    )
    print_classification(result)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python extract_commit.py find-closest <source_branch> <base_branch> <minimum_date in yyyy-mm-dd>")
        print("  python extract_commit.py classify"
              " <source_closest> <source_latest> <base_closest> <base_latest> [threshold]")
        sys.exit(1)

    subcommand = sys.argv[1]

    if subcommand == "find-closest":
        main_find_closest()
    elif subcommand == "classify":
        main_classify()
    else:
        # Backward compatibility: old 3-positional-arg form (no subcommand)
        if len(sys.argv) == 4:
            sys.argv.insert(1, "find-closest")
            main_find_closest()
        else:
            print(f"Unknown subcommand: '{subcommand}'")
            print("Use 'find-closest' or 'classify'.")
            sys.exit(1)


if __name__ == "__main__":
    main()
