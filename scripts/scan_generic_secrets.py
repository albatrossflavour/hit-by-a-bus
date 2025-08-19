#!/usr/bin/env python3
import argparse
import base64
import csv
import io
import json
import os
import re
import sys

# ---------- Credit cards (ccextractor-style) ----------
# Accept 12-19 digits, allow spaces/dashes, reject if not Luhn-valid.
CC_SPAN = re.compile(r"\b(?:\d[ -]?){12,19}\b")

def luhn_ok(digits: str) -> bool:
    s = 0
    alt = False
    for ch in reversed(digits):
        d = ord(ch) - 48
        if d < 0 or d > 9:
            return False
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        s += d
        alt = not alt
    return s % 10 == 0

def normalize_number(s: str) -> str:
    return re.sub(r"[^\d]", "", s)

def card_brand(num: str) -> str:
    # Very light brand hinting, not authoritative.
    if re.match(r"^4\d{12}(\d{3})?(\d{3})?$", num):
        return "visa"
    if re.match(r"^(5[1-5]\d{14}|2(2[2-9]\d|[3-6]\d{2}|7[01]\d|720)\d{12})$", num):
        return "mastercard"
    if re.match(r"^3[47]\d{13}$", num):
        return "amex"
    if re.match(r"^3(0[0-5]\d{11}|[68]\d{12})$", num):
        return "diners"
    if re.match(r"^6(011|5\d{2})\d{12}$", num):
        return "discover"
    if re.match(r"^35\d{14}$", num):
        return "jcb"
    return "unknown"

# ---------- IBAN ----------
IBAN_RE = re.compile(r"\b(?=.{15,34}\b)[A-Z]{2}\d{2}[A-Z0-9]+\b")

def iban_checksum_ok(iban: str) -> bool:
    s = (iban[4:] + iban[:4]).upper()
    mapped = []
    for c in s:
        if c.isalpha():
            mapped.append(str(ord(c) - 55))  # A=10, Z=35
        else:
            mapped.append(c)
    mod = 0
    for ch in "".join(mapped):
        mod = (mod * 10 + (ord(ch) - 48)) % 97
    return mod == 1

# ---------- ABA routing ----------
def aba_ok(routing: str) -> bool:
    if not (routing.isdigit() and len(routing) == 9):
        return False
    w = (3, 7, 1)
    total = sum(int(d) * w[i % 3] for i, d in enumerate(routing))
    return total % 10 == 0

# ---------- Country-ish patterns (format + proximity) ----------
UK_SORT = re.compile(r"\b\d{2}-?\d{2}-?\d{2}\b")
UK_ACCT = re.compile(r"\b\d{8}\b")

AU_BSB = re.compile(r"\b\d{3}-?\d{3}\b")
AU_ACCT = re.compile(r"\b\d{6,10}\b")

CA_TRANSIT = re.compile(r"\b\d{5}\b")
CA_INST = re.compile(r"\b\d{3}\b")
CA_ACCT = re.compile(r"\b\d{7,12}\b")

IN_IFSC = re.compile(r"\b[A-Z]{4}0\d{6}\b")
IN_ACCT = re.compile(r"\b\d{9,18}\b")

CONTEXT = re.compile(r"(?i)\b(iban|routing|aba|bsb|sort\s*code|ifsc|account|acct|iban:|iban\s*no|iban#|iban number)\b")

NUM_NEAR = re.compile(r"\b\d[\d \-]{6,}\d\b")  # longish numeric spans for context scan

# ---------- False positive patterns ----------
# Common test/example patterns to ignore
TEST_PATTERNS = [
    re.compile(r"\b(4111\s*1111\s*1111\s*1111|4000\s*0000\s*0000\s*0002)\b"),  # Test credit cards
    re.compile(r"\b(5555\s*5555\s*5555\s*4444|5105\s*1051\s*0510\s*5100)\b"),  # Test mastercards
    re.compile(r"\b(example|test|dummy|fake|sample|placeholder)\b", re.IGNORECASE),
    re.compile(r"\b(xxxx|1234\s*1234|0000\s*0000)\b"),  # Obvious placeholders
    re.compile(r"\[(your|my|their)\s+(account|card|bank|name)\]", re.IGNORECASE),  # Markdown placeholders
    re.compile(r"\{\{\s*(person|account|bank)\.\w+\s*\}\}", re.IGNORECASE),  # Template variables
]

# Context that suggests this is instructional/example content
SAFE_CONTEXT = re.compile(r"(?i)\b(example|template|placeholder|sample|format|like|such as|e\.g\.|for instance|emergency plan|guide|documentation)\b")

