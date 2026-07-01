"""Deterministic worship-lyric correction rules (no AI, no network).

This is the always-on layer. Every transform here is conservative and provable
in code. Genuinely ambiguous theological capitalization (spirit/Spirit,
word/Word, name/Name, father/Father ...) is *flagged* for the optional nightly
AI pass rather than guessed at.

`correct_text(text)` returns a CorrectionResult with the new text, a `changed`
flag, a list of human-readable change `notes`, and a list of `flags`
(ambiguities to hand to the AI queue). Operates on the *logical* slide text
(line breaks as "\n"); the RTF codec handles cp1252 escaping on the way back.
"""

from __future__ import annotations
import re

# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------

# Unambiguous divine / proper names -> always capitalized when found lowercase.
ALWAYS_CAP = {
    "god": "God", "jesus": "Jesus", "christ": "Christ", "messiah": "Messiah",
    "emmanuel": "Emmanuel", "immanuel": "Immanuel", "yahweh": "Yahweh",
    "jehovah": "Jehovah", "adonai": "Adonai", "elohim": "Elohim",
    # NOTE: hallelujah / alleluia / hosanna are exclamations, NOT names of God.
    # They are capitalized as a standalone shout or at the start of a line (the
    # first-word rule handles that), but lowercase as a common noun ("give Him
    # your hallelujah", "sing a hallelujah"). So they are NOT force-capitalized
    # here; the AI pass lowercases the common-noun uses in context.
    "calvary": "Calvary", "zion": "Zion", "bethlehem": "Bethlehem",
    "galilee": "Galilee", "nazareth": "Nazareth", "jerusalem": "Jerusalem",
    "israel": "Israel", "judah": "Judah", "alpha": "Alpha", "omega": "Omega",
    "lord": "Lord", "savior": "Savior", "saviour": "Savior",
    "redeemer": "Redeemer", "almighty": "Almighty", "abba": "Abba",
    # Lion / Lamb are clear divine metaphors in worship (Lion of Judah, Lamb of
    # God) and are not human roles, so they stay deterministic. "King" is a human
    # title too ("kings bow down"), so it is handled by the AI pass instead --
    # see AMBIGUOUS_DIVINE. Plurals (lions/lambs) are not here.
    "lion": "Lion", "lamb": "Lamb",
}

# Second-person address. Context-dependent (God vs. a human), so the
# deterministic layer does NOT recase these -- they are flagged for the AI pass.
# (Kept as a set of words; the mapping is unused now but documents the forms.)
SECOND_PERSON = {
    "you": "You", "your": "Your", "yours": "Yours", "yourself": "Yourself",
    "yourselves": "Yourselves", "thee": "Thee", "thou": "Thou",
    "thy": "Thy", "thine": "Thine",
}

# Third-person pronouns for God ("He/Him/His") are equally context-dependent
# (could be a human "he"), so they are flagged for the AI pass too.
THIRD_PERSON = {"he", "him", "his", "himself"}

# First-person pronouns are capitalized when GOD/JESUS is the speaker ("Come to
# Me", "Follow Me" -- the red-letter words of Christ) and lowercase for the
# worshipper ("my heart", "save me"). Context-dependent -> flagged for the AI,
# never changed deterministically. ("I" is always capital -- see _pronoun_i.)
FIRST_PERSON = {"me", "my", "mine", "myself"}

