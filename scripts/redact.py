#!/usr/bin/env python3
"""Redact secret *values* from a stream (stdin -> stdout), or a file given as arg.

Conservative patterns: PEM private keys, key=value / key:value secrets,
scheme://user:pass@host, Bearer tokens, K8s secret base64 blobs, long key-like blobs.
Values -> <<REDACTED:TYPE>>; callers preserve metadata themselves.
"""
import sys, re

if len(sys.argv) > 1:
    with open(sys.argv[1]) as f:
        data = f.read()
elif not sys.stdin.isatty():
    data = sys.stdin.read()
else:
    sys.exit(0)

# Terminal formatting is not evidence and raw control characters make YAML invalid.
data = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", data)
data = "".join(ch for ch in data if ch in "\n\t\r" or ord(ch) >= 32)

data = re.sub(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----.*?-----END (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----",
              "<<REDACTED:PRIVATE_KEY>>", data, flags=re.S)

data = re.sub(r"([a-z][a-z0-9+.\-]*://[^:@/\s~]+:)([^@/\s]+)(@)",
              r"\1<<REDACTED:SECRET>>\3", data, flags=re.I)

data = re.sub(r"(authorization:\s*bearer\s+)[A-Za-z0-9._\-]+",
              r"\1<<REDACTED:BEARER>>", data, flags=re.I)

# Secret words that must stand alone (not a prefix of a normal word).
# "auth" is intentionally NOT here: matching it would redact "authorization",
# "authenticated", etc. It is still matched below only as a whole key.
_STANDALONE = r"password|passwd|pwd|secret|token|auth"
# Compound secret tokens: may appear embedded in a longer identifier
# (e.g. GOOGLE_MAPS_API_KEY, client_secret, S3_ACCESS_KEY_ID).
_COMPOUND = r"api[_-]?key|access[_-]?key|access[_-]?token|client[_-]?secret|private[_-]?key"

# A secret key is an identifier token that (a) contains a compound secret token,
# or (b) contains a standalone secret word delimited from adjacent letters/digits.
# This catches both `password=...` and `SMTP_PASSWORD=...` / `DB_PASSWORD=...`.
_kv = re.compile(
    r'(?<![A-Za-z0-9])'
    r'(?P<key>[A-Za-z0-9_.\-]*?'
    r'(?:(?:' + _STANDALONE + r')(?![A-Za-z0-9])'
    r'|(?:' + _COMPOUND + r')(?![A-Za-z0-9]))'
    r'[A-Za-z0-9_.\-]*?)'
    r'(?P<eq>\s*[=:]\s*)'
    r'(?P<val>"[^"]*"|\'[^\']*\'|[^\s,"\'`]+)',
    re.I)
def _kv_repl(m):
    key = m.group("key")
    eq = m.group("eq")
    val = m.group("val")
    if val[:1] == '"' and val[-1:] == '"':
        return key + eq + '"<<REDACTED:SECRET>>"'
    if val[:1] == "'" and val[-1:] == "'":
        return key + eq + "'<<REDACTED:SECRET>>'"
    return key + eq + "<<REDACTED:SECRET>>"
data = _kv.sub(_kv_repl, data)

_md = {"apiVersion","kind","metadata","name","namespace","creationTimestamp","type",
       "labels","annotations","uid","resourceVersion","status","clusterName","generation"}
_b64 = re.compile(r"^(\s*)([a-z0-9_.\-]+)(\s*:\s*)([A-Za-z0-9+/]{20,}={0,2})\s*$", re.I)
def _b64_line(l):
    m = _b64.match(l)
    if not m or m.group(2) in _md: return l
    return m.group(1) + m.group(2) + m.group(3) + "<<REDACTED:BASE64_BLOB>>"
data = "\n".join(_b64_line(l) for l in data.split("\n"))

data = "\n".join(
    "<<REDACTED:BLOB>>" if (
        re.fullmatch(r"\s*[A-Za-z0-9+/]{60,}={0,2}\s*", l) or
        re.fullmatch(r"\s*[0-9a-fA-F]{60,}\s*", l)
    ) else l
    for l in data.split("\n"))

sys.stdout.write(data)
