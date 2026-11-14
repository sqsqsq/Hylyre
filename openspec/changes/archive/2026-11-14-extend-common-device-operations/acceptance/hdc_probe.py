"""Read-only HDC channel probes; writes raw host bytes and environment facts."""

from __future__ import annotations

import argparse
import base64
import importlib.metadata
import json
import shutil
import subprocess
import time
import uuid
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    executable = shutil.which('hdc')
    assert executable, 'hdc is required'
    marker = '__HYLYRE_PROBE_' + uuid.uuid4().hex
    probes = [
        ('hdc-version', ['version'], 10),
        ('system', ['shell', 'param get const.ohos.fullname'], 10),
        ('api', ['shell', 'param get const.ohos.apiversion'], 10),
        ('channels', ['shell', "printf 'OUT\\n'; printf 'ERR\\n' >&2"], 10),
        ('remote-7', ['shell', 'exit 7'], 10),
        ('wrapped-7', ['shell', f"( exit 7 ); rc=$?; printf '\\n{marker}=%s\\n' \"$rc\""], 10),
        ('timeout', ['shell', "printf 'BEFORE\\n'; sleep 2; printf 'AFTER\\n'"], .25),
    ]
    results = []
    for name, tail, timeout in probes:
        argv = [executable, '-t', args.serial, *tail]
        started = time.monotonic()
        try:
            proc = subprocess.run(argv, capture_output=True, timeout=timeout, check=False)
            stdout, stderr, code, timed_out = proc.stdout, proc.stderr, proc.returncode, False
        except subprocess.TimeoutExpired as exc:
            stdout, stderr, code, timed_out = exc.stdout or b'', exc.stderr or b'', None, True
        record = dict(name=name, argv=argv, timeout=timeout, elapsed=time.monotonic()-started,
                      stdout=stdout.decode('utf-8', 'replace'), stderr=stderr.decode('utf-8', 'replace'),
                      stdout_b64=base64.b64encode(stdout).decode(), stderr_b64=base64.b64encode(stderr).decode(),
                      transport_exit_code=code, timed_out=timed_out)
        results.append(record)
        print(json.dumps({k: record[k] for k in ('name', 'stdout', 'stderr', 'transport_exit_code', 'timed_out')}), flush=True)
    output = dict(serial=args.serial, hypium=importlib.metadata.version('hypium'), marker=marker, probes=results)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
