"""Zero-dependency Protocol Buffers wire-format codec.

ProPresenter 7 `.pro` files are binary protobuf. Rather than depend on an
unofficial, possibly-stale `.proto` schema plus a `protoc` toolchain (neither of
which is installable on the bare system Python this ships on), we parse the raw
wire format generically into a tree, let callers edit individual leaf values,
and re-serialize. Because every length prefix is recomputed on serialize, an
edited leaf safely propagates new lengths up the whole parent chain.

Safety property proven against the real library: parsing every `.pro` file and
serializing it back reproduces the original bytes exactly (byte-for-byte) for
all 392 songs. So an unchanged file produces zero diff, and a changed file
differs only in the edited leaf and its ancestors' length prefixes.

Node representation (mutable lists so callers can edit in place):
    ['v',   field_no, int]      varint (wire type 0)
    ['f64', field_no, bytes]    fixed64 (wire type 1) -- raw 8 bytes preserved
    ['b',   field_no, bytes]    length-delimited leaf (string/bytes) (wire type 2)
    ['m',   field_no, [nodes]]  length-delimited sub-message (wire type 2)
    ['f32', field_no, bytes]    fixed32 (wire type 5) -- raw 4 bytes preserved

Length-delimited payloads are heuristically classified as sub-messages vs.
opaque leaves. Misclassification is harmless for round-trip fidelity because
re-serialization reproduces identical bytes either way; the classification only
guides traversal (e.g. locating RTF leaves).
"""

from __future__ import annotations

RTF_MAGIC = b"{\\rtf1"
_MAX_DEPTH = 40


class WireError(ValueError):
    """Raised when bytes are not parseable as protobuf wire format."""


def read_varint(buf: bytes, i: int):
    shift = 0
    result = 0
    n = len(buf)
    while True:
        if i >= n:
            raise WireError("truncated varint")
        byte = buf[i]
        i += 1
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return result, i
        shift += 7
        if shift > 70:
            raise WireError("varint too long")


def encode_varint(value: int) -> bytes:
    out = bytearray()
    while True:
        b = value & 0x7F
        value >>= 7
        if value:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _looks_like_message(payload: bytes) -> bool:
    """True if payload cleanly parses as a sequence of protobuf fields."""
    if not payload:
        return False
    if payload.startswith(RTF_MAGIC):      # RTF text leaf, never a sub-message
        return False
    i = 0
    n = len(payload)
    try:
        while i < n:
            tag, i = read_varint(payload, i)
            wt = tag & 7
            fn = tag >> 3
            if fn == 0:
                return False
            if wt == 0:
                _, i = read_varint(payload, i)
            elif wt == 2:
                ln, i = read_varint(payload, i)
                if i + ln > n:
                    return False
                i += ln
            elif wt == 5:
                i += 4
            elif wt == 1:
                i += 8
            else:
                return False
        return i == n
    except WireError:
        return False


def parse(buf: bytes, _depth: int = 0):
    """Parse protobuf bytes into a list of mutable node lists."""
    nodes = []
    i = 0
    n = len(buf)
    while i < n:
        tag, i = read_varint(buf, i)
        wt = tag & 7
        fn = tag >> 3
        if fn == 0:
            raise WireError("field number 0")
        if wt == 0:
            v, i = read_varint(buf, i)
            nodes.append(["v", fn, v])
        elif wt == 5:
            nodes.append(["f32", fn, buf[i:i + 4]])
            i += 4
        elif wt == 1:
            nodes.append(["f64", fn, buf[i:i + 8]])
            i += 8
        elif wt == 2:
            ln, i = read_varint(buf, i)
            payload = buf[i:i + ln]
            if len(payload) != ln:
                raise WireError("truncated length-delimited field")
            i += ln
            if _depth < _MAX_DEPTH and _looks_like_message(payload):
                nodes.append(["m", fn, parse(payload, _depth + 1)])
            else:
                nodes.append(["b", fn, payload])
        else:
            raise WireError("unsupported wire type %d (field %d)" % (wt, fn))
    return nodes


def serialize(nodes) -> bytes:
    """Serialize a node tree back to protobuf bytes, recomputing all lengths."""
    out = bytearray()
    for node in nodes:
        kind = node[0]
        fn = node[1]
        if kind == "v":
            out += encode_varint((fn << 3) | 0)
            out += encode_varint(node[2])
        elif kind == "f32":
            out += encode_varint((fn << 3) | 5)
            out += node[2]
        elif kind == "f64":
            out += encode_varint((fn << 3) | 1)
            out += node[2]
        elif kind == "b":
            out += encode_varint((fn << 3) | 2)
            out += encode_varint(len(node[2]))
            out += node[2]
        elif kind == "m":
            payload = serialize(node[2])
            out += encode_varint((fn << 3) | 2)
            out += encode_varint(len(payload))
            out += payload
        else:
            raise WireError("unknown node kind %r" % (kind,))
    return bytes(out)


def iter_leaves(nodes, path=()):
    """Yield (path, node) for every 'b' leaf, recursing into sub-messages.

    `path` is a tuple of (field_no, index_among_siblings_with_same_field)
    style is avoided; instead we yield numeric field-number paths so callers can
    reason about structural location. Index disambiguation is provided via the
    node identity (the actual list object), which callers can mutate in place.
    """
    for node in nodes:
        kind = node[0]
        fn = node[1]
        p = path + (fn,)
        if kind == "b":
            yield p, node
        elif kind == "m":
            yield from iter_leaves(node[2], p)


def find_rtf_leaves(nodes):
    """Return [(field_path, node), ...] for every RTF leaf in the tree.

    Each node is the mutable list; assign new bytes to node[2] then serialize().
    """
    hits = []
    for path, node in iter_leaves(nodes):
        if node[2].startswith(RTF_MAGIC):
            hits.append((path, node))
    return hits


def find_string_leaves(nodes, min_len=1):
    """Return [(field_path, text), ...] for leaves that decode as printable text.

    Used to surface titles / group names / arrangement labels for inspection and
    the song-detection gate without needing a schema.
    """
    out = []
    for path, node in iter_leaves(nodes):
        raw = node[2]
        if len(raw) < min_len or raw.startswith(RTF_MAGIC):
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if text and all(ch >= " " or ch in "\t\n\r" for ch in text):
            out.append((path, text))
    return out
