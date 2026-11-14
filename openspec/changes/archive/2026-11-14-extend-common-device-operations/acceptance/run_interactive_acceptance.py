"""Wait for the manually opened fixture, then run the frozen interactive matrix.

Only Hylyre CLI steps touch the device. Browser state is an independent oracle;
it never supplies device actions. A missing page/native node stays incomplete.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from hylyre.api.selector_resolve import resolve_one, resolve_targets
from hylyre.scenario.plan_contract import validate_planned_step
from hylyre.ui_dump_hints import parse_bounds_rect


BASE = 'http://127.0.0.1:18765'


def events() -> list[dict]:
    with urlopen(BASE + '/state', timeout=3) as response:
        return json.load(response)


def device_event(event: dict) -> bool:
    ua = event.get('userAgent', '')
    return bool(event.get('clientId') and re.search(r'Harmony|Android|Mobile|Phone', ua, re.I)
                and not re.search(r'Windows NT|Macintosh|X11', ua, re.I))


def latest_layout(view: str | None = None) -> dict | None:
    return next((e for e in reversed(events()) if e.get('type') in {'page-ready', 'page-state'}
                 and device_event(e)
                 and e.get('fixtureVersion') == 2 and e.get('visible') is True
                 and time.time() - e.get('receivedAt', 0) < 8
                 and (view is None or e.get('view') == view)), None)


def attrs(tree: dict) -> list[dict]:
    result, pending = [], [tree]
    for node in pending:
        result.append(node.get('attributes', {}))
        pending.extend(node.get('children', []))
    return result


def calibrate(tree: dict, layout: dict) -> tuple[float, float, float]:
    """Calibrate from actual reset-button center, check a second visible anchor."""
    screen = parse_bounds_rect(tree['attributes']['bounds'])
    if screen is None:
        raise ValueError('UI dump has no screen bounds')
    scale = (screen[2] - screen[0]) / layout['viewport']['width']
    reset = resolve_one(tree, {'by_text': 'Reset fixture', 'match': 'exact'})
    r = layout['rects']['reset']
    ox = reset.center[0] - scale * (r['x'] + r['width'] / 2)
    oy = reset.center[1] - scale * (r['y'] + r['height'] / 2)
    anchor = resolve_one(tree, {'by_text': 'Gestures', 'match': 'exact'})
    r = layout['rects']['gestures']
    projected = (ox + scale * (r['x'] + r['width'] / 2), oy + scale * (r['y'] + r['height'] / 2))
    if math.dist(projected, anchor.center) > 24:
        raise ValueError('DOM/native anchor calibration disagrees; no coordinate action injected')
    return scale, ox, oy


def native_selector(tree: dict, layout: dict, geometry: tuple, name: str) -> dict:
    """Use a real dump node matching the visible DOM rectangle, never a point."""
    scale, ox, oy = geometry
    r = layout['rects'][name]
    expected = (ox + scale*r['x'], oy + scale*r['y'],
                ox + scale*(r['x']+r['width']), oy + scale*(r['y']+r['height']))
    candidates = []
    for a in attrs(tree):
        bounds = parse_bounds_rect(a.get('bounds', ''))
        if a.get('type') and bounds and max(abs(x-y) for x, y in zip(bounds, expected)) <= 24:
            candidates.append(a)
    if not candidates:
        raise ValueError(f'{name}: no native component corresponds to fixture bounds {expected}')
    # Nested text and control bounds can coincide. Prefer the observable control.
    candidates.sort(key=lambda a: (not any(t in a['type'].lower() for t in ('button', 'input', 'checkbox', 'scroll', 'textarea')), a['type']))
    a = candidates[0]
    for key, field in (('by_id', 'id'), ('by_key', 'key')):
        if a.get(field):
            selector = {key: a[field]}
            hits = resolve_targets(tree, selector)
            if len(hits) == 1 and hits[0].tap_bounds == a['bounds']:
                return selector
    hits = resolve_targets(tree, {'by_type': a['type']})
    if len(hits) == 1 and hits[0].tap_bounds == a['bounds']:
        return {'by_type': a['type']}
    indices = [i for i, h in enumerate(hits) if h.tap_bounds == a['bounds']]
    if len(indices) != 1:
        raise ValueError(f'{name}: native bounds are not unique')
    return {'by_type': a['type'], 'index': indices[0]}


def planned_cases(layout: dict, geometry: tuple, selectors: dict) -> dict[str, tuple[str, list[dict]]]:
    scale, ox, oy = geometry
    r = layout['rects']['pad']
    def p(x: float, y: float) -> dict:
        return {'x': round(ox + scale*(r['x']+r['width']*x)), 'y': round(oy + scale*(r['y']+r['height']*y))}
    def center(name: str) -> dict:
        b = layout['rects'][name]
        return {'x': round(ox+scale*(b['x']+b['width']/2)), 'y': round(oy+scale*(b['y']+b['height']/2))}
    area, field, check = selectors.get('pad'), selectors.get('entry'), selectors.get('fixture-check')
    cases = {
        'touch-double': ('gestures', [{'touch': {**p(.75, .3), 'mode': 'double'}}]),
        'touch-long-3s': ('gestures', [{'touch': {**p(.75, .3), 'mode': 'long', 'press_time': 3}}]),
        'drag': ('gestures', [{'drag': {'start': center('box'), 'end': p(.72, .7), 'press_time': 2, 'drag_time': .7}}]),
        'slide': ('gestures', [{'slide': {'start': p(.2, .3), 'end': p(.8, .7), 'duration': .6}}]),
        'pinch-in': ('gestures', [{'pinch_in': {'area': area, 'scale': .5, 'direction': 'horizontal'}}]),
        'pinch-out': ('gestures', [{'pinch_out': {'area': area, 'scale': 1.5, 'direction': 'horizontal'}}]),
        'two-finger-swipe': ('gestures', [{'two_finger_swipe': {'start1': p(.3, .3), 'end1': p(.3, .7), 'start2': p(.7, .3), 'end2': p(.7, .7), 'duration': .7, 'area': area}}]),
        'multi-finger-touch': ('gestures', [{'multi_finger_touch': {'points': [p(.3, .4), p(.7, .4)], 'duration': .4, 'area': area}}]),
        'gesture-single': ('gestures', [{'gesture': {'fingers': [{'points': [p(.2, .3), p(.5, .7), p(.8, .3)]}], 'speed': 800}}]),
        'gesture-multi': ('gestures', [{'gesture': {'fingers': [{'points': [p(.2, .3), p(.3, .7), p(.4, .3)]}, {'points': [p(.6, .3), p(.7, .7), p(.8, .3)]}], 'speed': 800}}]),
        'fling': ('scroll', [{'fling': {'area': selectors.get('scroll'), 'direction': 'UP', 'distance': 60, 'speed': 'fast'}}]),
        'get-property': ('edit', [{'get_component_property': {'target': check, 'property': 'checked'}}]),
        'clear-text': ('edit', [{'touch': center('entry')}, {'clear_text': {'target': field}}]),
        'move-cursor': ('edit', [{'touch': center('entry')}, {'move_cursor': {'direction': 'begin'}}, {'move_cursor': {'direction': 'right', 'times': 2}}, {'input': {'text': 'X'}}]),
        'press-key': ('edit', [{'touch': center('multiline')}, {'move_cursor': {'direction': 'end'}}, {'press_key': {'key': 'ENTER'}}]),
        'combination': ('edit', [{'touch': center('entry')}, {'press_combination_key': {'keys': ['CTRL_LEFT', 'A']}}]),
        'wait-for': ('edit', [{'wait_for': {**(check or {}), 'checked': False, 'timeout': 2}}]),
        'wait-gone': ('edit', [{'touch': center('fixture-check')}, {'wait_gone': {**(check or {}), 'checked': False, 'timeout': 2}}, {'wait_for': {**(check or {}), 'checked': True, 'timeout': 2}}]),
        'set-checked': ('edit', [{'set_checked': {'target': check, 'checked': True}}, {'set_checked': {'target': check, 'checked': True}}]),
        'not-checkable': ('edit', [{'set_checked': {'target': selectors.get('plain'), 'checked': True}}]),
        'current-app': ('gestures', [{'current_app': {}}]),
        'recent-tasks': ('gestures', [{'recent_tasks': {}}]),
    }
    return cases


def observe(name: str, observed: list[dict], outcome_steps: list[dict]) -> bool | None:
    ends = [e for e in observed if e.get('type') == 'gesture-end']
    state = next((e for e in reversed(observed) if e.get('type') == 'page-state'), {})
    values = state.get('values', {})
    facts = [(s.get('outcome', {}).get('observation') or {}).get('facts', {}) for s in outcome_steps]
    if name == 'touch-double': return any(e.get('type') == 'double-tap' for e in observed)
    if name == 'touch-long-3s': return any(e.get('type') == 'long-menu' and 2800 <= e['durationMs'] <= 4500 for e in observed)
    if name == 'drag': return bool(ends and ends[-1]['maximumContacts'] == 1 and ends[-1]['box'] != {'x': 30, 'y': 80})
    if name == 'slide': return bool(ends and len(ends[-1]['contacts'][0]['path']) > 2 and ends[-1]['maximumContacts'] == 1)
    if name.startswith('pinch-'):
        ratio = ends[-1].get('pinchRatio') if ends else None
        return bool(ratio and ends[-1]['maximumContacts'] == 2 and (ratio < .9 if name == 'pinch-in' else ratio > 1.1))
    if name in {'two-finger-swipe', 'multi-finger-touch', 'gesture-multi'}:
        if not ends or ends[-1]['maximumContacts'] != 2 or len(ends[-1]['contacts']) != 2: return False
        if name == 'multi-finger-touch':
            return 300 <= ends[-1]['durationMs'] <= 1000 and all(math.dist((c['start']['x'],c['start']['y']),(p['x'],p['y'])) < 12 for c in ends[-1]['contacts'] for p in c['path'])
        return all(len(c['path']) > 2 for c in ends[-1]['contacts'])
    if name == 'gesture-single': return bool(ends and ends[-1]['maximumContacts'] == 1 and len(ends[-1]['contacts'][0]['path']) > 3)
    if name == 'fling': return any(e.get('type') == 'scroll-sample' and e.get('afterReleaseMs') == 600 and e['scrollTop'] > e['atRelease'] + 5 for e in observed)
    if name == 'get-property': return bool(facts and facts[0].get('value') is False and values.get('checked') is False)
    if name == 'clear-text': return values.get('entry') == ''
    if name == 'move-cursor': return values.get('entry') == 'ABXCD'
    if name == 'press-key': return values.get('multiline') == 'first line\nsecond line\n' and any(e.get('type') == 'key' and e.get('key') == 'Enter' for e in observed)
    if name == 'combination': return values.get('entry') == 'ABCD' and values.get('selectionStart') == 0 and values.get('selectionEnd') == 4
    if name == 'wait-for': return values.get('checked') is False
    if name == 'wait-gone': return values.get('checked') is True
    if name == 'set-checked': return [f.get('changed') for f in facts] == [True, False] and values.get('checked') is True and values.get('changes') == 1
    if name == 'not-checkable': return not any(e.get('type') == 'plain-click' for e in observed)
    if name == 'current-app': return facts[0].get('bundle') == 'com.huawei.hmos.browser'
    return None  # Recent tasks needs actual after-action dump/screenshot review.


def requested_paths(steps: list[dict]) -> list | None:
    root, block = next(iter(steps[0].items()))
    if root in {'drag', 'slide'}: return [[block['start'], block['end']]]
    if root == 'two_finger_swipe': return [[block['start1'], block['end1']], [block['start2'], block['end2']]]
    if root == 'multi_finger_touch': return [[p, p] for p in block['points']]
    if root == 'gesture': return [f['points'] for f in block['fingers']]
    return None


def paths_match(steps: list[dict], observed: list[dict], geometry: tuple) -> bool:
    paths = requested_paths(steps)
    if paths is None: return True
    end = next((e for e in reversed(observed) if e.get('type') == 'gesture-end'), None)
    if not end or len(end['contacts']) != len(paths): return False
    scale, ox, oy = geometry
    expected = [[((p['x']-ox)/scale, (p['y']-oy)/scale) for p in path] for path in paths]
    for contacts in itertools.permutations(end['contacts']):
        matches = True
        for contact, points in zip(contacts, expected):
            actual = [(p['x'], p['y']) for p in contact['path']]
            matches &= math.dist(actual[0], points[0]) <= 12 and math.dist(actual[-1], points[-1]) <= 12
            matches &= all(min(math.dist(p, a) for a in actual) <= 18 for p in points[1:-1])
        if matches: return True
    return False


def releases_match(steps: list[dict], observed: list[dict], geometry: tuple) -> bool:
    paths = requested_paths(steps)
    if paths is None: return True
    scale, ox, oy = geometry
    pointer_ends = [e for e in observed if e.get('type') == 'pointer-end']
    end = next((e for e in reversed(observed) if e.get('type') == 'gesture-end'), None)
    if not end: return False
    for path in paths:
        first, last = path[0], path[-1]
        start = ((first['x']-ox)/scale, (first['y']-oy)/scale)
        expected = ((last['x']-ox)/scale, (last['y']-oy)/scale)
        candidates = [c for c in end['contacts']+pointer_ends if math.dist((c['start']['x'],c['start']['y']),start)<=12]
        if not any('release' in c and math.dist((c['release']['x'],c['release']['y']),expected)<=12 for c in candidates):
            return False
    return True


class Run:
    def __init__(self, out: Path, session: Path):
        self.out, self.session = out, session
        self.out.mkdir(parents=True, exist_ok=True)

    def command(self, name: str, args: list[str]) -> subprocess.CompletedProcess:
        argv = [sys.executable, '-m', 'hylyre', *args]
        result = subprocess.run(argv, capture_output=True, encoding='utf-8', errors='replace',
                                timeout=45, env={**os.environ, 'PYTHONUTF8': '1'}, check=False)
        (self.out / (name + '.command.json')).write_text(json.dumps(dict(argv=argv, exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr), ensure_ascii=False, indent=2), encoding='utf-8')
        return result

    def dump(self, name: str) -> dict:
        path = self.out / (name + '.ui.json')
        result = self.command(name + '-dump', ['dump-ui', '--session', str(self.session), '--out', str(path), '--full'])
        if result.returncode: raise RuntimeError('dump-ui failed; see command log')
        return json.loads(path.read_text(encoding='utf-8'))['tree']

    def steps(self, name: str, steps: list[dict], report: bool = True) -> list[dict]:
        for step in steps: validate_planned_step(step, path=name)
        path = self.out / (name + '.steps.json')
        path.write_text(json.dumps(steps, ensure_ascii=False, indent=2), encoding='utf-8')
        args = ['run', '--steps-file', str(path), '--session', str(self.session)]
        if report:
            args += ['--feature', 'interactive-' + name, '--report-out', str(self.out / (name + '.report.md')), '--trace-out', str(self.out / (name + '.trace.json'))]
        else: args += ['--out', str(self.out / (name + '.result.json'))]
        result = self.command(name, args)
        if not report:
            if result.returncode: raise RuntimeError(f'{name}: fixture setup failed')
            return []
        trace = self.out / (name + '.trace.json')
        if not trace.exists(): raise RuntimeError(f'{name}: no trace produced')
        return [s for c in json.loads(trace.read_text(encoding='utf-8'))['cases'] for s in c['steps']]

    def wait(self, view: str | None, seconds: float) -> dict | None:
        deadline = time.monotonic() + seconds
        while time.monotonic() <= deadline:
            layout = latest_layout(view)
            if layout:
                tree = self.dump('ready-' + str(view))
                try: calibrate(tree, layout)
                except Exception: pass
                else: return layout
            time.sleep(1)
        return None

    def context(self, view: str, name: str) -> tuple[dict, dict, tuple]:
        layout = latest_layout()
        if not layout: raise RuntimeError('fixture heartbeat missing')
        current = self.dump(name+'-setup')
        if any(a.get('bundleName') == 'com.huawei.hmos.inputmethod' for a in attrs(current)):
            self.steps(name+'-dismiss-keyboard', [{'back': {}}], False)
            time.sleep(.4)
        if layout['view'] != view:
            self.steps(name+'-navigate', [{'touch': {'by_text': view.capitalize(), 'match': 'exact'}}], False)
            layout = self.wait(view, 12)
            if not layout: raise RuntimeError(f'{view}: fixture navigation did not become ready')
        self.steps(name+'-reset', [{'touch': {'by_text': 'Reset fixture', 'match': 'exact'}}], False)
        time.sleep(.5)
        layout = latest_layout(view)
        tree = self.dump(name+'-before')
        return layout, tree, calibrate(tree, layout)


def self_check() -> None:
    layout = {'viewport': {'width': 400}, 'rects': {name: {'x': 20, 'y': 50, 'width': 100, 'height': 40} for name in ('pad','box','entry','multiline','fixture-check','plain')}}
    selectors = {name: {'by_id': name} for name in ('pad','scroll','entry','fixture-check','plain')}
    for _, steps in planned_cases(layout, (3, 0, 100), selectors).values():
        for step in steps: validate_planned_step(step, path='offline')
    assert observe('clear-text', [{'type': 'page-state', 'values': {'entry': ''}}], []) is True
    assert observe('touch-double', [], []) is False
    sample = [{'type':'gesture-end','contacts':[{'path':[{'x':10,'y':20},{'x':30,'y':40}]}]}]
    step = [{'slide': {'start': {'x':30,'y':160},'end': {'x':90,'y':220}}}]
    assert paths_match(step, sample, (3,0,100))
    assert not paths_match(step, sample, (3,0,200))
    assert not device_event({'clientId':'desktop','userAgent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    assert device_event({'clientId':'phone','userAgent':'Mozilla/5.0 (Phone; HarmonyOS 6.0)'})
    print('Offline case validation and oracle self-check passed; no device actions', flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('.hylyre/verification/extend-common-device-operations/interactive'))
    parser.add_argument('--session', type=Path, default=Path('.hylyre/verification/extend-common-device-operations/session.json'))
    parser.add_argument('--wait', type=float, default=0, help='Seconds to wait for live fixture heartbeat')
    parser.add_argument('--only', action='append', help='Run only named cases')
    parser.add_argument('--skip', action='append', default=[], help='Skip an independently verified case')
    parser.add_argument('--fullscreen-multitouch', action='store_true', help='Use the verified Fullscreen API context for multi-finger cases')
    parser.add_argument('--self-check', action='store_true')
    args = parser.parse_args()
    if args.self_check:
        self_check()
        return
    run = Run(args.out, args.session)
    layout = run.wait(None, max(.1, args.wait))
    if not layout:
        (args.out/'readiness.json').write_text(json.dumps({'status': 'pending', 'reason': 'fresh visible fixture page and matching native anchors not observed'}), encoding='utf-8')
        print('Pending: unlock device and open '+BASE+'/', flush=True)
        return
    results = []
    entered_fullscreen = False
    cases = planned_cases({'rects': {n: {'x': 0, 'y': 0, 'width': 1, 'height': 1} for n in ('pad','box','entry','multiline','fixture-check')}}, (1,0,0), {})
    for name, (view, _) in cases.items():
        if name in args.skip or (args.only and name not in args.only): continue
        try:
            layout, tree, geometry = run.context(view, name)
            if args.fullscreen_multitouch and name in {'two-finger-swipe','multi-finger-touch','gesture-multi'} and not layout.get('fullscreen'):
                run.steps(name+'-enter-fullscreen', [{'touch': {'by_text':'Toggle fullscreen','match':'exact'}}], False)
                time.sleep(1.5)
                layout = latest_layout(view)
                if not layout or not layout.get('fullscreen'): raise RuntimeError('fixture Fullscreen API did not enter supported context')
                entered_fullscreen = True
                tree = run.dump(name+'-fullscreen-before')
                geometry = calibrate(tree, layout)
            needed = ['pad'] if name in {'pinch-in','pinch-out','two-finger-swipe','multi-finger-touch'} else ['scroll'] if name == 'fling' else ['entry'] if name == 'clear-text' else ['fixture-check'] if name in {'get-property','wait-for','wait-gone','set-checked'} else ['plain'] if name == 'not-checkable' else []
            selectors = {n: native_selector(tree, layout, geometry, n) for n in needed}
            steps = planned_cases(layout, geometry, selectors)[name][1]
            start = len(events())
            outcomes = run.steps(name, steps)
            time.sleep(3.3)
            observed = [e for e in events()[start:] if e.get('clientId') == layout['clientId'] and device_event(e)]
            (args.out/(name+'.events.json')).write_text(json.dumps(observed, ensure_ascii=False, indent=2), encoding='utf-8')
            verified = run.command(name+'-verify', ['report','verify','--report',str(args.out/(name+'.report.md')),'--trace',str(args.out/(name+'.trace.json'))]).returncode == 0
            oracle = observe(name, observed, outcomes)
            path_check = paths_match(steps, observed, geometry)
            end_check = releases_match(steps, observed, geometry)
            if oracle is not None: oracle = oracle and path_check
            statuses = [s['outcome']['status'] for s in outcomes]
            expected = statuses == ['failed'] if name == 'not-checkable' else all(s == 'passed' for s in statuses)
            status = 'passed' if expected and oracle is True and verified and end_check else 'partial_end_unverified' if expected and oracle is True and verified else 'blocked' if 'blocked' in statuses else 'needs_visual_review' if oracle is None else 'failed'
            if name == 'recent-tasks':
                run.dump(name+'-after')
                run.command(name+'-screenshot', ['screenshot','--session',str(args.session),'--out',str(args.out/(name+'.png'))])
                run.steps(name+'-return', [{'back': {}}], False)
            row = dict(name=name,status=status,operation_statuses=statuses,oracle=oracle,path_check=path_check,end_coordinate_verified=end_check,report_verified=verified)
        except Exception as exc:
            row = dict(name=name,status='incomplete',reason=str(exc))
        results.append(row)
        (args.out/'summary.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(row),flush=True)
    layout = latest_layout()
    if entered_fullscreen and layout and layout.get('fullscreen'):
        run.steps('exit-owned-fullscreen', [{'touch': {'by_text':'Toggle fullscreen','match':'exact'}}], False)


if __name__ == '__main__':
    main()