# Multi-word divine titles -> canonical capitalization (phrase context is safe).
PHRASE_RULES = [
    (re.compile(r"\bking of kings\b", re.I), "King of Kings"),
    (re.compile(r"\blord of lords\b", re.I), "Lord of Lords"),
    (re.compile(r"\bson of man\b", re.I), "Son of Man"),
    (re.compile(r"\bson of god\b", re.I), "Son of God"),
    (re.compile(r"\blamb of god\b", re.I), "Lamb of God"),
    (re.compile(r"\blion of judah\b", re.I), "Lion of Judah"),
    (re.compile(r"\bholy one\b", re.I), "Holy One"),
    (re.compile(r"\bholy spirit\b", re.I), "Holy Spirit"),
    (re.compile(r"\bholy ghost\b", re.I), "Holy Ghost"),
    (re.compile(r"\bprince of peace\b", re.I), "Prince of Peace"),
    (re.compile(r"\bmorning star\b", re.I), "Morning Star"),
    (re.compile(r"\bthe great i am\b", re.I), "the Great I Am"),
    # NOTE: "the one who/whom" -> "the One Who/Whom" and second-person You/Your
    # capitalization are context-dependent (the referent may be human, e.g.
    # "To you who boast / Tomorrow's gain"). Those are deliberately NOT done here
    # -- they are flagged for the AI routine instead. See _flag_for_ai().
]

# House style.
HOUSE_CAP = {"church": "Church"}

# Ambiguous: depends on whether the referent is divine. Leave unchanged, flag.
AMBIGUOUS_DIVINE = {
    "spirit", "word", "name", "father", "son",
    "king", "rock", "shepherd", "light", "life", "way",
    "truth", "vine", "bread", "gate", "door", "branch", "root", "dove",
    "one", "master", "author",
}
# NOTE: grace / glory / blood / majesty / mercy / kingdom / holy / cross are NOT
# here -- they are attributes/common nouns, never titles, so they are ALWAYS
# lowercase mid-line (see COMMON_WORDS). ("cross" was moved out of the AI's
# context-dependent set: reverential-vs-literal "Cross" produced too many wrong
# capitalizations, so it is simply always lowercase now.) "Holy Spirit / Holy
# Ghost / Holy One" stay capitalized via PHRASE_RULES (and _midline_decap keeps
# "holy" capital right before Spirit/Ghost/One). Only "name" stays AI-judged --
# "the Name" of God vs. a generic name.

# American spelling (case pattern preserved by apply_case).
SPELLING = {
    "saviour": "savior", "honour": "honor", "honours": "honors",
    "honoured": "honored", "honouring": "honoring", "favour": "favor",
    "favours": "favors", "favoured": "favored", "favouring": "favoring",
    "colour": "color", "colours": "colors", "coloured": "colored",
    "glamour": "glamor", "labour": "labor", "labours": "labors",
    "neighbour": "neighbor", "neighbours": "neighbors", "splendour": "splendor",
    "valour": "valor", "ardour": "ardor", "fervour": "fervor",
    "vapour": "vapor", "vapours": "vapors", "clamour": "clamor",
    "centre": "center", "centres": "centers", "theatre": "theater",
    "fibre": "fiber", "sceptre": "scepter", "sombre": "somber",
    "travelling": "traveling", "travelled": "traveled", "traveller": "traveler",
    "marvellous": "marvelous", "counsellor": "counselor",
    "counsellors": "counselors", "jewellery": "jewelry", "defence": "defense",
    "offence": "offense", "fulfil": "fulfill", "fulfilment": "fulfillment",
    "worshipper": "worshiper", "worshippers": "worshipers",
    "worshipping": "worshiping",
}

# Conservative, well-known worship-lyric typos only.
TYPOS = {
    "alright": "all right", "untill": "until", "recieve": "receive",
    "beleive": "believe", "definately": "definitely", "seperate": "separate",
    "freind": "friend", "thier": "their", "wich": "which", "halleluiah": "hallelujah",
}

