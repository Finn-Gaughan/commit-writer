# commit-writer

Write text into your GitHub contribution graph. Each letter is drawn with a 7-pixel-tall
font (one row per weekday, one column per week), and every lit pixel becomes a day with a
batch of backdated commits. Long text simply keeps going into the next year, so you can
write across as many years as you like.

Plain Python 3.8+ and git. No dependencies.

## Preview first (writes nothing)

```bash
python3 commit_canvas.py "HELLO"                 # starts at the first Sunday of last year
python3 commit_canvas.py "HELLO WORLD" --year 2021
python3 commit_canvas.py "HI <3" --start 2024-06-01
```

The preview prints one block per calendar year, laid out like GitHub's year view:

```
     2024
     Jan Feb Mar  Apr May Jun  Jul Aug  Sep Oct Nov  Dec
Sun   ·█···█·█████·█·····█······███······█···█··███··████·
Mon  ··█···█·█·····█·····█·····█···█·····█···█·█···█·█···█
Tue  ··█···█·█·····█·····█·····█···█·····█···█·█···█·█···█
Wed  ··█████·████··█·····█·····█···█·····█·█·█·█···█·████
...
```

## Write it for real

```bash
# 1. Create an empty repo on GitHub, e.g. "my-graph-art" (public, or private with
#    "Private contributions" turned on in your profile settings).
# 2. Write the commits into a local repo:
python3 commit_canvas.py "HELLO" --year 2021 --repo ./my-graph-art \
    --email you@example.com
# 3. Push it:
cd my-graph-art
git remote add origin git@github.com:<you>/my-graph-art.git
git push -u origin main
```

The graph updates within a few minutes. Run the script several times with different
`--year`/`--start` values against the same `--repo` to add more text.

## Options

| Option | Meaning |
| --- | --- |
| `--year YYYY` | Start at the first Sunday of that year (default: last year) |
| `--start YYYY-MM-DD` | Start at a specific date (moved forward to the next Sunday) |
| `--offset N` | Blank weeks before the text (default 1) |
| `--spacing N` | Blank columns between letters (default 1) |
| `--commits N` | Commits per lit day. Higher means darker green (default 12) |
| `--repo PATH` | Git repo to write into (created if missing). Without it, preview only |
| `--branch NAME` | Branch to write to (default `main`) |
| `--name`, `--email` | Commit author. Defaults to your `git config` values |
| `--hour H` | UTC hour for the commit times (default 12) |
| `-y` | Skip the confirmation prompt |

Supported characters: `A-Z 0-9 space ! . , : ' - _ + = / ( ) ? # < >` and `<3` (or `♥`) for a heart.

## Things to know

- **The email must be one of your verified GitHub emails**, or the commits will not count.
- **Pick `--commits` high enough** to outshine your real activity. GitHub shades days relative
  to your busiest days, so if you commit a lot, raise it (e.g. `--commits 30`).
- **Commits land on the default branch** of the repo you push to, which is what GitHub counts.
- **Year boundaries:** GitHub shows each year separately, so a letter that straddles 1 January
  is split across two year views. The preview shows exactly where the split falls; nudge
  `--start` or `--offset` if a letter gets cut.
- **Future dates** are allowed but only show up once those days arrive.
- **To undo**, delete the GitHub repo you pushed to; its commits vanish from your graph.

Commits are created with `git fast-import`, so even tens of thousands take about a second.
