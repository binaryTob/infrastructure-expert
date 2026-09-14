#!/usr/bin/env python3
"""Capture a bounded command in memory; persist only successfully redacted streams."""
import pathlib
import subprocess
import sys


def main():
    out_path, err_path, redactor, *command = sys.argv[1:]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # Redact both streams before writing either. A failed redactor must fail closed.
    streams = [
        subprocess.run(
            [redactor, "-s"], input=stream, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=True,
        ).stdout
        for stream in (result.stdout, result.stderr)
    ]
    pathlib.Path(out_path).write_bytes(streams[0])
    pathlib.Path(err_path).write_bytes(streams[1])
    print(result.returncode if result.returncode >= 0 else 128 - result.returncode)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Exceptions can contain command arguments or output: never print them.
        sys.stderr.write("Command capture/redaction failed; no raw output was persisted.\n")
        sys.exit(1)