# Common words that are safe to de-capitalize mid-line. Deliberately excludes
# proper nouns, personal names, and ambiguous-divine words.
COMMON_WORDS = {
    "world", "see", "saw", "seen", "let", "all", "every", "when", "where",
    "while", "before", "after", "above", "below", "through", "beyond",
    "within", "without", "again", "today", "tonight", "forever", "always",
    "never", "here", "there", "now", "then", "come", "came", "coming", "go",
    "goes", "going", "gone", "run", "running", "walk", "walking", "stand",
    "standing", "rise", "rising", "fall", "falling", "fell", "hold", "holding",
    "held", "give", "giving", "given", "gave", "take", "taking", "taken",
    "took", "bring", "bringing", "brought", "shout", "shouting", "cry",
    "crying", "call", "calling", "wait", "waiting", "seek", "seeking", "find",
    "finding", "found", "know", "knowing", "knew", "known", "feel", "feeling",
    "hear", "hearing", "speak", "speaking", "tell", "telling", "make",
    "making", "made", "open", "close", "high", "low", "deep", "wide", "far",
    "near", "good", "great", "strong", "sweet", "bright", "morning",
    "evening", "river", "sea", "ocean", "mountain", "mountains", "valley",
    "ground", "earth", "sky", "wind", "rain", "storm", "sun", "moon", "star",
    "stars", "song", "songs", "sing", "singing", "praise", "praises",
    "wonder", "wonders", "love", "loving", "loved", "joy", "peace", "hope",
    "fear", "darkness", "shadow", "shadows", "ever", "more", "most", "many",
    "much", "old", "new", "free", "alive", "awake", "anew",
    # Christian common-nouns / attributes that are never names or titles -> always
    # lowercase mid-line. "holy" is here too, but _midline_decap keeps it capital
    # right before Spirit/Ghost/One so those titles survive.
    "grace", "glory", "glories", "blood", "mercy", "mercies",
    "majesty", "majesties", "kingdom", "kingdoms", "holy",
    "cross", "crosses",
}

# Grammatical function words (articles, conjunctions, prepositions, auxiliaries).
# These are NEVER capitalized mid-line in lyrics -- a capital one is a stray
# typo, so _midline_decap lowercases them. Deliberately excludes pronouns
# (handled elsewhere / context-dependent) and the vocative "O".
FUNCTION_WORDS = {
    "a", "an", "the",
    "and", "but", "or", "nor", "yet", "so", "for", "as", "than", "if",
    "though", "although", "because", "unless", "until", "till", "while",
    "in", "on", "at", "of", "to", "by", "with", "from", "into", "unto",
    "onto", "upon", "over", "under", "beneath", "beside", "between", "among",
    "through", "throughout", "around", "about", "before", "after", "behind",
    "within", "without", "against", "toward", "towards", "across", "along",
    "beyond", "near", "off", "out", "up", "down",
    "is", "are", "am", "was", "were", "be", "been", "being", "do", "does",
    "did", "has", "have", "had", "having", "will", "would", "shall", "should",
    "can", "could", "may", "might", "must",
    "not", "no", "this", "that", "these", "those",
}

ACRONYMS = set()  # none expected in lyrics; extend if needed


# ---------------------------------------------------------------------------
# Result container & config
# ---------------------------------------------------------------------------

class CorrectionResult:
    __slots__ = ("text", "changed", "notes", "flags")

    def __init__(self, text, changed, notes, flags):
        self.text = text
        self.changed = changed
        self.notes = notes
        self.flags = flags


class Config:
    # divine_second_person default OFF: capitalizing You/Your toward God vs a
    # human ("you who boast") is context-dependent, so it is left to the AI pass.
    def __init__(self, divine_second_person=False, allcaps=True, spelling=True,
                 smart_punct=True, midline=True, typos=True, divine=True,
                 fix_title=True, intercaps=True):
        self.divine_second_person = divine_second_person
        self.allcaps = allcaps
        self.spelling = spelling
        self.smart_punct = smart_punct
        self.midline = midline
        self.typos = typos
        self.divine = divine
        self.fix_title = fix_title       # set internal title to the filename
        self.intercaps = intercaps       # lowercase stray mid-word capitals


DEFAULT = Config()

_WORD_RE = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)*")
_APOS = "’"   # right single quotation mark (cp1252 0x92)
_LSQ = "‘"    # left single quote  (cp1252 0x91)
_LDQ = "“"    # left double quote  (cp1252 0x93)
_RDQ = "”"    # right double quote (cp1252 0x94)

