"""Exercise real CLI/session read operations and persist command/report evidence."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--session', type=Path)
    parser.add_argument('--serial', default='3UJ0225321000395')
    parser.add_argument('--case', action='append', help='Only run the named case(s)')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    cases = {
        'shell-success': [{'shell': {'command': "printf 'hylyre:ok\\n'"}}],
        'shell-nonzero': [{'shell': {'command': "printf 'hylyre:failure\\n'; exit 7"}}],
        'shell-special': [{'shell': {'command': "printf '%s\\n' '中文;分号；与 空格' 'quote\"single'\n"}}],
        'shell-timeout': [{'shell': {'command': "printf 'BEFORE\\n'; sleep 2; printf 'AFTER\\n'", 'timeout': .25}}],
        'has-app': [{'has_app': {'bundle': 'com.huawei.hmos.browser'}},
                    {'has_app': {'bundle': 'com.hylyre.acceptance.notinstalled'}}],
        'current-app': [{'current_app': {}}],
    }
    results = []
    environment = {**os.environ, 'PYTHONUTF8': '1'}
    for name, steps in cases.items():
        if args.case and name not in args.case:
            continue
        steps_file = args.out / (name + '.steps.json')
        report = args.out / (name + '.report.md')
        trace = args.out / (name + '.trace.json')
        steps_file.write_text(json.dumps(steps, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        argv = [sys.executable, '-m', 'hylyre', 'run', '--steps-file', str(steps_file)]
        argv += ['--session', str(args.session)] if args.session else ['--device-sn', args.serial]
        argv += ['--feature', 'common-device-' + name, '--report-out', str(report), '--trace-out', str(trace)]
        proc = subprocess.run(argv, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=50, check=False, env=environment)
        log = {'name': name, 'argv': argv, 'exit_code': proc.returncode, 'stdout': proc.stdout, 'stderr': proc.stderr}
        if report.exists() and trace.exists():
            verify_argv = [sys.executable, '-m', 'hylyre', 'report', 'verify', '--report', str(report), '--trace', str(trace)]
            verified = subprocess.run(verify_argv, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=20, check=False, env=environment)
            log['verify'] = {'argv': verify_argv, 'exit_code': verified.returncode, 'stdout': verified.stdout, 'stderr': verified.stderr}
        (args.out / (name + '.command.json')).write_text(json.dumps(log, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        results.append(log)
        print(json.dumps({'name': name, 'exit_code': proc.returncode, 'verify': log.get('verify', {}).get('exit_code'), 'stdout': proc.stdout[-1500:], 'stderr': proc.stderr[-1500:]}), flush=True)
    (args.out / 'readonly-summary.json').write_text(json.dumps(results, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
