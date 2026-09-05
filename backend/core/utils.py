"""
backend/core/utils.py
=====================
Shared text normalization, decoding, and preprocessing routines.
Handles multi-layered payload de-obfuscation (Base64, Hex, URL, Unicode, Morse, Binary).
"""

import re
import base64
import urllib.parse
from typing import List

MORSE_DICT = {
    '.-': 'a', '-...': 'b', '-.-.': 'c', '-..': 'd', '.': 'e',
    '..-.': 'f', '--.': 'g', '....': 'h', '..': 'i', '.---': 'j',
    '-.-': 'k', '.-..': 'l', '--': 'm', '-.': 'n', '---': 'o',
    '.--.': 'p', '--.-': 'q', '.-.': 'r', '...': 's', '-': 't',
    '..-': 'u', '...-': 'v', '.--': 'w', '-..-': 'x', '-.--': 'y',
    '--..': 'z', '-----': '0', '.----': '1', '..---': '2', '...--': '3',
    '....-': '4', '.....': '5', '-....': '6', '--...': '7', '---..': '8',
    '----.': '9', '/': ' '
}


def preprocess(text: str) -> str:
    """Lowercase and collapse multiple whitespace characters."""
    text = text.lower()
    return re.sub(r"\s+", " ", text).strip()


def decode_morse(text: str) -> str:
    """Decode Morse code sequences (e.g. .... .- -.-. -.-)."""
    if re.search(r'(?:[.-]{1,6}\s+){2,}', text):
        words = []
        for word_seq in re.findall(r'(?:[.-]{1,6}(?:\s+|$))+', text):
            tokens = word_seq.strip().split()
            decoded = "".join(MORSE_DICT.get(tok, "") for tok in tokens)
            if len(decoded) >= 3:
                words.append(decoded)
        if words:
            return " ".join(words)
    return ""


def decode_binary_strings(text: str) -> str:
    """Decode space or array separated 8-bit binary strings."""
    bin_tokens = re.findall(r'\b[01]{8}\b', text)
    if len(bin_tokens) >= 2:
        try:
            chars = [chr(int(b, 2)) for b in bin_tokens]
            decoded = "".join(chars)
            if any(c.isalnum() for c in decoded):
                return decoded
        except Exception:
            pass
    return ""


def decode_despacing(text: str) -> str:
    """Collapse vertical or diagonal single-character ASCII formatting (e.g. WHOAMI)."""
    lines = [l.strip(' `\t') for l in text.splitlines()]
    consecutive: List[str] = []
    max_run: List[str] = []
    for l in lines:
        if len(l) == 1 and l.isalnum():
            consecutive.append(l)
        else:
            if len(consecutive) > len(max_run):
                max_run = consecutive
            consecutive = []
    if len(consecutive) > len(max_run):
        max_run = consecutive
    if len(max_run) >= 4:
        return "".join(max_run)
    return ""


def decode_obfuscated_content(text: str) -> str:
    """
    Scans for and decodes obfuscated representations (Base64, Hex, URL-encoding,
    Unicode escape sequences, Morse code, Binary sequences, and ASCII de-spacing).
    Returns original text with decoded plaintext appended without triggering false n-gram tokens.
    """
    decoded_fragments: List[str] = []

    # 1. Base64 (with validation to avoid matching natural English words)
    for match in re.finditer(r'(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{8,}={0,2}(?![A-Za-z0-9+/=])', text):
        token = match.group(0)
        if token.isalpha() and (token.islower() or token.isupper()):
            continue
        has_upper = any(c.isupper() for c in token)
        has_lower = any(c.islower() for c in token)
        has_digit = any(c.isdigit() for c in token)
        has_sym = any(c in '+/=' for c in token)
        if not ((has_upper and has_lower) or (has_digit and (has_upper or has_lower)) or has_sym):
            continue
        try:
            raw = base64.b64decode(token).decode('utf-8', errors='ignore')
            if len(raw) >= 3 and all(c.isprintable() or c in '\r\n\t' for c in raw):
                alpha_count = sum(1 for c in raw if c.isalnum() or c in ' _-./')
                if alpha_count / len(raw) >= 0.7:
                    decoded_fragments.append(raw)
        except Exception:
            pass

    # 2. Hex sequences (e.g., 726d202d7266202f or '636174202f6574632f736861646f77')
    for match in re.finditer(r'[\'"]?(?:0x)?([0-9a-fA-F]{8,})[\'"]?', text):
        token = match.group(1)
        if not token.isalpha() and len(token) % 2 == 0:
            try:
                raw = bytes.fromhex(token).decode('utf-8', errors='ignore')
                if len(raw) >= 3 and all(c.isprintable() or c in '\r\n\t' for c in raw):
                    alpha_count = sum(1 for c in raw if c.isalnum() or c in ' _-./')
                    if alpha_count / len(raw) >= 0.7:
                        decoded_fragments.append(raw)
            except Exception:
                pass

    # 3. Unicode escape sequences (e.g., \u0072\u006d \u002d\u0072\u0066 \u002f)
    if r'\u00' in text or r'\x' in text:
        try:
            unescaped = text.encode('utf-8').decode('unicode_escape')
            if unescaped != text:
                decoded_fragments.append(unescaped)
        except Exception:
            pass

    # 4. URL percent-encoding (e.g., %20, %2f)
    if '%' in text:
        try:
            unquoted = urllib.parse.unquote(text)
            if unquoted != text:
                decoded_fragments.append(unquoted)
        except Exception:
            pass

    # 5. Morse Code
    morse_res = decode_morse(text)
    if morse_res:
        decoded_fragments.append(morse_res)

    # 6. Binary byte sequences
    bin_res = decode_binary_strings(text)
    if bin_res:
        decoded_fragments.append(bin_res)

    # 7. ASCII art / diagonal single-letter spacing
    despaced = decode_despacing(text)
    if despaced:
        decoded_fragments.append(despaced)

    # Deduplicate while preserving order
    seen = set()
    unique_fragments = []
    for frag in decoded_fragments:
        cleaned = frag.strip()
        if cleaned and cleaned not in seen and cleaned != text.strip():
            seen.add(cleaned)
            unique_fragments.append(cleaned)

    if not unique_fragments:
        return text

    return f"{text} decoded payload {' '.join(unique_fragments)}"
