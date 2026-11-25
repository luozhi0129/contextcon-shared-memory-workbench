#!/usr/bin/env python3
"""Pure-stdlib cl100k_base token counter.

Uses the vendored BPE ranks file data/cl100k_base.tiktoken (the same table
tiktoken's cl100k_base encoding uses; 100,256 ranks). No third-party
dependency: the pre-tokenizer is tiktoken's cl100k regex translated to
stdlib `re` (\\p{L} -> [^\\W\\d_], \\p{N} -> \\d), and the merge loop is
the standard byte-level BPE by lowest rank.

Scope note: the regex translation is exact for ASCII text (all texts
measured in this project are ASCII). Unicode letters/numbers outside ASCII
are approximated (Python \\w covers most, but not all, of \\p{L}∪\\p{N}).
No special tokens are handled: none of the measured texts contain any
(<|endoftext|> etc.), so the text is counted literally.

Validation: see tests/test_cl100k.py (canonical vectors + round-trip).
"""
import base64
import os
import re

RANKS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "cl100k_base.tiktoken")

# tiktoken cl100k_base pre-tokenizer, translated to stdlib re.
#   (?i:'s|'t|'re|'ve|'m|'ll|'d)
#   |[^\r\n\p{L}\p{N}]?\p{L}+
#   |\p{N}{1,3}
#   | ?[^\s\p{L}\p{N}]+[\r\n]*
#   |\s*[\r\n]+
#   |\s+(?!\S)
#   |\s+
# with \p{L} -> [^\W\d_] and \p{N} -> \d; the negated classes
# [^\r\n\p{L}\p{N}] and [^\s\p{L}\p{N}] become (?:[^\r\n\w]|_) and
# (?:[^\s\w]|_) (a non-word char, or underscore, since \w includes _).
_CL100K_PAT = re.compile(
    r"(?i:'s|'t|'re|'ve|'m|'ll|'d)"
    r"|(?:[^\r\n\w]|_)?[^\W\d_]+"
    r"|\d{1,3}"
    r"| ?(?:[^\s\w]|_)+[\r\n]*"
    r"|\s*[\r\n]+"
    r"|\s+(?!\S)"
    r"|\s+"
)

_RANKS = None


def _ranks():
    global _RANKS
    if _RANKS is None:
        ranks = {}
        with open(RANKS_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                token_b64, rank = line.split(" ")
                ranks[base64.b64decode(token_b64)] = int(rank)
        _RANKS = ranks
    return _RANKS


def _bpe_encode(piece: bytes, ranks) -> list:
    parts = [bytes([b]) for b in piece]
    while len(parts) > 1:
        best_rank = None
        best_idx = -1
        for i in range(len(parts) - 1):
            r = ranks.get(parts[i] + parts[i + 1])
            if r is not None and (best_rank is None or r < best_rank):
                best_rank = r
                best_idx = i
        if best_idx == -1:
            break
        parts = parts[:best_idx] + [parts[best_idx] + parts[best_idx + 1]] + parts[best_idx + 2:]
    return parts


def encode(text: str) -> list:
    """Encode text to cl100k_base token byte-strings."""
    ranks = _ranks()
    tokens = []
    for m in _CL100K_PAT.finditer(text):
        tokens.extend(_bpe_encode(m.group(0).encode("utf-8"), ranks))
    return tokens


def decode(tokens) -> str:
    return b"".join(tokens).decode("utf-8")


def count(text: str) -> int:
    """Number of cl100k_base tokens in text."""
    return len(encode(text))


def words(text: str) -> int:
    return len(text.split())
