#!/usr/bin/env python3
"""Self-contained test suite (no pytest dependency).

Run:  python3 tests/run_tests.py
Covers the §11 verification matrix: rules, RTF codec, wire round-trip,
preservation invariants, no-op safety, and the non-song gate.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
FIX = os.path.join(ROOT, "tests", "fixtures")

from pro7corrector import wire, rtf, rules, presentation, song_gate, reviewed  # noqa

_passed = 0
_failed = 0


def check(name, cond, detail=""):
    global _passed, _failed
    if cond:
        _passed += 1
        print("  PASS  %s" % name)
    else:
        _failed += 1
        print("  FAIL  %s   %s" % (name, detail))


def eq(name, got, want):
    check(name, got == want, "got=%r want=%r" % (got, want))


# ---------------------------------------------------------------------------
print("\n[rules] divine / capitalization")
# second-person at line START is still capitalized by the (safe) first-word rule
eq("line-start You via first-word cap",
   rules.correct_text("you are good\nyour mercy").text, "You are good\nYour mercy")
# but MID-LINE second person is left to the AI pass (could be human-directed)
r_2p = rules.correct_text("To you who boast\nTomorrow's gain")
eq("mid-line second person NOT capitalized deterministically",
   r_2p.text, "To you who boast\nTomorrow’s gain")
check("mid-line second person flagged for AI",
      "second-person" in r_2p.flags, r_2p.flags)
r_one = rules.correct_text("he is the one who saves")
eq("the-one-who NOT changed deterministically",
   r_one.text, "He is the one who saves")
check("the-one-who flagged for AI", "relative-pronoun" in r_one.flags, r_one.flags)
eq("human pronouns stay lowercase",
   rules.correct_text("I told him he is loved").text, "I told him he is loved")
# church is house style (deterministic); the mid-line "your" goes to the AI pass
eq("church house style (your deferred to AI)",
   rules.correct_text("build your church").text, "Build your Church")
eq("first word cap", rules.correct_text("amazing grace").text, "Amazing grace")
eq("child of god -> God", rules.correct_text("I am a child of god").text,
   "I am a child of God")
eq("divine metaphors Lion/Lamb capitalized (singular)",
   rules.correct_text("behold the lion and the lamb").text,
   "Behold the Lion and the Lamb")
# "king" is a human title too -> left to the AI pass, not capitalized here
r_king = rules.correct_text("the splendor of a king")
eq("mid-line king NOT capitalized deterministically",
   r_king.text, "The splendor of a king")
check("king flagged for AI", "ambiguous-divine:'king'" in r_king.flags, r_king.flags)

print("\n[rules] word-initial quotes (elisions -> apostrophe, not opening quote)")
eq("'Twas -> apostrophe (elision)",
   rules.correct_text("'Twas grace that taught my heart").text,
   "’Twas grace that taught my heart")
eq("’Tis apostrophe preserved", rules.correct_text("’Tis grace").text,
   "’Tis grace")
eq("mis-converted ‘Cause healed to apostrophe",
   rules.correct_text("‘Cause I know").text, "’Cause I know")
eq("'Round -> apostrophe (elision)", rules.correct_text("'Round the throne").text,
   "’Round the throne")
check("elision not flagged",
      "word-initial-quote" not in rules.correct_text("'Cause I know").flags, "ok")
# A word-initial quote that is NOT a known elision is ambiguous -> flagged for
# the AI, and an opening quote the AI set is preserved (not reverted).
_wq = rules.correct_text("‘Holy’ is the cry")
eq("opening quote on non-elision preserved", _wq.text, "‘Holy’ is the cry")
check("non-elision word-initial quote flagged",
      "word-initial-quote" in _wq.flags, _wq.flags)
eq("mid/end apostrophes unaffected",
   rules.correct_text("don't stop\nGod's love").text, "Don’t stop\nGod’s love")
eq("opening single quote encodes to cp1252 \\'91",
   rtf.encode_run("‘Twas"), b"\\'91Twas")

print("\n[rules] mid-word capitals")
eq("stray mid-word cap lowercased",
   rules.correct_text("come evEry battle").text, "Come every battle")
eq("multiple mid-word caps", rules.correct_text("JeSUS reigns").text, "Jesus reigns")
eq("all-caps word still normalized", rules.correct_text("GOD is good").text,
   "God is good")
eq("legit first-letter caps preserved",
   rules.correct_text("Holy Spirit fall").text, "Holy Spirit fall")

print("\n[rules] hallelujah is an exclamation, not a forced divine name")
eq("lowercase hallelujah NOT force-capitalized mid-line",
   rules.correct_text("sing a hallelujah tonight").text, "Sing a hallelujah tonight")
eq("hallelujah at line start capitalized by the first-word rule",
   rules.correct_text("hallelujah").text, "Hallelujah")

print("\n[rules] attributes are always lowercase mid-line (never titles)")
eq("grace/glory/blood/majesty/mercy/kingdom lowercased mid-line",
   rules.correct_text("By His Grace and Glory and Blood and Majesty and Mercy and Kingdom").text,
   "By His grace and glory and blood and majesty and mercy and kingdom")
eq("amazing grace stays lowercase", rules.correct_text("Amazing Grace how sweet").text,
   "Amazing grace how sweet")
eq("standalone Holy lowercased mid-line", rules.correct_text("Our God is Holy").text,
   "Our God is holy")
eq("Holy Spirit title preserved mid-line",
   rules.correct_text("Come Holy Spirit").text, "Come Holy Spirit")
eq("Holy Ghost title preserved mid-line",
   rules.correct_text("Father Son and Holy Ghost").text, "Father Son and Holy Ghost")
eq("Holy One title preserved mid-line",
   rules.correct_text("You are the Holy One").text, "You are the Holy One")
eq("church stays capitalized (house style)",
   rules.correct_text("build your church").text, "Build your Church")
eq("cross always lowercase mid-line", rules.correct_text("nailed to the Cross").text,
   "Nailed to the cross")
check("cross no longer flagged for AI",
      "ambiguous-divine:'cross'" not in rules.correct_text("at the cross i bow").flags, "")
check("name still flagged for AI (context-dependent)",
      "ambiguous-divine:'name'" in rules.correct_text("praise his name forever").flags, "")
check("grace no longer flagged for AI",
      "ambiguous-divine:'grace'" not in rules.correct_text("your grace is enough").flags, "")

print("\n[rules] stray mid-line function-word capitals + first-person pronouns")
eq("function words lowercased mid-line",
   rules.correct_text("Glory To God In The highest").text, "Glory to God in the highest")
eq("'In Your name' -> 'in Your name'",
   rules.correct_text("there’s salvation In Your name").text,
   "There’s salvation in Your name")
check("first-person me/my flagged for AI",
      "first-person" in rules.correct_text("come to me and follow me").flags, "")
eq("first-person not changed deterministically (AI decides)",
   rules.correct_text("hold my hand and lead me").text, "Hold my hand and lead me")

print("\n[rules] punctuation")
eq("smart apostrophes",
   rules.correct_text("you're so\nGod's love\ndon't stop").text,
   "You’re so\nGod’s love\nDon’t stop")
eq("smart quotes", rules.correct_text('"holy holy holy"').text,
   "“Holy holy holy”")
eq("feet/inches preserved", rules.correct_text("it was 6'2\" tall").text,
   "It was 6'2\" tall")

print("\n[rules] spelling / caps / spacing")
eq("american spelling", rules.correct_text("our Saviour reigns").text,
   "Our Savior reigns")
eq("honour->honor", rules.correct_text("all honour to the King").text,
   "All honor to the King")
eq("all-caps -> sentence",
   rules.correct_text("HOLY IS THE LORD GOD ALMIGHTY").text,
   "Holy is the Lord God Almighty")
eq("midline decap", rules.correct_text("Let the World see Your glory").text,
   "Let the world see Your glory")
eq("double-space cleanup", rules.correct_text("we  have   spaces").text,
   "We have spaces")

print("\n[rules] flags & no-op")
r = rules.correct_text("the spirit and the word")
check("ambiguous flagged", any("spirit" in f for f in r.flags), r.flags)
r2 = rules.correct_text("You are good\nYour mercy")
check("already-correct -> no change", not r2.changed)

print("\n[rtf] codec round-trip & no-op identity")
ag = open(os.path.join(FIX, "amazing_grace.pro"), "rb").read()
tree = wire.parse(ag)
eq("wire round-trip byte-exact", wire.serialize(tree), ag)
clean = roundtrip = ident = 0
for _, node in wire.find_rtf_leaves(tree):
    pt = rtf.extract(node[2])
    if pt.clean:
        clean += 1
        out = rtf.splice(node[2], pt.coded, pt)        # no-op splice (coded)
        if out is not None and rtf.extract(out).text == pt.text:
            roundtrip += 1
        if out == node[2]:
            ident += 1
check("no-op splice semantic round-trip for ALL clean payloads",
      clean == roundtrip, "%d/%d" % (roundtrip, clean))
check("no-op splice byte-identical for clean payloads", clean == ident,
      "%d/%d (rest differ only by benign soft-break normalization)"
      % (ident, clean))

eq("rtf extract line breaks",
   rtf.extract(b"{\\rtf1\\fs152 line one\\\nline two}").text, "line one\nline two")
eq("rtf cp1252 decode",
   rtf.extract(b"{\\rtf1\\fs152 it\\'92s here}").text, "it’s here")
eq("rtf u2028 as break",
   rtf.extract(b"{\\rtf1\\fs152 a\\uc0\\u8232 b}").text, "a\nb")
eq("smart apostrophe encodes to \\'92", rtf.encode_run("it’s"), b"it\\'92s")

print("\n[pipeline] preservation & verification")
res = presentation.process_bytes(ag)
check("Amazing Grace fixture changed", res.changed)
check("verification passed (no error)", res.error is None, res.error)
ot, nt = wire.parse(ag), wire.parse(res.new_bytes)
eq("cue count preserved",
   sum(1 for n in ot if n[1] == 13), sum(1 for n in nt if n[1] == 13))
eq("rtf leaf count preserved",
   len(wire.find_rtf_leaves(ot)), len(wire.find_rtf_leaves(nt)))
eq("non-lyric structure byte-identical",
   presentation._blank_rtf_serialize(ot),
   presentation._blank_rtf_serialize(nt))
res2 = presentation.process_bytes(res.new_bytes)
check("idempotent (2nd pass no change)", not res2.changed)

ag2 = presentation.process_bytes(ag).new_bytes or ag   # correct once
check("idempotent: a corrected file produces no further write",
      presentation.process_bytes(ag2).new_bytes is None)

print("\n[title] internal title set to filename, structure preserved")
# force a wrong title into the Amazing Grace fixture, then correct it back
t = wire.parse(ag)
tn = presentation._find_title_node(t)
tn[2] = b"amazing_grace"
wrong = wire.serialize(t)
tr = presentation.process_bytes(wrong, desired_title="Amazing Grace")
check("title change detected", tr.title_change == ("amazing_grace", "Amazing Grace"))
eq("new title is the filename",
   presentation.presentation_title(wire.parse(tr.new_bytes)), "Amazing Grace")
check("title-only verification preserves structure", tr.error is None, tr.error)
check("matching title -> no title change",
      presentation.process_bytes(ag, desired_title="Amazing Grace").title_change is None)
# regression: a title whose bytes coincidentally parse as protobuf wire format
# (e.g. "After You" = 0x41 + 8 bytes) must still verify and round-trip.
tr2 = presentation.process_bytes(wrong, desired_title="After You")
check("message-like title verifies (no error)", tr2.error is None, tr2.error)
eq("message-like title round-trips",
   presentation.presentation_title(wire.parse(tr2.new_bytes)), "After You")

print("\n[gate] non-song detection")
# synthesize a sermon-named file from a real one
check("Sermon.pro name skipped",
      not song_gate.classify("/x/Sermon.pro", ag)[0])
check("real song passes gate", song_gate.classify("/x/Amazing Grace.pro", ag)[0])
# empty-RTF presentation (strip lyric leaves) -> not a song
empty = wire.parse(ag)
for _, node in wire.find_rtf_leaves(empty):
    node[2] = b"{\\rtf1\\fs152 }"
check("no-lyric presentation skipped",
      not song_gate.classify("/x/Empty.pro", wire.serialize(empty))[0])

print("\n[reviewed] AI-review fingerprint gating (queue only changed songs)")
import tempfile  # noqa
_p_ag = os.path.join(FIX, "amazing_grace.pro")
_fp = reviewed.fingerprint(ag)
check("fingerprint is stable for same bytes", _fp and _fp == reviewed.fingerprint(ag), _fp)
check("fingerprint differs across different songs",
      reviewed.fingerprint(ag2) != _fp, "")
check("already_reviewed True when fingerprint matches the map",
      reviewed.already_reviewed(_p_ag, ag, {_p_ag: _fp}), "")
check("already_reviewed False when song absent from map",
      not reviewed.already_reviewed(_p_ag, ag, {}), "")
check("already_reviewed False when fingerprint differs (lyrics changed)",
      not reviewed.already_reviewed(_p_ag, ag, {_p_ag: "stale-hash"}), "")
_tmp = tempfile.mktemp(suffix=".json")
reviewed.save({_p_ag: _fp}, _tmp)
check("reviewed map save/load round-trips", reviewed.load(_tmp).get(_p_ag) == _fp, "")
os.remove(_tmp)

print("\n[cli] setup path commands")
import pro7_lyric_corrector as cli  # noqa
_p = cli.build_parser()
_args = _p.parse_args(["calibrate", "--all", "--per-file", "0"])
check("calibrate can show a full no-write draft",
      _args.command == "calibrate" and _args.all and _args.per_file == 0, _args)
_args = _p.parse_args(["review", "--file", "Song.pro"])
check("review command parses",
      _args.command == "review" and _args.file == "Song.pro", _args)
_args = _p.parse_args(["apply-once", "--review"])
check("apply-once --review parses",
      _args.command == "apply-once" and _args.review, _args)

# ---------------------------------------------------------------------------
print("\n%d passed, %d failed" % (_passed, _failed))
sys.exit(1 if _failed else 0)
