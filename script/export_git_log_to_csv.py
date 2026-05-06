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

import subprocess
import sys
from datetime import datetime


def git_log_since(minimum_date: str) -> list[str]:
    result = subprocess.run(
        [
            "git", "--no-pager", "log", "--first-parent",
            f"--since={minimum_date}",
            "--format=%H;%ci;%an;%s",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def format_line(raw_line: str) -> str:
    # git --format=%H;%ci;%an;%s  →  hash;ISO-8601 date with tz;author;subject
    parts = raw_line.split(";", 3)
    if len(parts) != 4:
        return raw_line

    commit_hash, date_str, author, subject = parts

    # Parse ISO-8601 from git (%ci = "2026-05-06 14:30:00 +0700")
    # and reformat to yyyy-MM-dd HH:mm:ss.SSS
    try:
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d %H:%M:%S %z")
        formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S.000")
    except ValueError:
        formatted_date = date_str.strip()

    return f"{commit_hash};{formatted_date};{author};{subject}"


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python export_git_log_to_csv.py <minimum_date>")
        print("  minimum_date format: yyyy-MM-dd")
        sys.exit(1)

    minimum_date_str = sys.argv[1]

    try:
        datetime.strptime(minimum_date_str, "%Y-%m-%d")
    except ValueError:
        print(f"Error: minimum_date '{minimum_date_str}' is not in yyyy-MM-dd format")
        sys.exit(1)

    lines = git_log_since(minimum_date_str)
    for line in lines:
        print(format_line(line))


if __name__ == "__main__":
    main()
