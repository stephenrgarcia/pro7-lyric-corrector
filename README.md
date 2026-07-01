# ProPresenter Lyric Corrector

**A free tool that automatically cleans up the lyrics in your ProPresenter 7
song library — and keeps them clean — so your screens look consistent every
week.** No more random ALL-CAPS lines, "your" where it should be "Your" (and
vice-versa), `colour`/`Saviour`, stray Capitals In The Middle of lines, or
twelve different ways of writing the same chorus.

Run it once, review changes before writing, or let it run quietly in the
background on your Mac or Windows PC. In always-on mode, when you add or edit a
song and close ProPresenter, it tidies the lyrics within a few seconds —
backing up every file first.

> 💝 This is a gift to the worship-tech community. It's free, open, and there's
> nothing to buy. Use it, share it, change it.

---

## Is this for me?

You'll need:

- **A Mac or Windows PC.**
- **ProPresenter 7**, with your songs in a library called **Songs** (the default).
- **Python 3.** macOS can use the system `python3`; Windows users can install
  Python 3 from python.org or use the Python launcher (`py`).
- A few minutes for setup. The easiest path is to let your AI coding assistant
  run the Terminal commands for you; the copy/paste Terminal steps are still
  included below if you prefer to do it yourself.

That's it. No accounts, no internet connection required, no paid software for the
core tool. (There's an **optional** AI step later that needs a local coding
assistant that can read this folder and run commands — but the main tool works
great without it.)

---

## How it works (the two layers)

**1. The deterministic corrector (free, local, no AI).**
Run it as a one-time cleanup, review each proposed song before writing, or
install a tiny background helper that watches your **Songs** library. Whenever a
song is new or edited, it fixes everything that can be fixed *reliably by
rules* — spelling, capitalization of God's names, stray capitals, smart quotes,
and so on. It only writes when ProPresenter is **closed**, so it never fights
with you while you're editing.

