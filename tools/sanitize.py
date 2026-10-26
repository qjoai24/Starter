#!/usr/bin/env python3
"""Usage:
  python3 tools/sanitize.py text "some text"        -> prints cleaned text
  python3 tools/sanitize.py textfile in.txt          -> prints cleaned text
  python3 tools/sanitize.py docx in.docx out.docx    -> cleans text + strips metadata
  python3 tools/sanitize.py selftest
Exit code 1 if any non-ASCII character survives cleaning."""
import re, sys, unicodedata

MAP = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"',
    "–": "-", "—": ", ", "―": "-", "−": "-",
    "…": "...", " ": " ", "•": "-", "●": "-",
    "▪": "-", "·": "-", "‣": "-", "⁃": "-",
    "®": "", "™": "", "©": "", "℠": "",
}
ZERO_WIDTH = re.compile("[​-‏‪-‮⁠-⁤⁦-⁯﻿­]")
MARKDOWN = re.compile(r"(\*\*|__|`|^\s*#{1,6}\s)", re.M)

def clean(text):
    text = ZERO_WIDTH.sub("", text)
    for k, v in MAP.items():
        text = text.replace(k, v)
    text = unicodedata.normalize("NFKC", text)
    text = MARKDOWN.sub("", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\s+,", ",", text)
    text = re.sub(r",\s*,", ",", text)
    bad = sorted({c for c in text if not (32 <= ord(c) < 127 or c in "\n\t")})
    return text, bad

def clean_docx(src, dst):
    from docx import Document
    doc = Document(src)
    flagged = set()
    def runs(container):
        for p in container.paragraphs:
            for r in p.runs:
                yield r
        for t in getattr(container, "tables", []):
            for row in t.rows:
                for cell in row.cells:
                    yield from runs(cell)
    targets = [doc]
    for s in doc.sections:
        targets += [s.header, s.footer, s.first_page_header, s.first_page_footer]
    for c in targets:
        for r in runs(c):
            new, bad = clean(r.text)
            r.text = new
            flagged.update(bad)
    cp = doc.core_properties
    for field in ("author", "last_modified_by", "title", "subject",
                  "comments", "keywords", "category", "identifier"):
        try:
            setattr(cp, field, "")
        except Exception:
            pass
    cp.author = "Quentin Owens"
    cp.last_modified_by = "Quentin Owens"
    doc.save(dst)
    return sorted(flagged)

def report(bad):
    if bad:
        print("FLAGGED:", " ".join("U+%04X" % ord(c) for c in bad), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "selftest"
    if mode == "text":
        out, bad = clean(sys.argv[2]); print(out); report(bad)
    elif mode == "textfile":
        out, bad = clean(open(sys.argv[2], encoding="utf-8").read()); print(out); report(bad)
    elif mode == "docx":
        report(clean_docx(sys.argv[2], sys.argv[3])); print("CLEAN:", sys.argv[3])
    else:
        sample = "“Xactimate®” — 6 yrs… • roof​ inspections"
        out, bad = clean(sample)
        assert not bad, bad
        print("SELFTEST PASS:", out)