def is_likely_false_positive(raw: str, context: str) -> bool:
    """Check if this finding is likely a false positive"""
    # Check against known test patterns
    for pattern in TEST_PATTERNS:
        if pattern.search(raw):
            return True

    # Check if surrounded by safe context
    if SAFE_CONTEXT.search(context):
        return True

    # Check for markdown formatting that suggests examples
    if re.search(r"`[^`]*" + re.escape(raw) + r"[^`]*`", context):  # In code blocks
        return True

    return False

# ---------- Helpers ----------
def mask_value(kind: str, raw: str) -> str:
    if kind in ("CREDIT_CARD", "ACCOUNT_LIKE", "US_ROUTING", "UK_SORT", "AU_BSB", "CA_TRANSIT", "CA_INST"):
        digits = re.sub(r"\D", "", raw)
        if len(digits) <= 4:
            return "*" * len(digits)
        return "*" * (len(digits) - 4) + digits[-4:]
    if kind in ("IBAN", "IN_IFSC"):
        if len(raw) <= 6:
            return "***"
        return raw[:4] + "…" + raw[-2:]
    return raw

def is_probably_binary(chunk: bytes) -> bool:
    # Heuristic: a NUL byte or very high ratio of non-text control chars
    if b"\x00" in chunk:
        return True
    textlike = sum((32 <= b <= 126) or b in (9, 10, 13) for b in chunk)
    return textlike / max(1, len(chunk)) < 0.80

def read_text_file(path: str, max_bytes: int) -> str | None:
    try:
        with open(path, "rb") as f:
            data = f.read(max_bytes)
            if is_probably_binary(data):
                return None
            # Try utf-8, fall back to latin-1 lossless
            try:
                return data.decode("utf-8")
            except UnicodeDecodeError:
                return data.decode("latin-1", errors="ignore")
    except Exception:
        return None

def iter_lines_with_offsets(text: str):
    # yield (line_no starting at 1, line_text, line_start_offset)
    off = 0
    for i, line in enumerate(text.splitlines(keepends=True), 1):
        yield i, line, off
        off += len(line)

def snippet(text: str, start: int, end: int, radius: int = 40) -> str:
    s = max(0, start - radius)
    e = min(len(text), end + radius)
    return text[s:e].replace("\n", " ")

# ---------- Scan routines ----------
def scan_text(path: str, text: str):
    findings = []

    # A) IBANs (validate)
    for m in IBAN_RE.finditer(text.upper()):
        val = m.group(0)
        if iban_checksum_ok(val):
            findings.append(("IBAN", val, m.start(), m.end()))

    # B) ABA routing (validate)
    for m in re.finditer(r"\b\d{9}\b", text):
        rt = m.group(0)
        if aba_ok(rt):
            findings.append(("US_ROUTING", rt, m.start(), m.end()))

    # C) Credit cards (Luhn + length + brand sanity)
    for m in CC_SPAN.finditer(text):
        raw = m.group(0)
        num = normalize_number(raw)
        if 12 <= len(num) <= 19 and luhn_ok(num):
            # mild false-positive cut: must not be inside an IBAN
            findings.append(("CREDIT_CARD", raw, m.start(), m.end()))

    # D) Country proximity rules (format + nearby pairing or context)
    # UK: sort + 8-digit account within 60 chars
    for sm in UK_SORT.finditer(text):
        s_range = (sm.start(), sm.end())
        window = text[max(0, s_range[0] - 60): s_range[1] + 60]
        am = UK_ACCT.search(window)
        if am:
            findings.append(("UK_SORT", sm.group(0), sm.start(), sm.end()))
            findings.append(("ACCOUNT_LIKE", am.group(0),
                             max(0, s_range[0]-60) + am.start(),
                             max(0, s_range[0]-60) + am.end()))
    # AU: BSB + 6-10 digit account within 60 chars
    for bm in AU_BSB.finditer(text):
        b_range = (bm.start(), bm.end())
        window = text[max(0, b_range[0]-60): b_range[1]+60]
        am = AU_ACCT.search(window)
        if am:
            findings.append(("AU_BSB", bm.group(0), bm.start(), bm.end()))
            findings.append(("ACCOUNT_LIKE",
                             am.group(0),
                             max(0, b_range[0]-60) + am.start(),
                             max(0, b_range[0]-60) + am.end()))
    # CA: transit + institution + account roughly nearby
    for tm in CA_TRANSIT.finditer(text):
        t_range = (tm.start(), tm.end())
        win = text[max(0, t_range[0]-80): t_range[1]+80]
        im = CA_INST.search(win)
        am = CA_ACCT.search(win)
        if im and am:
            findings.append(("CA_TRANSIT", tm.group(0), tm.start(), tm.end()))
            findings.append(("CA_INST",
                             im.group(0),
                             max(0, t_range[0]-80) + im.start(),
                             max(0, t_range[0]-80) + im.end()))
            findings.append(("ACCOUNT_LIKE",
                             am.group(0),
                             max(0, t_range[0]-80) + am.start(),
                             max(0, t_range[0]-80) + am.end()))
    # IN: IFSC + account within 60 chars
    for im in IN_IFSC.finditer(text.upper()):
        i_range = (im.start(), im.end())
        win = text[max(0, i_range[0]-60): i_range[1]+60]
        am = IN_ACCT.search(win)
        if am:
            findings.append(("IN_IFSC", im.group(0), im.start(), im.end()))
            findings.append(("ACCOUNT_LIKE",
                             am.group(0),
                             max(0, i_range[0]-60) + am.start(),
                             max(0, i_range[0]-60) + am.end()))

    # E) Generic context-based catch
    for m in NUM_NEAR.finditer(text):
        s, e = m.span()
        if CONTEXT.search(text[max(0, s-60): e+60]):
            findings.append(("ACCOUNT_LIKE", m.group(0), s, e))

    # Filter out false positives and deduplicate
    seen = set()
    uniq = []
    for kind, raw, s, e in findings:
        # Get context around the finding for false positive detection
        context = snippet(text, s, e, 80)

        # Skip if likely false positive
        if is_likely_false_positive(raw, context):
            continue

        k = (kind, raw, s, e)
        if k not in seen:
            uniq.append((kind, raw, s, e))
            seen.add(k)
    return uniq

