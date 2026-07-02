"""RTF text-layer codec for ProPresenter lyric payloads (run-preserving).

ProPresenter stores slide text as an RTF document embedded in the protobuf. We
do not do a full RTF round-trip (that risks reflowing control words). Instead we
split the renderable body into an alternating sequence of *text runs* and
*control segments* (formatting like `\\pard`, `\\cf2`, `\\b`, `\\fs152`). We
re-encode only the text runs and copy every control segment through byte-for-
byte. The entire formatting prelude (font/color tables, paragraph/run controls
before the first character) is also left untouched.

`extract()` returns:
  * .text   -- logical text for display/correction (cp1252 escapes decoded,
               line breaks as "\n"); control-segment boundaries are NOT shown.
  * .coded  -- same text but with a private-use SENTINEL char marking each
               control-segment boundary, so the corrector preserves run
               boundaries; correct this string and split it back on the
               sentinel.
  * .ctrl_segments -- the raw bytes of each control segment, in order.
  * .body_start / .body_end -- byte span of the renderable region.
  * .clean / .skip_reason -- a payload is skipped only when its text contains a
               character that is not representable in cp1252 (a "special glyph"
               such as a Cyrillic letter rendered via a font switch). Paragraph
               resets and other formatting are kept *as is* and corrected.

`encode_run()` re-encodes a text run to ProPresenter's conventions:
  * line break  -> backslash + newline  (0x5C 0x0A)   [verified against library]
  * '{' '}' '\\' -> escaped
  * non-breaking space (U+00A0) -> \\~                (RTF's own control symbol)
  * byte >= 0x80 -> \\'hh  (lowercase hex, cp1252)     [matches library]

`splice()` rebuilds: rtf[:body_start] + reconstructed body + rtf[body_end:],
where the reconstructed body interleaves re-encoded text runs with the original
control-segment bytes. For an unchanged payload this reproduces the original
bytes exactly (proven by the no-op identity test in tests/run_tests.py),
and the corrector's no-op write-guard means unchanged content is never written.
"""

from __future__ import annotations

SENTINEL = ""   # private-use marker for a control-segment boundary

_DEST_WORDS = {
    "fonttbl", "colortbl", "expandedcolortbl", "stylesheet", "listtable",
    "listoverridetable", "info", "pict", "object", "themedata",
    "colorschememapping", "datastore", "latentstyles", "rsidtbl", "generator",
    "xmlnstbl", "filetbl", "revtbl", "protusertbl",
}

# Control symbols that emit a literal character.
_SYMBOL_CHARS = {
    0x5C: "\\",       # \\  -> backslash
    0x7B: "{",        # \{  -> {
    0x7D: "}",        # \}  -> }
    0x7E: " ",   # \~ -> non-breaking space (U+00A0, round-trips via encode_run)
    0x5F: "-",        # \_ -> (non-breaking) hyphen, normalized to a regular hyphen
}


class RtfText:
    __slots__ = ("text", "coded", "body_start", "body_end", "ctrl_segments",
                 "clean", "skip_reason")

    def __init__(self, text, coded, body_start, body_end, ctrl_segments,
                 clean, skip_reason):
        self.text = text
        self.coded = coded
        self.body_start = body_start
        self.body_end = body_end
        self.ctrl_segments = ctrl_segments
        self.clean = clean
        self.skip_reason = skip_reason

    def __repr__(self):
        return "RtfText(text=%r, segs=%d, clean=%s, skip=%r)" % (
            self.text, len(self.ctrl_segments), self.clean, self.skip_reason)


def _is_alpha(b):
    return 0x41 <= b <= 0x5A or 0x61 <= b <= 0x7A


def _cp1252_ok(s):
    for ch in s:
        if ch == "\n":
            continue
        try:
            ch.encode("cp1252")
        except UnicodeEncodeError:
            return False
    return True