# A single quote starting a word. This is AMBIGUOUS: it is usually an elision
# (the mark stands for dropped letters -> right single quote / apostrophe), but
# it can also open a genuine single-quoted phrase (-> left/opening single quote).
# A blind rule cannot tell these apart, so the deterministic layer only fixes the
# KNOWN front-clipped elisions in ELISIONS (where it is 100% reliable: those are
# always apostrophes). Every OTHER word-initial single quote is left untouched
# and flagged for the AI pass to decide -- which also means we never revert an
# opening quote the AI deliberately set. The capture group is the following word.
_WORD_INITIAL_QUOTE = re.compile(r"(?<![A-Za-z0-9])['’‘]([A-Za-z]+)")

# Front-clipped elisions whose leading mark is ALWAYS an apostrophe, never an
# opening quote. Matched case-insensitively on the word after the quote.
ELISIONS = {
    "cause", "twas", "tis", "twill", "til", "till", "em",
    "round", "neath", "gainst", "fore", "bout", "cept", "nuff", "n",
}


def apply_case(template_word: str, lower_replacement: str) -> str:
    """Map a lowercase replacement onto the case pattern of template_word."""
    if template_word.isupper() and len(template_word) > 1:
        return lower_replacement.upper()
    if template_word[:1].isupper():
        return lower_replacement[:1].upper() + lower_replacement[1:]
    return lower_replacement


def is_allcaps_word(w: str) -> bool:
    return len(w) > 1 and w.isupper() and w.isalpha()


# ---------------------------------------------------------------------------
# Per-line transforms
# ---------------------------------------------------------------------------

def _smart_punctuation(line: str, notes):
    # Known front-clipped elisions ('Cause, 'Twas, 'Till, 'em, ...) -> apostrophe
    # (also heals files an earlier rule mis-converted to an opening quote). Any
    # OTHER word-initial single quote is left as-is and flagged for the AI pass
    # (it may be a genuine opening quote); see _flag_for_ai.
    def _elision(m):
        return (_APOS + m.group(1)) if m.group(1).lower() in ELISIONS else m.group(0)
    line = _WORD_INITIAL_QUOTE.sub(_elision, line)
    out = []
    n = len(line)
    for i, ch in enumerate(line):
        if ch == "'":
            prev = line[i - 1] if i > 0 else ""
            nxt = line[i + 1] if i + 1 < n else ""
            # contraction/possessive: letter on at least one side, not feet/inches
            if prev.isalpha() and (nxt.isalpha() or not nxt.strip() or nxt in ".,!?;:)"):
                out.append(_APOS)
                continue
            if prev.isalpha() or nxt.isalpha():
                out.append(_APOS)
                continue
            out.append(ch)  # leave (e.g. feet/inches after a digit)
        else:
            out.append(ch)
    line2 = "".join(out)
    # double quotes -> curly, alternating per line. A " right after a digit is
    # an inches mark -> leave straight and don't disturb the open/close pairing.
    if '"' in line2:
        res = []
        opened = False
        for i, ch in enumerate(line2):
            if ch == '"':
                prev = line2[i - 1] if i > 0 else ""
                if prev.isdigit():
                    res.append('"')
                    continue
                res.append(_RDQ if opened else _LDQ)
                opened = not opened
            else:
                res.append(ch)
        line2 = "".join(res)
    if line2 != line:
        notes.append("smart-punct")
    return line2


def _allcaps_to_base(line: str, notes):
    def repl(m):
        w = m.group(0)
        if is_allcaps_word(w) and w not in ACRONYMS and w.lower() not in ("i",):
            return w.capitalize() if False else w.lower()
        return w
    new = _WORD_RE.sub(repl, line)
    if new != line:
        notes.append("allcaps->sentence")
    return new