def walk_files(root: str, max_bytes: int, include_exts: set[str] | None, exclude_exts: set[str] | None):
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            path = os.path.join(dirpath, fn)
            ext = os.path.splitext(fn)[1].lower()
            if include_exts and ext not in include_exts:
                continue
            if exclude_exts and ext in exclude_exts:
                continue
            yield path

def main():
    p = argparse.ArgumentParser(description="Scan directory for credit cards and bank details (IBAN/ABA/context).")
    p.add_argument("directory", help="Root directory to scan")
    p.add_argument("--json", action="store_true", help="Output JSON instead of CSV")
    p.add_argument("--max-bytes", type=int, default=5_000_000, help="Max bytes to read per file (default 5MB)")
    p.add_argument("--include-ext", action="append", help="Limit to these file extensions (repeatable), e.g. --include-ext .txt --include-ext .log")
    p.add_argument("--exclude-ext", action="append", help="Exclude these file extensions (repeatable)")
    p.add_argument("--exit-code", action="store_true", help="Exit with code 1 if secrets found, 0 if clean (for CI integration)")
    p.add_argument("--quiet", action="store_true", help="Suppress output, just set exit code")
    args = p.parse_args()

    # Default to markdown files for emergency plan project
    include_exts = set(e.lower() for e in args.include_ext) if args.include_ext else {'.md', '.txt', '.yml', '.yaml'}
    exclude_exts = set(e.lower() for e in args.exclude_ext) if args.exclude_ext else {'.git', '.pdf', '.png', '.jpg', '.jpeg'}

    root = os.path.abspath(args.directory)
    rows = []
    for path in walk_files(root, args.max_bytes, include_exts, exclude_exts):
        text = read_text_file(path, args.max_bytes)
        if text is None:
            continue
        for kind, raw, s, e in scan_text(path, text):
            # find line number
            line_no = 1
            line_start = 0
            for ln, line, off in iter_lines_with_offsets(text):
                if s < off + len(line):
                    line_no = ln
                    line_start = off
                    break
            value_masked = mask_value(kind, raw)
            rows.append({
                "file": path,
                "line": line_no,
                "start": s,
                "end": e,
                "type": kind,
                "value_masked": value_masked,
                "value_raw": raw,
                "context": snippet(text, s, e),
            })

    # Output results
    if not args.quiet:
        if args.json:
            print(json.dumps(rows, indent=2, ensure_ascii=False))
        else:
            w = csv.writer(sys.stdout)
            w.writerow(["file","line","start","end","type","value_masked","value_raw","context"])
            for r in rows:
                w.writerow([r["file"], r["line"], r["start"], r["end"], r["type"], r["value_masked"], r["value_raw"], r["context"]])

    # Exit with appropriate code for CI integration
    if args.exit_code:
        sys.exit(1 if rows else 0)
    elif rows and not args.quiet:
        print(f"\n⚠️  Found {len(rows)} potential sensitive data items", file=sys.stderr)

if __name__ == "__main__":
    main()