**2. The optional nightly AI pass.**
Some choices need judgment, not rules — like whether "your" refers to God ("I
worship You") or to a person ("give Him your praise"). The corrector **flags**
those instead of guessing. If you set up the optional AI step with a local AI
coding assistant, it reviews the flagged songs and makes those
context-dependent calls.
**You can skip this entirely** and still get 90% of the benefit.

Every change — by either layer — is written to a plain-text log
(`EDIT-LOG.md`) and every file is backed up first.

---

## What it changes by default

These run automatically and are considered "safe" (rule-based):

| Category | Example |
|---|---|
| ALL-CAPS lines → sentence case | `HOLY IS THE LORD` → `Holy is the Lord` |
| First word of each line capitalized | `and we worship` → `And we worship` |
| Stray capitals inside a word | `evEry` → `every` |
| Stray capitals on small words mid-line | `salvation In The night` → `salvation in the night` |
| American spelling | `Saviour`, `colour`, `honour` → `Savior`, `color`, `honor` |
| Common typos | `alright` → `all right`, `recieve` → `receive` |
| Straight → smart quotes & apostrophes | `'Cause`, `"Holy"` → `’Cause`, `“Holy”` |
| God's names & titles always capitalized | `jesus`, `lord`, `king of kings`, `holy spirit` → `Jesus`, `Lord`, `King of Kings`, `Holy Spirit` |
| Attributes always **lowercase** | `Grace`, `Glory`, `Mercy`, `the Cross` → `grace`, `glory`, `mercy`, `the cross` |
| Tidy spacing | double spaces, trailing spaces, extra blank lines removed |
| Song title cleaned | the name shown in ProPresenter's library is set to the file's name (so no more `Untitled` or typo'd titles) |

**Left for the optional AI pass (flagged, never guessed):**

- Pronouns that may be God or a person — **You/Your**, **He/Him/His**,
  **Me/My** (capital only when it refers to / is spoken by God or Jesus).
- "the **One** Who…" when it means God.
- Words that are sometimes a title for Jesus and sometimes a normal word —
  `king, spirit, word, name, father, son, rock, shepherd, light, life, way,
  truth`, etc.
- A leading single quote that might be an opening quote instead of an apostrophe.

> **Heads-up — these are opinionated defaults.** They reflect a common, clean
> worship-display style, but they may not match yours exactly (for instance,
> capitalizing the first word of *every* line). See **[Make it your
> own](#make-it-your-own)** to change any of them before you run it.

---

## Your data is safe

- **Every changed file is backed up first**, timestamped, to
  `~/Documents/ProPresenter Backups/lyric-corrector/` (outside your library).
- Files are edited **in place** — no new files appear in your Songs folder.
- After each edit the file is **re-checked**; if anything looks off, the change
  is thrown away and the original kept.
- It is **fail-safe while ProPresenter is open** — it waits until you close it.
- It **only ever touches the Songs library** — never sermons, announcements,
  playlists, media, themes, or any other library.
- Songs with unusual characters it can't safely re-encode are **skipped**, not
  mangled.

You can undo everything (see **[Undo / restore](#undo--restore)**).

---

# Setup

Takes about 10–15 minutes. The easiest path is to open this folder in your AI
coding assistant and let it walk you through the setup. The no-AI copy/paste
method is right below it.

Before you start, choose two things:

- **How it should run:** one-time cleanup only, or always-on background cleanup.
- **How cautious the first pass should be:** preview a draft first, review every
  changed song one-by-one, or update the live Songs library after a normal
  preview.

The safest first run is: **full draft preview → one-by-one review → optional
always-on helper**.

### Setup with an AI IDE (easiest)

Use any local AI coding assistant that can read this folder and run Terminal
commands on the computer that has your ProPresenter library. Good options include
Claude Code, Codex, Cursor, VS Code with GitHub Copilot, Windsurf, Cline, Roo
Code, Continue, Gemini CLI, Qwen Code, Kiro, Junie, Devin, and
Hermes-compatible workflows. Availability and pricing vary by tool.

1. Download/unzip (or clone) this folder somewhere you'll remember, e.g. your
   Documents folder.
2. Open this folder in your AI IDE or coding assistant.
3. Quit ProPresenter before any live update.
4. Paste this prompt:

```
Please set up this ProPresenter lyric corrector on this computer.

Read AGENTS.md and README.md first. Do not add dependencies. Only touch the
ProPresenter Songs library.

First ask me to choose:
- one-time cleanup only, or always-on background cleanup
- full draft preview first, one-by-one review, or update live after a normal
  preview

Then follow my choice using these commands:
1. Confirm this folder contains pro7_lyric_corrector.py.
2. Use `python3` on macOS, or `py` on Windows. If `py` is unavailable on
   Windows, try `python`.
3. Run: python3 pro7_lyric_corrector.py discover
4. For a normal no-write preview, run:
   python3 pro7_lyric_corrector.py calibrate
5. For a full no-write draft of every proposed change, run:
   python3 pro7_lyric_corrector.py calibrate --all --per-file 0
6. For one-by-one review before writing anything, run:
   python3 pro7_lyric_corrector.py review
7. For direct one-time live cleanup after I confirm, run:
   python3 pro7_lyric_corrector.py apply-once
8. Only if I choose always-on cleanup, install and start the helper:
   python3 pro7_lyric_corrector.py install-agent
   python3 pro7_lyric_corrector.py start
   python3 pro7_lyric_corrector.py status

If ProPresenter is open, stop and tell me to quit it before writing. If I choose
always-on cleanup on macOS, remind me to grant Full Disk Access to
/usr/bin/python3. On Windows, remind me that install-agent creates a Task
Scheduler task.
```

5. On macOS, when the assistant reaches the Full Disk Access step, do that part yourself:
   open **System Settings → Privacy & Security → Full Disk Access**, click **+**,
   press **⌘⇧G**, type `/usr/bin/python3`, press Return, and **Add** it. Make
   sure its switch is **on**. This is only needed for the always-on background
   helper. Windows does not use Full Disk Access; the helper is installed with
   Task Scheduler.

If you choose one-time cleanup, you're done after `apply-once` or `review`
finishes. If you choose always-on cleanup, you're set once `status` says the
helper is running. Everyday rhythm: edit songs in ProPresenter → **close
ProPresenter** → within a few seconds your new/edited songs are corrected and
backed up.

### Setup without AI (copy/paste)

Prefer to do it yourself? Copy/paste each command below.

### Step 0 — Make a safety copy (optional but smart)

The tool backs up every file it changes, but for total peace of mind you can
make your own copy of your library first: go to your ProPresenter Libraries
folder, right-click the **Songs** folder, and compress/copy it somewhere safe.
The default location is usually `~/Documents/ProPresenter/Libraries/` on macOS
or `%USERPROFILE%\Documents\ProPresenter\Libraries\` on Windows.

Also: **quit ProPresenter** before the one-time cleanup.

### Step 1 — Put the tool on your computer

Download/unzip (or clone) this folder somewhere you'll remember, e.g. your
Documents folder. The whole thing is one folder containing
`pro7_lyric_corrector.py` and a `pro7corrector/` folder.

### Step 2 — Open Terminal or PowerShell *in that folder*

On macOS, open the **Terminal** app. On Windows, open **PowerShell**. Type
`cd ` (with a space), then drag the tool's folder onto the Terminal/PowerShell
window and press **Return/Enter**. Your prompt should now show the folder name.

The commands below use `python3`. On Windows, replace `python3` with `py` (or
`python` if that is how Python is installed).

Check it works (this only reads, changes nothing):

```bash
python3 pro7_lyric_corrector.py discover
```

> On macOS, if the system asks to **install developer tools**, click **Install**
> and wait, then run the command again. On Windows, if `py`/`python` is not
> found, install Python 3 and reopen PowerShell.

You should see it find your ProPresenter and your Songs library.

### Step 3 — Preview the changes (no writes)

Start with a normal preview summary and sample diffs:

```bash
python3 pro7_lyric_corrector.py calibrate
```

To see a full draft of every proposed change before anything is written:

```bash
python3 pro7_lyric_corrector.py calibrate --all --per-file 0
```

Read through the preview. If something looks wrong for your style, see
**[Make it your own](#make-it-your-own)** first.

### Step 4 — Choose how to update the live library

**Option A — Review each changed song before writing anything.**
This shows every proposed diff, lets you approve or skip each song, then asks
one final time before it writes approved files to the live Songs library:

```bash
python3 pro7_lyric_corrector.py review
```

This is the safest path for an existing library.

**Option B — Run a one-time cleanup now.**
With ProPresenter **closed**, correct the whole library once (every changed file
is backed up):


```bash
python3 pro7_lyric_corrector.py apply-once
```

It prints each song it changed. Open ProPresenter and spot-check a few. Don't
like a result? See **[Undo / restore](#undo--restore)**.

**Option C — Stop after preview.**
If you only wanted to see what the tool would do, stop after `calibrate`. No
files were changed.

### Step 5 — Optional: turn on the always-on auto-corrector

This installs a small background helper that keeps new/edited songs clean going
forward. Skip this step if you only want one-time cleanup.

```bash
python3 pro7_lyric_corrector.py install-agent
python3 pro7_lyric_corrector.py start
python3 pro7_lyric_corrector.py status
```

`status` should say it's **running**.

### Step 6 — Platform permission / background helper notes

On macOS, your library lives in `~/Documents`, which macOS protects. The
background helper can't touch it until you allow it **once**:

1. Open **System Settings → Privacy & Security → Full Disk Access**.
2. Click **+**, press **⌘⇧G**, type `/usr/bin/python3`, press Return, and **Add**
   it.
3. Make sure its switch is **on**.

On Windows, `install-agent` creates a Task Scheduler task named
`Pro7LyricCorrector`; no Full Disk Access step is needed.

That's it — the helper now corrects songs automatically. **Everyday rhythm:**
edit songs in ProPresenter → **close ProPresenter** → within a few seconds your
new/edited songs are corrected (and backed up). Reopen any time.

> Prefer not to install the background helper? You can instead run the watcher
> by hand in a Terminal/PowerShell window whenever you want it active:
> `python3 pro7_lyric_corrector.py watch` (leave the window open; press
> **Ctrl-C** to stop).

---

## Step 7 (optional) — The nightly AI pass with any local AI assistant

This adds the *judgment* calls the basic tool leaves alone (e.g. lowercasing
"your" when it's the listener's, capitalizing "You" when it's God). **Totally
optional.** It needs an AI coding assistant that can read local files and run
Terminal commands, and it must run **on the computer that has your library** (it
needs local file access). Examples include Claude Code, Codex, Gemini CLI,
Qwen Code, Cursor, Copilot coding agent, Cline, Roo, Continue, Kiro, Junie,
Devin, Windsurf, and Hermes-compatible workflows. Availability and pricing vary
by tool.

The instructions the AI follows live in **`docs/ROUTINE.md`** in this folder —
it's the single source of truth, so you never have to update the assistant
itself. This repo also includes common starter files (`AGENTS.md`, `CLAUDE.md`,
`GEMINI.md`, `QWEN.md`, `HERMES.md`, Copilot/Cursor/Cline/Roo/Continue rules,
and more) so most AI IDEs can find the same project guidance automatically.
See `docs/AI_IDE_SUPPORT.md` for the full list.

**A. Install your assistant** and sign in (follow their docs):
- Choose any assistant that can access this folder and run Terminal commands.
- If it supports repository instruction files, it should pick up the matching
  starter file automatically.

**B. Open this tool's folder** in the assistant (point it at the folder from
Step 1).

**C. Run the pass on demand** — paste this prompt to the assistant:

```
You are my worship-lyric assistant. Read the file docs/ROUTINE.md in this
project and follow it exactly, top to bottom. Re-read it every time (it is the
source of truth and may have changed). Only ever touch songs in the
ProPresenter "Songs" library. When you're done, stop.
```

It will pull the list of flagged songs, make the context-dependent fixes, apply
them through the same safe pipeline (backup → verify → log), and report what it
changed. (Quit ProPresenter first, or it will safely defer.)

**D. (Advanced) Schedule it nightly.** Some assistants can run on a schedule, or
you can use your operating system's scheduler to launch the assistant with the
prompt above (e.g. nightly at 3 AM). The pass is cheap to run repeatedly because it
**only looks at songs whose lyrics changed since the last run** — usually just
the few you edited that week. If nothing changed, it does nothing.

> New to scheduling? Skip it. Just paste the prompt from step C whenever you've
> added a batch of songs and want the polish.

---

## Undo / restore

Every changed file has a timestamped backup in your Documents folder under
`ProPresenter Backups/lyric-corrector/`.

- **Restore one song** to its pre-change version:
  ```bash
  python3 pro7_lyric_corrector.py --restore "20260630-125719__Amazing Grace.pro.bak"
  ```
  (Use a filename from the backups folder.)
- **Restore by hand:** copy the `.pro.bak` file over the original `.pro` in
  your `Documents/ProPresenter/Libraries/Songs/` folder (and remove the `.bak`).
- **See exactly what changed and why:** open `EDIT-LOG.md` in this folder — it's
  a running, plain-text history of every edit.

To turn the background helper off:
`python3 pro7_lyric_corrector.py stop`

---

## Make it your own

The defaults are opinionated. To change them, open `pro7corrector/rules.py`:

- Each rule category has an on/off switch in the `Config` near the top:
  `allcaps`, `spelling`, `smart_punct`, `midline` (lowercasing common words),
  `typos`, `divine` (capitalizing God's names), `intercaps` (mid-word capitals),
  `fix_title`. Set any to `False` to disable it.
- The lists that decide casing are right there too and easy to read:
  `ALWAYS_CAP` (always capitalized), `COMMON_WORDS` / `FUNCTION_WORDS` (always
  lowercase mid-line), `AMBIGUOUS_DIVINE` (left for the AI pass), `PHRASE_RULES`
  (multi-word titles like *King of Kings*).
- The most opinionated rule is **capitalizing the first word of every line**. To
  change it, edit `_first_word_cap` in `rules.py`.

After any change, re-run `python3 pro7_lyric_corrector.py calibrate` to preview,
then `apply-once`. There are tests: `python3 tests/run_tests.py`.

---

## Troubleshooting

- **"It's not correcting my songs automatically."** The background helper only
  writes when **ProPresenter is closed**. Close it and wait ~5 seconds. Also
  confirm Step 6 is complete and `status` shows *running*.
- **"`python3` / `py` says command not found."** On macOS, click **Install**
  if prompted for developer tools, then retry. On Windows, install Python 3 and
  reopen PowerShell.
- **"It didn't touch some songs."** It only edits the **Songs** library and
  skips non-song files and songs with characters it can't safely re-encode (it
  logs why).
- **"A capitalization looks wrong."** The context-dependent ones are judgment
  calls handled by the optional AI pass — and even that isn't perfect. Fix it in
  ProPresenter; the tool won't undo your manual choice for those flagged words.

---

## What it will never do

- Touch any library other than **Songs**.
- Change wording, reorder or add/remove lines, or alter meaning — it only
  adjusts capitalization, spelling, punctuation, and spacing.
- Create new files in your library or upload anything anywhere. It's entirely
  local and offline (the optional AI step is the only thing that uses a network,
  and only if you set it up).

---

## A gift, freely given

This was built for one church's volunteer team and is shared freely with the
wider ProPresenter community — **not for sale, not for profit, no strings.** If
it blesses your Sunday, pass it on. Improvements and fixes are welcome.

Pure Python 3 standard library — **zero dependencies**, nothing to install
beyond Python itself.

*Developers:* see `AGENTS.md` and `docs/ARCHITECTURE.md` (how the `.pro` format
is parsed and edited safely). AI IDE starter files are listed in
`docs/AI_IDE_SUPPORT.md`.
