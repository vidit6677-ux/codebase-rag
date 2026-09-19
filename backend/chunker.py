"""
chunker.py

Splits C++ source/header files into function- and class-level chunks
using brace-matching (not a full parser, but far better than fixed-size
splitting because it respects code boundaries).
"""

import re
import os
from dataclasses import dataclass
from typing import List


@dataclass
class Chunk:
    file_path: str
    start_line: int
    end_line: int
    text: str
    kind: str  # "function", "class", "other"


def strip_comments(source: str) -> str:
    source = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), source, flags=re.DOTALL)
    source = re.sub(r"//.*", "", source)
    return source


SIGNATURE_RE = re.compile(
    r"^\s*(template\s*<[^>]*>\s*)?"
    r"(class|struct)\s+\w+"
    r"|^\s*(template\s*<[^>]*>\s*)?"
    r"[\w:<>,\*&~\s]+\([^;{]*\)\s*(const)?\s*(noexcept)?\s*\{?\s*$",
)


def find_blocks(lines: List[str]) -> List[tuple]:
    blocks = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if SIGNATURE_RE.match(line):
            brace_line = i
            search_limit = min(i + 6, n)
            found_brace = "{" in line
            while not found_brace and brace_line < search_limit - 1:
                brace_line += 1
                if "{" in lines[brace_line]:
                    found_brace = True
            if not found_brace:
                i += 1
                continue
            depth = 0
            j = brace_line
            started = False
            while j < n:
                depth += lines[j].count("{") - lines[j].count("}")
                if "{" in lines[j]:
                    started = True
                if started and depth <= 0:
                    break
                j += 1
            end_idx = min(j, n - 1)
            blocks.append((i, end_idx))
            i = end_idx + 1
        else:
            i += 1
    return blocks


def chunk_file(file_path: str, max_leftover_lines: int = 40) -> List[Chunk]:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        raw = f.read()

    cleaned = strip_comments(raw)
    lines = cleaned.split("\n")
    orig_lines = raw.split("\n")

    blocks = find_blocks(lines)

    chunks = []
    covered = [False] * len(lines)
    for start, end in blocks:
        for k in range(start, end + 1):
            if k < len(covered):
                covered[k] = True
        text = "\n".join(orig_lines[start:end + 1]).strip()
        if len(text) < 20:
            continue
        kind = "class" if re.search(r"\b(class|struct)\b", lines[start]) else "function"
        chunks.append(Chunk(file_path, start + 1, end + 1, text, kind))

    leftover_start = None
    for idx, is_covered in enumerate(covered + [True]):
        if not is_covered and leftover_start is None:
            leftover_start = idx
        elif is_covered and leftover_start is not None:
            end = idx - 1
            text = "\n".join(orig_lines[leftover_start:end + 1]).strip()
            if len(text) >= 20:
                seg_lines = text.split("\n")
                for i in range(0, len(seg_lines), max_leftover_lines):
                    seg = seg_lines[i:i + max_leftover_lines]
                    seg_text = "\n".join(seg).strip()
                    if len(seg_text) >= 20:
                        chunks.append(Chunk(
                            file_path,
                            leftover_start + i + 1,
                            leftover_start + i + len(seg),
                            seg_text,
                            "other",
                        ))
            leftover_start = None

    return chunks


def chunk_repo(root_dir: str, extensions=(".hpp", ".h", ".cpp", ".cc")) -> List[Chunk]:
    all_chunks = []
    for dirpath, _, filenames in os.walk(root_dir):
        if any(skip in dirpath for skip in ("test", "third_party", "build", ".git", "docs")):
            continue
        for fname in filenames:
            if fname.endswith(extensions):
                fpath = os.path.join(dirpath, fname)
                try:
                    all_chunks.extend(chunk_file(fpath))
                except Exception as e:
                    print(f"  [skip] {fpath}: {e}")
    return all_chunks


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "./data/nlohmann-json/include"
    chunks = chunk_repo(target)
    print(f"Total chunks: {len(chunks)}")
    for c in chunks[:5]:
        print(f"\n--- {c.file_path}:{c.start_line}-{c.end_line} [{c.kind}] ---")
        print(c.text[:200])