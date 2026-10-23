import hashlib
import re
from typing import Dict, Any, Tuple


def calculate_sha256(content: bytes) -> str:
    """Computes SHA-256 cryptographic hash of byte content."""
    hasher = hashlib.sha256()
    hasher.update(content)
    return hasher.hexdigest()


def detect_file_type(file_bytes: bytes, filename: str = "") -> Tuple[str, bool, str]:
    """
    Validates magic bytes to detect file format and prevent file extension spoofing.
    Returns: (detected_format, is_valid, error_message)
    Supported formats: 'pdf', 'html', 'plain_text'
    """
    if not file_bytes:
        return "empty", False, "File content is empty."

    # 1. PDF magic bytes check: %PDF-
    if file_bytes.startswith(b"%PDF-"):
        return "pdf", True, ""

    # 2. HTML magic bytes / signatures check
    header_snippet = file_bytes[:1024].lower()
    html_signatures = [
        b"<!doctype html",
        b"<html",
        b"<head",
        b"<body",
        b"<div",
        b"<?xml",
    ]
    if any(sig in header_snippet for sig in html_signatures):
        return "html", True, ""

    # 3. Check for binary / executable signatures (Disallowed malicious files)
    executable_magic_bytes = [
        b"MZ",           # Windows PE executable / DLL
        b"\x7fELF",      # Linux ELF binary
        b"\xca\xfe\xba\xbe", # Mach-O or Java class
        b"\xfe\xed\xfa", # Mach-O
        b"PK\x03\x04",   # ZIP / JAR (unless explicitly handled)
    ]
    for magic in executable_magic_bytes:
        if file_bytes.startswith(magic):
            return "binary_executable", False, "Security Alert: Detected unauthorized binary or executable file format."

    # 4. Check for shell script / dangerous script signatures
    if header_snippet.startswith(b"#!") or re.search(rb"(?i)(<\?php|eval\(|base64_decode\(|<script)", header_snippet):
        return "script", False, "Security Alert: Detected executable script or command sequence."

    # 5. Plain text check: verify bytes are valid utf-8 / ascii text
    try:
        decoded = file_bytes.decode("utf-8")
        # Check ratio of printable characters
        printable = sum(1 for c in decoded if c.isprintable() or c in "\r\n\t")
        if len(decoded) > 0 and (printable / len(decoded)) > 0.85:
            return "plain_text", True, ""
        return "binary_unknown", False, "File contains non-text binary data without valid document headers."
    except UnicodeDecodeError:
        return "binary_corrupted", False, "Unable to decode text. File is binary or corrupted."


def validate_document_safety(file_bytes: bytes, filename: str = "") -> Dict[str, Any]:
    """
    Runs pre-ingestion security gate checks on raw file bytes before any AI or parser reads it.
    """
    sha256_hash = calculate_sha256(file_bytes)
    detected_format, is_valid, error = detect_file_type(file_bytes, filename)

    # Extension mismatch check (extension spoofing)
    ext = filename.lower().split(".")[-1] if "." in filename else ""
    extension_mismatch = False

    if ext == "pdf" and detected_format != "pdf":
        extension_mismatch = True
        is_valid = False
        error = f"Extension Spoofing Detected: File claims to be .pdf but has format '{detected_format}'."
    elif ext in ("html", "htm") and detected_format != "html":
        extension_mismatch = True
        is_valid = False
        error = f"Extension Spoofing Detected: File claims to be .html but has format '{detected_format}'."

    return {
        "is_safe_format": is_valid,
        "format": detected_format,
        "sha256": sha256_hash,
        "size_bytes": len(file_bytes),
        "extension_mismatch": extension_mismatch,
        "error": error if not is_valid else None
    }
