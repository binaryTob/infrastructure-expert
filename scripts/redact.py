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

# PEM private key blocks -> single marker
data = re.sub(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----.*?-----END (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----",
              "<<REDACTED:PRIVATE_KEY>>", data, flags=re.S)

# scheme://user:password@host
data = re.sub(r"([a-z][a-z0-9+.\-]*://[^:@/\s~]+:)([^@/\s]+)(@)",
              r"\1<<REDACTED:SECRET>>\3", data, flags=re.I)

# Authorization: Bearer <token>
data = re.sub(r"(authorization:\s*bearer\s+)[A-Za-z0-9._\-]+",
              r"\1<<REDACTED:BEARER>>", data, flags=re.I)

_SECRET_WORDS = r"(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|access[_-]?token|client[_-]?secret|private[_-]?key|auth)"
_kv = re.compile(
    r'((?:^|[\s,;{(\[])(?:["\']?)' + _SECRET_WORDS + r'(?:["\']?)' +
    r'(?:["\']?\s*[=:]\s*))' +
    r'("([^"]*)"|\'([^\']*)\'|([^\s,"\']+))',
    re.I)
def _kv_repl(m):
    pre = m.group(1)
    if m.group(3) is not None:   return pre + '"<<REDACTED:SECRET>>"'
    if m.group(4) is not None:   return pre + "'<<REDACTED:SECRET>>'"
    return pre + "<<REDACTED:SECRET>>"
data = _kv.sub(_kv_repl, data)

# K8s secret base64-ish values: a key: <20+ base64> line, excluding known metadata keys
_md = {"apiVersion","kind","metadata","name","namespace","creationTimestamp","type",
       "labels","annotations","uid","resourceVersion","status","clusterName","generation"}
_b64 = re.compile(r"^(\s*)([a-z0-9_.\-]+)(\s*:\s*)([A-Za-z0-9+/]{20,}={0,2})\s*$", re.I)
def _b64_line(l):
    m = _b64.match(l)
    if not m or m.group(2) in _md: return l
    return m.group(1) + m.group(2) + m.group(3) + "<<REDACTED:BASE64_BLOB>>"
data = "\n".join(_b64_line(l) for l in data.split("\n"))

# long key-like blobs (>=60 base64 or hex) on their own line
data = "\n".join(
    "<<REDACTED:BLOB>>" if (
        re.fullmatch(r"\s*[A-Za-z0-9+/]{60,}={0,2}\s*", l) or
        re.fullmatch(r"\s*[0-9a-fA-F]{60,}\s*", l)
    ) else l
    for l in data.split("\n"))

sys.stdout.write(data)