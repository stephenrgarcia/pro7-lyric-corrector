# Architecture

How `pro7_lyric_corrector` parses and edits ProPresenter 7 `.pro` files safely,
with zero third-party dependencies.

## The `.pro` file format (confirmed against the real library)

- `.pro` files are **binary Google Protocol Buffers** (not the XML of PP5/6).
  (`file` misidentifies them as thermal-camera data — ignore that; it is a
  magic-byte coincidence.)
- The **presentation title** is top-level protobuf **field 3** (a UTF-8 string).
- **Lyric text** is stored as an **RTF document** embedded in a bytes field at a
  single consistent nested path, which the code finds structurally (it does not
  hardcode the path): every RTF payload in all 384 files lives at
  `.../13/10/23/2/1/1/1/13/5` and begins with `{\rtf1`.
- Each text element **also** has a sibling **plain-text** field
  (`.../13/10/23/2/1/1/1/2`). On this library that field is a stale template
  string ("There's nothing worth more …") that ProPresenter does **not** render.
  **We edit the RTF only**; the plain field is ignored. (This is why the
  "TEST TEST" junk that appears in `strings` output is never touched — it lives
  in that ignored plain field, whose RTF box is empty.)
- In-slide line breaks are encoded two ways: a trailing **`\` + newline**
  (`0x5C 0x0A`), or a Unicode **line separator** (`\uc0\u8232`, U+2028). Both are handled.
- Smart punctuation is **cp1252-escaped**, not raw Unicode: `’`=`\'92`,
  `“`=`\'93`, `”`=`\'94`, en/em dash = `\'96`/`\'97`.

## Why a stdlib wire codec instead of the GreyShirtGuy `.proto`

The spec called for GreyShirtGuy's `ProPresenter7-Proto` + `protoc`-generated
classes. On the target machine that path is **not installable**: the system
Python (3.9.6) has no `protobuf`/`grpc_tools`, there is no `protoc`, and there
is no network at runtime. Depending on `pip`-installed packages would also make
an always-on LaunchAgent fragile (OS updates wipe them).

Instead, `pro7corrector/wire.py` is a **dependency-free protobuf wire-format
codec**. The deciding evidence: parsing every `.pro` in the library and
serializing it back reproduces the **original bytes exactly** for all 384 files.
This achieves the spec's actual safety goals (preserve every non-lyric field,
round-trip verify, edit only lyric text) more robustly than an unofficial schema
that could drift. See the "deviation" note in `docs/HANDOFF.md`.

## Module map

| Module | Responsibility |
|---|---|
| `wire.py` | Generic protobuf wire parse/serialize into a mutable node tree; locate RTF leaves and string leaves. Byte-exact round trip. |
| `rtf.py` | RTF text-layer codec: extract logical text, **run-preserving** splice. |
| `rules.py` | Deterministic correction rules + ambiguity flagging. |
| `song_gate.py` | Per-file song detection (name markers + "has lyric slides"). |
| `presentation.py` | Orchestration: correct lyrics + title, then **verify** preservation. |
| `backup.py` | Timestamped backups, manifest, atomic writes, restore. |
| `monitor.py` | The engine: scan/gate/correct/backup/write/log; fail-closed; cache; deferral. |
| `config.py` | Root/library discovery, ProPresenter-running detection, paths. |
| `agent.py` | LaunchAgent plist build + `launchctl` start/stop/status. |
| `aibatch.py` | Optional AI pass: emit tasks, validate + apply proposals. |

## The wire codec (`wire.py`)

Length-delimited fields are heuristically classified as **sub-message** vs.
**opaque leaf** by attempting a full protobuf parse of the payload
(`_looks_like_message`). The node tree is mutable lists so callers edit a leaf's
bytes in place; `serialize()` recomputes **all** length prefixes, so an edited
leaf safely propagates new lengths up the parent chain.

**Important subtlety — string/message ambiguity.** A bytes/string field whose
content *coincidentally* forms valid protobuf wire format gets parsed as a
sub-message. This is harmless for round-trip fidelity (serializing reproduces the
same bytes either way) but matters for anything that searches by node *kind*.
RTF payloads are immune (they start with `{` = wire type 3, never a message). The
**title** is not: e.g. `"After You"` is 9 bytes that parse as a fixed64 field, so
after writing it the re-parsed title is a message node. All title handling is
therefore **classification-independent** — `presentation._find_title_node`
matches field 3 regardless of kind, and `_title_bytes` reserializes a
mis-classified message back to its string bytes. (Regression-tested.)

## The RTF codec (`rtf.py`) — run-preserving splice

We never do a full RTF round trip. `extract()` splits the renderable body into an
alternating sequence of **text runs** and **control segments** (formatting like
`\pard`, `\cf2`, `\b`, `\fs152`):

- `.text` — logical text for display/diffing.
- `.coded` — same text with a private-use `SENTINEL` (`U+E000`) marking each
  control-segment boundary, so the corrector preserves run boundaries.
- `.ctrl_segments` — the raw bytes of each control segment, in order.
- `.clean` / `.skip_reason` — a payload is skipped **only** when its text
  contains a non-cp1252 character (a "special glyph", e.g. a Cyrillic letter
  rendered via a font switch). Those are left exactly as-is.

The corrector runs on `.coded`; `splice()` splits the corrected coded text back
on the sentinel and rebuilds the body by interleaving **re-encoded text runs**
with the **original control-segment bytes**. So:

- Formatting (paragraph resets, color/size/bold runs) is preserved **byte-for-
  byte**.
- For an unchanged payload this reproduces the original bytes exactly — verified
  by the no-op identity test (the few that differ only normalize a `\u8232` soft
  break to a hard break, which is rendering-equivalent and only happens when the
  text actually changes).
- `encode_run()` emits ProPresenter's conventions: line break → `\` + newline,
  `{`/`}`/`\` escaped, byte ≥ 0x80 → `\'hh` (lowercase, cp1252).

History: an earlier version treated any interleaved formatting as "skip"
(74 → 20 payloads skipped). The run-preserving rewrite reclaimed paragraph resets
and other formatting; now only **7** genuine special-glyph payloads are skipped.

## Correction + verification (`presentation.py`)

`process_bytes(data, cfg, desired_title)`:

1. Plan a **title fix** (field 3 → filename) if it differs.
2. For each non-empty, clean RTF leaf: correct `.coded`, collect flags, skip if
   the length delta is suspicious or the splice no longer fits the segment
   structure.
3. Apply all splices (+ title) to a fresh tree, serialize.
4. **Verify** and only then return `new_bytes`:
   - Blank every RTF leaf (and the title, if changed) to empty in **both** the
     original and corrected trees, serialize, and require byte-equality — this
     proves the entire non-lyric structure is unchanged.
   - Require each changed leaf to re-extract to exactly the corrected text, and
     each untouched leaf to be byte-identical.
   - Any failure ⇒ discard, keep original, report error (the monitor logs it and
     leaves the file untouched).

The monitor (`monitor.py`) wraps this with the song gate, hash/sig cache,
backups, atomic writes, a post-write re-parse, fail-closed-when-open deferral,
and the ambiguous-flag queue feeding the optional AI pass.