def _fix_intercaps(line: str, notes):
    """Lowercase stray mid-word capitals (e.g. 'evEry' -> 'every').

    Worship vocabulary has no legitimate intra-word capitals (no 'McDonald'),
    so any uppercase letter that is not a word's first letter is a typo. Fully
    upper-case words are left to _allcaps_to_base; the first letter's case is
    preserved (line-start capitalization is handled by _first_word_cap, mid-line
    common-word lowercasing by _midline_decap).
    """
    def repl(m):
        w = m.group(0)
        if w.isupper():
            return w  # all-caps emphasis -> handled by _allcaps_to_base
        fixed = w[0] + "".join(c.lower() if c.isupper() else c for c in w[1:])
        if fixed != w:
            notes.append("intercaps:%s->%s" % (w, fixed))
        return fixed
    return _WORD_RE.sub(repl, line)


def _spelling(line: str, notes):
    def repl(m):
        w = m.group(0)
        low = w.lower()
        if low in SPELLING:
            return apply_case(w, SPELLING[low])
        return w
    new = _WORD_RE.sub(repl, line)
    if new != line:
        notes.append("us-spelling")
    return new


def _typos(line: str, notes):
    def repl(m):
        w = m.group(0)
        low = w.lower()
        if low in TYPOS:
            rep = TYPOS[low]
            return apply_case(w, rep) if rep[:1].islower() else rep
        return w
    new = _WORD_RE.sub(repl, line)
    if new != line:
        notes.append("typo-fix")
    return new


def _divine_words(line: str, cfg, notes, flags):
    # phrase rules first
    for rx, canon in PHRASE_RULES:
        if rx.search(line):
            line = rx.sub(canon, line)
            notes.append("divine-phrase")
    def repl(m):
        w = m.group(0)
        low = w.lower()
        if low in ALWAYS_CAP:
            rep = ALWAYS_CAP[low]
            if w != rep:
                notes.append("divine-cap:%s" % low)
            return rep
        if low in HOUSE_CAP:
            rep = HOUSE_CAP[low]
            if w != rep:
                notes.append("house-cap:%s" % low)
            return rep
        if cfg.divine_second_person and low in SECOND_PERSON:
            rep = SECOND_PERSON[low]
            if w != rep:
                notes.append("divine-2p:%s" % low)
            return rep
        if low in AMBIGUOUS_DIVINE and w[:1].islower():
            flags.append("ambiguous-divine:'%s'" % low)
        return w
    return _WORD_RE.sub(repl, line)


def _pronoun_i(line: str, notes):
    def repl(m):
        w = m.group(0)
        if w == "i":
            notes.append("pronoun-I")
            return "I"
        if w[:1] == "i" and len(w) > 1 and w[1] in "'’":
            return "I" + w[1:]
        return w
    return _WORD_RE.sub(repl, line)


def _midline_decap(line: str, notes):
    """Lowercase mid-line capitalized COMMON_WORDS (not the first word)."""
    matches = list(_WORD_RE.finditer(line))
    if not matches:
        return line
    out = line
    # rebuild left-to-right
    pieces = []
    last = 0
    for idx, m in enumerate(matches):
        pieces.append(line[last:m.start()])
        w = m.group(0)
        if idx == 0:
            pieces.append(w)
        else:
            low = w.lower()
            nxt = matches[idx + 1].group(0).lower() if idx + 1 < len(matches) else ""
            # "Holy" stays capital when it heads a divine title (Holy Spirit /
            # Holy Ghost / Holy One); elsewhere it lowercases like any attribute.
            holy_title = low == "holy" and nxt in ("spirit", "ghost", "one")
            if (w[:1].isupper() and not w.isupper()
                    and (low in COMMON_WORDS or low in FUNCTION_WORDS)
                    and not holy_title
                    and low not in ALWAYS_CAP and low not in SECOND_PERSON
                    and low not in HOUSE_CAP and low not in AMBIGUOUS_DIVINE):
                pieces.append(low)
                notes.append("midline-decap:%s" % low)
            else:
                pieces.append(w)
        last = m.end()
    pieces.append(line[last:])
    return "".join(pieces)