def extract(rtf: bytes) -> RtfText:
    i = 0
    n = len(rtf)
    ignore_stack = [False]
    text_runs = [[]]          # list of char-lists; one per text run
    ctrl_segments = []        # raw bytes of control segments between text runs
    cur_ctrl = bytearray()    # control bytes accumulating after body text began
    first_text = None
    last_text = None
    in_body = False
    skip_reason = None
    cur_uc = 0

    def add_text(ch, start, end):
        nonlocal first_text, last_text, in_body, cur_ctrl
        if first_text is None:
            first_text = start
        if in_body and cur_ctrl:
            ctrl_segments.append(bytes(cur_ctrl))
            cur_ctrl = bytearray()
            text_runs.append([])
        text_runs[-1].append(ch)
        last_text = end
        in_body = True

    def add_ctrl(start, end):
        nonlocal cur_ctrl
        if in_body:
            cur_ctrl += rtf[start:end]

    while i < n:
        c = rtf[i]
        if c == 0x7B:                              # {
            ignore_stack.append(ignore_stack[-1])
            add_ctrl(i, i + 1)
            i += 1
            continue
        if c == 0x7D:                              # }
            if len(ignore_stack) > 1:
                ignore_stack.pop()
            add_ctrl(i, i + 1)
            i += 1
            continue
        if c == 0x5C:                              # backslash
            if i + 1 >= n:
                break
            nx = rtf[i + 1]
            if nx == 0x27:                         # \'hh
                try:
                    val = int(rtf[i + 2:i + 4], 16)
                except ValueError:
                    val = 0x20
                if not ignore_stack[-1]:
                    add_text(bytes([val]).decode("cp1252", "replace"), i, i + 4)
                else:
                    add_ctrl(i, i + 4)
                i += 4
                continue
            if nx in (0x0A, 0x0D):                 # backslash + newline = break
                if not ignore_stack[-1]:
                    add_text("\n", i, i + 2)
                else:
                    add_ctrl(i, i + 2)
                i += 2
                continue
            if nx == 0x2A:                         # \*  ignorable destination
                ignore_stack[-1] = True
                add_ctrl(i, i + 2)
                i += 2
                continue
            if not _is_alpha(nx):                  # control symbol
                ch = _SYMBOL_CHARS.get(nx)
                if not ignore_stack[-1] and ch is not None:
                    add_text(ch, i, i + 2)
                else:
                    add_ctrl(i, i + 2)
                i += 2
                continue
            # control word: \word [-] [digits] [single trailing space]
            j = i + 1
            while j < n and _is_alpha(rtf[j]):
                j += 1
            word = rtf[i + 1:j].decode("ascii", "replace")
            k = j
            if k < n and rtf[k] == 0x2D:
                k += 1
            while k < n and 0x30 <= rtf[k] <= 0x39:
                k += 1
            param = rtf[j:k]
            if k < n and rtf[k] == 0x20:
                k += 1
            if word in _DEST_WORDS:
                ignore_stack[-1] = True
                add_ctrl(i, k)
            elif word in ("par", "line"):
                if not ignore_stack[-1]:
                    add_text("\n", i, k)
                else:
                    add_ctrl(i, k)
            elif word == "uc":
                if param not in (b"0", b""):
                    skip_reason = "non-zero \\uc fallback"
                add_ctrl(i, k)
            elif word == "u":
                if not ignore_stack[-1]:
                    try:
                        val = int(param)
                    except ValueError:
                        val = None
                    if val in (0x2028, 0x2029):
                        add_text("\n", i, k)
                    elif val is not None:
                        add_text(chr(val), i, k)
                    else:
                        add_ctrl(i, k)
                else:
                    add_ctrl(i, k)
            else:
                add_ctrl(i, k)                     # any other formatting control
            i = k
            continue
        # raw byte
        if c in (0x0A, 0x0D):                      # ignorable whitespace
            add_ctrl(i, i + 1)
            i += 1
            continue
        if not ignore_stack[-1]:
            add_text(bytes([c]).decode("cp1252", "replace"), i, i + 1)
        else:
            add_ctrl(i, i + 1)
        i += 1

    # Build outputs.
    run_strings = ["".join(r) for r in text_runs]
    text = "".join(run_strings)
    coded = SENTINEL.join(run_strings)
    body_start = first_text if first_text is not None else n
    body_end = last_text if last_text is not None else n
    if skip_reason is None and not _cp1252_ok(text):
        skip_reason = "special glyph (non-cp1252)"
    # If there is leftover control after the last text run it belongs to the
    # suffix (rtf[body_end:]) and is preserved automatically.
    return RtfText(text, coded, body_start, body_end, ctrl_segments,
                   clean=(skip_reason is None), skip_reason=skip_reason)


def encode_run(text: str) -> bytes:
    out = bytearray()
    for ch in text:
        if ch == "\n":
            out += b"\\\n"
            continue
        if ch == "\\":
            out += b"\\\\"
            continue
        if ch == "{":
            out += b"\\{"
            continue
        if ch == "}":
            out += b"\\}"
            continue
        if ch == " ":
            out += b"\\~"
            continue
        cp = ord(ch)
        if cp < 0x80:
            out.append(cp)
            continue
        try:
            b = ch.encode("cp1252")
        except UnicodeEncodeError:
            out += ("\\u%d?" % cp).encode("ascii")
            continue
        out += ("\\'%02x" % b[0]).encode("ascii")
    return bytes(out)


def display(coded: str) -> str:
    return coded.replace(SENTINEL, "")


def splice(rtf: bytes, new_coded: str, parsed: RtfText):
    """Rebuild the payload with corrected text. Returns bytes, or None if the
    corrected text no longer matches the control-segment structure (skip)."""
    pieces = new_coded.split(SENTINEL)
    if len(pieces) != len(parsed.ctrl_segments) + 1:
        return None
    body = bytearray()
    body += encode_run(pieces[0])
    for idx, seg in enumerate(parsed.ctrl_segments):
        body += seg
        body += encode_run(pieces[idx + 1])
    return rtf[:parsed.body_start] + bytes(body) + rtf[parsed.body_end:]
