#!/usr/bin/env python3
"""commit-canvas: write text into your GitHub contribution graph.

Each lit pixel of a 7-row pixel font becomes one day with N backdated commits.
Columns are weeks (Sunday at the top), so text can run across as many years
as it needs.

By default the script only prints a preview. Pass --repo to actually write
commits into a local git repository, then push that repo to GitHub yourself.

No dependencies beyond Python 3.8+ and git.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
import sys

# ---------------------------------------------------------------------------
# Font: 7 rows tall (Sunday..Saturday). '#' = commit, '.' = empty.
# ---------------------------------------------------------------------------
_FONT_SRC = {
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "C": [".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "G": [".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "I": ["###", ".#.", ".#.", ".#.", ".#.", ".#.", "###"],
    "J": ["..###", "...#.", "...#.", "...#.", "#..#.", "#..#.", ".##.."],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    "N": ["#...#", "#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "Q": [".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "V": ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#."],
    "X": ["#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"],
    "Y": ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."],
    "Z": ["#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"],
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["####.", "....#", "....#", ".###.", "....#", "....#", "####."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": [".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."],
    " ": ["...", "...", "...", "...", "...", "...", "..."],
    "!": ["#", "#", "#", "#", "#", ".", "#"],
    ".": [".", ".", ".", ".", ".", ".", "#"],
    ",": ["..", "..", "..", "..", "..", ".#", "#."],
    ":": [".", "#", ".", ".", ".", "#", "."],
    "'": ["#", "#", ".", ".", ".", ".", "."],
    "-": ["...", "...", "...", "###", "...", "...", "..."],
    "_": [".....", ".....", ".....", ".....", ".....", ".....", "#####"],
    "+": [".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."],
    "=": ["....", "....", "####", "....", "####", "....", "...."],
    "/": ["....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."],
    "(": [".#", "#.", "#.", "#.", "#.", "#.", ".#"],
    ")": ["#.", ".#", ".#", ".#", ".#", ".#", "#."],
    "?": [".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."],
    "#": [".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".#.#."],
    "<": ["...#", "..#.", ".#..", "#...", ".#..", "..#.", "...#"],
    ">": ["#...", ".#..", "..#.", "...#", "..#.", ".#..", "#..."],
    "♥": [".##.##.", "#######", "#######", ".#####.", "..###..", "...#...", "......."],
}
FONT = {ch: [[c == "#" for c in row] for row in rows] for ch, rows in _FONT_SRC.items()}
for _ch, _g in FONT.items():
    assert len(_g) == 7 and len({len(r) for r in _g}) == 1, f"bad glyph {_ch!r}"


def render(text: str, spacing: int = 1) -> list[list[bool]]:
    """Return a 7 x W grid of booleans for the given text."""
    text = text.upper().replace("<3", "♥")
    missing = sorted({c for c in text if c not in FONT})
    if missing:
        raise SystemExit(
            f"Unsupported character(s): {' '.join(repr(c) for c in missing)}\n"
            f"Supported: {''.join(sorted(FONT))}"
        )
    rows: list[list[bool]] = [[] for _ in range(7)]
    for i, ch in enumerate(text):
        if i:
            for r in rows:
                r.extend([False] * spacing)
        for r, glyph_row in zip(rows, FONT[ch]):
            r.extend(glyph_row)
    return rows


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------
def first_sunday_on_or_after(d: dt.date) -> dt.date:
    # weekday(): Mon=0 .. Sun=6
    return d + dt.timedelta(days=(6 - d.weekday()) % 7)


def pixel_dates(grid: list[list[bool]], start: dt.date) -> list[dt.date]:
    """Map lit pixels to dates. start must be a Sunday (top-left cell)."""
    dates = []
    for col in range(len(grid[0]) if grid else 0):
        for row in range(7):
            if grid[row][col]:
                dates.append(start + dt.timedelta(weeks=col, days=row))
    return sorted(dates)


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------
DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


def preview(grid: list[list[bool]], start: dt.date, commits: int) -> None:
    width = len(grid[0])
    end = start + dt.timedelta(weeks=width - 1, days=6)
    lit = sum(sum(r) for r in grid)
    print(f"Text spans {width} weeks: {start} (Sun) -> {end} (Sat)")
    print(f"{lit} lit days x {commits} commits = {lit * commits} commits\n")
    print("The text:\n")
    for row in grid:
        print("  " + "".join("██" if px else "  " for px in row).rstrip())
    print("\nHow it lands on your GitHub graph (one block per year):\n")
    lit_days = set(pixel_dates(grid, start))
    # One block per calendar year, laid out like GitHub's year view.
    for year in range(start.year, end.year + 1):
        jan1, dec31 = dt.date(year, 1, 1), dt.date(year, 12, 31)
        first_col = jan1 - dt.timedelta(days=(jan1.weekday() + 1) % 7)  # Sunday on/before Jan 1
        ncols = (dec31 - first_col).days // 7 + 1
        label = [" "] * (2 * ncols + 3)
        free_from = 0
        for c in range(ncols):
            d = first_col + dt.timedelta(weeks=c)
            m = d + dt.timedelta(days=6)  # the week's Saturday decides the month label
            if m.year == year and (c == 0 or (m - dt.timedelta(weeks=1)).month != m.month) and c >= free_from:
                label[2 * c:2 * c + 3] = m.strftime("%b")
                free_from = c + 2
        print(f"     {year}")
        print("     " + "".join(label).rstrip())
        for row in range(7):
            cells = []
            for c in range(ncols):
                d = first_col + dt.timedelta(weeks=c, days=row)
                cells.append("  " if d.year != year else ("██" if d in lit_days else "░░"))
            print(f"{DAY_LABELS[row]}  {''.join(cells)}")
        print()

    today = dt.date.today()
    if end > today:
        print(f"Note: the drawing runs past today ({today}). Future days only appear on")
        print("GitHub once those dates arrive.\n")
    years = {}
    for d in pixel_dates(grid, start):
        years[d.year] = years.get(d.year, 0) + 1
    print("Lit days per year: " + ", ".join(f"{y}: {n}" for y, n in sorted(years.items())))


# ---------------------------------------------------------------------------
# Writing commits (git fast-import: thousands of commits in about a second)
# ---------------------------------------------------------------------------
def git(repo: str, *args: str, check: bool = True) -> str:
    res = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if check and res.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed:\n{res.stderr.strip()}")
    return res.stdout.strip()


def write_commits(repo: str, branch: str, dates: list[dt.date], commits: int,
                  name: str, email: str, hour: int) -> int:
    if not os.path.isdir(os.path.join(repo, ".git")):
        os.makedirs(repo, exist_ok=True)
        git(repo, "init", "-q", "-b", branch)
    parent = git(repo, "rev-parse", "--verify", "-q", f"refs/heads/{branch}^{{commit}}", check=False)

    stream = []
    n = 0
    for d in dates:
        for i in range(commits):
            n += 1
            # Noon UTC by default lands on the same calendar day in nearly every timezone.
            ts = int(dt.datetime(d.year, d.month, d.day, hour, 0, i % 60,
                                 tzinfo=dt.timezone.utc).timestamp())
            msg = f"canvas {d.isoformat()} #{i + 1}\n".encode()
            body = f"{d.isoformat()} {i + 1}\n".encode()
            head = (
                f"commit refs/heads/{branch}\n"
                f"author {name} <{email}> {ts} +0000\n"
                f"committer {name} <{email}> {ts} +0000\n"
                f"data {len(msg)}\n"
            ).encode()
            stream.append(head + msg)
            if n == 1 and parent:
                stream.append(f"from {parent}\n".encode())
            stream.append(f"M 644 inline canvas.txt\ndata {len(body)}\n".encode() + body + b"\n")

    res = subprocess.run(["git", "-C", repo, "fast-import", "--quiet"],
                         input=b"".join(stream), capture_output=True)
    if res.returncode != 0:
        raise SystemExit("git fast-import failed:\n" + res.stderr.decode(errors="replace"))
    # Refresh the working tree if the branch is checked out.
    if git(repo, "symbolic-ref", "-q", "--short", "HEAD", check=False) == branch:
        git(repo, "reset", "-q", "--hard", branch)
    return n


def push_in_batches(repo: str, remote: str, branch: str, batch: int, force: bool) -> None:
    """Push the branch a few hundred commits at a time.

    GitHub only records contributions for roughly the newest 1,000 commits of a
    single push, so a big drawing has to go up in steps.
    """
    out = git(repo, "ls-remote", remote, f"refs/heads/{branch}")
    remote_sha = out.split()[0] if out else ""
    known = remote_sha and subprocess.run(
        ["git", "-C", repo, "merge-base", "--is-ancestor", remote_sha, branch],
        capture_output=True).returncode == 0
    if remote_sha and not known and not force:
        raise SystemExit(f"{remote} already has a different {branch} branch (maybe an old drawing). "
                         "Rerun with --force-push to replace it.")
    rng = f"{remote_sha}..{branch}" if known else branch
    commits = git(repo, "rev-list", "--reverse", "--first-parent", rng).split()
    if not commits:
        print("Nothing new to push.")
        return
    stops = commits[batch - 1::batch]
    if not stops or stops[-1] != commits[-1]:
        stops.append(commits[-1])
    for i, sha in enumerate(stops, 1):
        args = ["push", "-q"]
        if force and i == 1:
            args.append("--force")
        print(f"Pushing batch {i}/{len(stops)}...")
        git(repo, *args, remote, f"{sha}:refs/heads/{branch}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Write text into your GitHub contribution graph with backdated commits.",
        epilog="Without --repo nothing is written: you just get a preview.",
    )
    p.add_argument("--push-only", action="store_true",
                   help="don't draw anything; just push --repo to --push REMOTE in batches")
    p.add_argument("text", nargs="?", help='text to draw, e.g. "HELLO" (A-Z, 0-9, some punctuation, <3)')
    when = p.add_mutually_exclusive_group()
    when.add_argument("--year", type=int,
                      help="start at the first Sunday of this year (default: last year)")
    when.add_argument("--start", type=dt.date.fromisoformat,
                      help="start date YYYY-MM-DD (moved forward to the next Sunday)")
    p.add_argument("--offset", type=int, default=1,
                   help="blank weeks before the text (default 1)")
    p.add_argument("--spacing", type=int, default=1, help="blank columns between letters (default 1)")
    p.add_argument("--commits", type=int, default=12,
                   help="commits per lit day; higher = darker green (default 12)")
    p.add_argument("--repo", help="path to a git repo to write commits into (created if missing)")
    p.add_argument("--branch", default="main", help="branch to write to (default main)")
    p.add_argument("--name", help="author name (default: git config user.name)")
    p.add_argument("--email", help="author email; must be a verified email on your GitHub account "
                                    "(default: git config user.email)")
    p.add_argument("--hour", type=int, default=12, help="UTC hour for commit times (default 12)")
    p.add_argument("--push", metavar="REMOTE",
                   help="after writing, push to this remote (e.g. origin) in batches; GitHub only "
                        "counts about 1,000 commits per push, so one big push loses most of the drawing")
    p.add_argument("--batch", type=int, default=900, help="commits per push with --push (default 900)")
    p.add_argument("--force-push", action="store_true",
                   help="with --push, allow replacing what is on the remote branch (e.g. an old drawing)")
    p.add_argument("-y", "--yes", action="store_true", help="skip the confirmation prompt")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    a = parse_args(argv)
    if a.push_only:
        if not (a.repo and a.push):
            raise SystemExit("--push-only needs --repo PATH and --push REMOTE.")
        push_in_batches(a.repo, a.push, a.branch, a.batch, a.force_push)
        print("Pushed.")
        return 0
    if not a.text:
        raise SystemExit("Give the text to draw, e.g. commit_canvas.py \"HELLO\"")
    if a.start:
        base = a.start
    else:
        year = a.year if a.year else dt.date.today().year - 1
        base = dt.date(year, 1, 1)
    start = first_sunday_on_or_after(base) + dt.timedelta(weeks=max(0, a.offset))

    grid = render(a.text, a.spacing)
    preview(grid, start, a.commits)

    if not a.repo:
        print("\nPreview only. Add --repo PATH to write the commits.")
        return 0

    def cfg(key: str) -> str:
        return subprocess.run(["git", "config", "--get", key], capture_output=True, text=True).stdout.strip()

    name = a.name or cfg("user.name")
    email = a.email or cfg("user.email")
    if not name or not email:
        raise SystemExit("Need an author name and email: pass --name/--email or set git config user.name/user.email.")

    dates = pixel_dates(grid, start)
    total = len(dates) * a.commits
    print(f"\nAbout to write {total} commits to {os.path.abspath(a.repo)} ({a.branch}) as {name} <{email}>.")
    if not a.yes:
        if input("Continue? [y/N] ").strip().lower() not in ("y", "yes"):
            print("Aborted.")
            return 1
    n = write_commits(a.repo, a.branch, dates, a.commits, name, email, a.hour)
    print(f"Wrote {n} commits.")
    if a.push:
        push_in_batches(a.repo, a.push, a.branch, a.batch, a.force_push)
        print("Pushed. Your graph should update within a few minutes.")
    else:
        print(f"Next: push in batches so GitHub counts every commit (it only counts ~1,000 per push):")
        print(f"  python3 {os.path.basename(sys.argv[0])} --push-only --repo {a.repo} --push origin")
        print("  (or rerun with --push origin next time)")
    print("To undo it later, delete that GitHub repo and the commits disappear from your graph.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