def _first_word_cap(line: str, notes):
    m = _WORD_RE.search(line)
    if not m:
        return line
    # don't recapitalize if line intentionally starts with punctuation+lowercase?
    w = m.group(0)
    if w[:1].islower():
        new = line[:m.start()] + w[:1].upper() + w[1:] + line[m.end():]
        notes.append("first-word-cap")
        return new
    return line


def _collapse_spaces(line: str, notes):
    new = re.sub(r"[ \t]{2,}", " ", line).rstrip()
    if new != line:
        notes.append("spacing")
    return new


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

_ONE_WHO_RE = re.compile(r"\bthe one whom?\b", re.I)


def _flag_for_ai(line, flags):
    """Flag context-dependent casing for the AI routine (do NOT change here).

    The deterministic layer only capitalizes words that are reliably divine in
    worship (proper names of God plus Lord/Savior/Redeemer/Lion/Lamb). Anything
    that could refer to a human (so capitalizing it might be wrong) OR that the
    deterministic layer leaves lowercase but might mean God is flagged here for
    the AI pass instead. Line-start words are capitalized by the safe first-word
    rule, so only MID-LINE occurrences are flagged.
    """
    words = _WORD_RE.findall(line)
    for i, w in enumerate(words):
        if i == 0:
            continue
        low = w.lower()
        if low in SECOND_PERSON and "second-person" not in flags:
            flags.append("second-person")
        if low in THIRD_PERSON and "third-person" not in flags:
            flags.append("third-person")
        if low in FIRST_PERSON and "first-person" not in flags:
            flags.append("first-person")
    if _ONE_WHO_RE.search(line) and "relative-pronoun" not in flags:
        flags.append("relative-pronoun")
    # A word-initial single quote that is NOT a known elision is ambiguous
    # (apostrophe vs. opening quote) -> let the AI decide.
    for m in _WORD_INITIAL_QUOTE.finditer(line):
        if m.group(1).lower() not in ELISIONS:
            if "word-initial-quote" not in flags:
                flags.append("word-initial-quote")
            break


def correct_line(line: str, cfg, notes, flags):
    if not line.strip():
        return ""
    _flag_for_ai(line, flags)
    if cfg.spelling:
        line = _spelling(line, notes)
    if cfg.typos:
        line = _typos(line, notes)
    if cfg.allcaps:
        line = _allcaps_to_base(line, notes)
    if cfg.intercaps:
        line = _fix_intercaps(line, notes)
    if cfg.smart_punct:
        line = _smart_punctuation(line, notes)
    if cfg.divine:
        line = _divine_words(line, cfg, notes, flags)
    line = _pronoun_i(line, notes)
    if cfg.midline:
        line = _midline_decap(line, notes)
    line = _first_word_cap(line, notes)
    line = _collapse_spaces(line, notes)
    return line


def _clean_blank_lines(lines):
    # strip leading/trailing blank lines; collapse 2+ internal blanks to 1
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    out = []
    blank = False
    for ln in lines:
        if not ln.strip():
            if blank:
                continue
            blank = True
            out.append("")
        else:
            blank = False
            out.append(ln)
    return out


def correct_text(text: str, cfg: Config = DEFAULT) -> CorrectionResult:
    notes = []
    flags = []
    lines = text.split("\n")
    corrected = [correct_line(ln, cfg, notes, flags) for ln in lines]
    corrected = _clean_blank_lines(corrected)
    new_text = "\n".join(corrected)
    if new_text != text and not corrected and text.strip() == "":
        new_text = text  # don't churn whitespace-only payloads
    changed = new_text != text
    if not changed:
        notes = []
    return CorrectionResult(new_text, changed, notes, flags)
