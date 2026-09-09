"""Real shipped Arrow/Vue components with a source-derived, simulated status API.
Run: python tests/controller_action_picker_browser.py --output /absolute/evidence
Requires Playwright Chromium. No device or live API is contacted.
"""
import argparse
import ast
import functools
import json
import os
from pathlib import Path
import subprocess
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Iterable, Mapping

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[4]
GALAXY = ROOT / "starpilot/system/the_galaxy"
BASE = os.environ.get("PICKER_SOURCE_BASE", "HEAD")


def source_options():
    """Execute original pure catalogue builder, without importing vehicle modules.

    All catalogue-eligible params/capabilities enabled gives a coverage superset;
    real device availability remains exclusively defined by the unchanged API.
    """
    ns: dict[str, Any] = dict(Path=Path, Any=Any, Callable=Callable, Iterable=Iterable, Mapping=Mapping,
              functools=functools, json=json, __file__=str(ROOT / "starpilot/common/favorite_slots.py"))
    # Combined personality builds intentionally exclude parked-only authoring
    # keys from favorites. Read their exact pure constants, without native imports.
    profile_source = ROOT / "starpilot/common/longitudinal_personality_profiles.py"
    if profile_source.exists():
        constants = [node for node in ast.parse(profile_source.read_text()).body
                     if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                     and node.targets[0].id.startswith("PERSONALITY_")]
        exec(compile(ast.Module(body=constants, type_ignores=[]), str(profile_source), "exec"), ns)
    files = ["starpilot/common/favorite_slots.py", "starpilot/system/wheel_controls/wheel_controlsd.py"]
    for filename in files:
        original = subprocess.check_output(["git", "show", f"{BASE}:{filename}"], cwd=ROOT).decode()
        assert original == (ROOT / filename).read_text(), f"Backend changed: {filename}"
        tree = ast.parse(original)
        nodes = []
        for node in tree.body:
            if isinstance(node, ast.Assign) and node.lineno < next(
                item.lineno for item in tree.body if isinstance(item, ast.Assign)
                and isinstance(item.targets[0], ast.Name)
                and item.targets[0].id == ('BLOCKED_ONROAD_KEYS' if 'favorite_slots' in filename else 'LEARN_TIMEOUT_SECONDS')
            ):
                nodes.append(node)
            if isinstance(node, ast.FunctionDef) and node.name in (
                "load_settings_catalog", "get_catalog_param_map", "build_favorite_slot_options", "filter_favorite_slot_options"
            ):
                nodes.append(node)
        exec(compile(ast.Module(body=nodes, type_ignores=[]), filename, "exec"), ns)
    options = ns['build_favorite_slot_options'](lambda key: True, alpha_longitudinal_available=True)
    options = ns['filter_favorite_slot_options'](options, {"HasRivianAngleHarness": True})
    options += list(ns['CONTROLLER_ACTION_OPTIONS'])
    options.sort(key=lambda o: (o.get('section', '').casefold(), o.get('label', o['key']).casefold()))
    assert len({o['key'] for o in options}) == len(options)
    return options


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def run(output):
    output.mkdir(parents=True, exist_ok=True)
    options = source_options()
    layout = json.loads((ROOT / 'starpilot/common/assets/device_settings_layout.json').read_text())
    category_by_key = {p['key']: s['name'] for s in layout for p in s['params']}
    def category_for(option):
        return category_by_key.get(option['key'], 'Controller Actions' if option['section'] == 'Actions' else option['section'])
    available = {category_for(o) for o in options}
    categories = [s['name'] for s in layout if s['name'] in available]
    categories += list(dict.fromkeys(category_for(o) for o in options if category_for(o) not in categories))
    (output / 'original-options.json').write_text(json.dumps(options, indent=2))
    handler = functools.partial(QuietHandler, directory=str(GALAXY))
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}'
    report = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for theme in ('classic', 'dipper'):
            for width, height, zoom, dpr in [(1440, 1000, 1, 1), (1440, 1000, 1.5, 1), (390, 844, 1, 3), (390, 844, 1.25, 3), (844, 390, 1, 2)]:
                context = browser.new_context(viewport={'width': width, 'height': height}, device_scale_factor=dpr, has_touch=width < 900)
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda e: errors.append(str(e)))
                slots = [dict(key='', label='', enabled=False) for _ in range(10)]
                slots[0] = dict(key=options[0]['key'], label=options[0]['label'], enabled=True, value=47)
                state = dict(available=True, offroad=True, controller_options=options.copy(), controller_slots=slots,
                             slots=[{} for _ in range(3)], mappings=[dict(id='mapping-1', slot=3, event_name='Button A', device_name='Test controller')],
                             devices=[], speed_unit='mph', speed_minimum=5, speed_maximum=90)
                posts = []
                def api(route):
                    if route.request.method == 'POST':
                        body = route.request.post_data_json
                        posts.append((route.request.url.rsplit('/', 1)[-1], body))
                        if route.request.url.endswith('/action'):
                            opt = next((o for o in options if o['key'] == body['key']), {})
                            slots[body['slot']] = dict(key=body['key'], label=opt.get('label', ''), enabled=bool(body['key']), value=body['value'])
                    route.fulfill(json=state)
                page.route('**/api/**', api)
                page.route('**/device_settings_layout.json*', lambda r: r.fulfill(json=layout))
                if theme == 'classic':
                    css = ['/assets/components/main.css', '/assets/components/tools/wheel_controls.css']
                    script = 'import {WheelControls} from "/assets/components/tools/wheel_controls.js"; WheelControls()(document.querySelector("#app"));'
                else:
                    css = ['/assets/mobile/css/material.css']
                    script = 'import {createApp} from "/assets/vendor/vue/vue.esm-browser.js"; import {WheelControls} from "/assets/mobile/js/components/WheelControls.js"; createApp(WheelControls).mount("#app");'
                markup = '<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><script type="importmap">{"imports":{"vue":"/assets/vendor/vue/vue.esm-browser.js"}}</script>' + ''.join(f'<link rel="stylesheet" href="{p}">' for p in css) + f'<style>body{{margin:16px;zoom:{zoom};}}</style><div id="app"></div><script type="module">{script}</script>'
                page.route('**/wheel-controls', lambda r: r.fulfill(content_type='text/html', body=markup))
                page.goto(url + '/wheel-controls')
                trigger = page.locator('[data-controller-action-slot="0"]')
                expect(trigger).to_be_enabled()
                if width < 900:
                    trigger.tap()
                else:
                    trigger.click()
                dialog = page.locator('dialog')
                search = dialog.locator('input')
                expect(search).to_be_focused()
                expect(dialog.locator('[data-current]')).to_contain_text(options[0]['label'])
                actual = dialog.locator('[data-action-key]').evaluate_all('(els) => els.map(e => e.dataset.actionKey)')
                assert actual == [''] + [o['key'] for o in options], 'Original dropdown coverage/order mismatch'
                expect(dialog.locator('select option')).to_have_text(['All categories'] + categories)
                for category in categories:
                    dialog.locator('select').select_option(category)
                    keys = dialog.locator('[data-action-key]').evaluate_all('(els) => els.map(e => e.dataset.actionKey)')
                    assert keys == [''] + [o['key'] for o in options if category_for(o) == category]
                # Search all original identifiers, including resetting a prior category.
                for option in options:
                    search.fill(option['key'])
                    assert option['key'] in dialog.locator('[data-action-key]').evaluate_all('(els) => els.map(e => e.dataset.actionKey)')
                search.fill('no-match-0123456789')
                expect(dialog).to_contain_text('No matching actions')
                assert dialog.locator('[data-action-key]').count() == 1
                search.fill('')
                # Modal is contained and the result list—not page—scrolls.
                geometry = dialog.evaluate('''d => { const r=d.getBoundingClientRect(), l=d.querySelector('.controllerActionResults'); return {x:r.x,y:r.y,right:r.right,bottom:r.bottom,scroll:l.scrollHeight,client:l.clientHeight,width:innerWidth,height:innerHeight}; }''')
                assert geometry['x'] >= 0 and geometry['y'] >= 0 and geometry['right'] <= width + 1 and geometry['bottom'] <= height + 1, geometry
                assert geometry['scroll'] > geometry['client'] > 40, geometry
                assert dialog.locator('[data-action-key]').evaluate_all('''els => els.every(e => {
                  const r=e.getBoundingClientRect();
                  return [...e.children].every(c => c.getBoundingClientRect().bottom <= r.bottom + 1);
                })'''), 'Action descriptions overflow their buttons'
                name = f'{theme}-{width}x{height}-zoom{zoom}-dpr{dpr}'
                page.screenshot(path=str(output / f'{name}.png'))
                page.keyboard.press('Shift+Tab')
                expect(dialog.locator('[data-cancel]')).to_be_focused()
                page.keyboard.press('Shift+Tab')
                assert page.evaluate('document.querySelector("dialog").contains(document.activeElement)')
                page.keyboard.press('Escape')
                expect(dialog).to_have_count(0)
                expect(trigger).to_be_focused()
                assert not posts
                trigger.click()
                dialog.locator('[data-cancel]').click()
                assert not posts
                # A failed presentation catalogue read cannot remove actions;
                # the next open retries and restores canonical menu order.
                page.unroute('**/device_settings_layout.json*')
                page.route('**/device_settings_layout.json*', lambda r: r.fulfill(status=503, body='Unavailable'))
                with page.expect_response('**/device_settings_layout.json*'):
                    trigger.click()
                assert dialog.locator('[data-action-key]').evaluate_all('(els) => els.map(e => e.dataset.actionKey)') == [''] + [o['key'] for o in options]
                dialog.locator('[data-cancel]').click()
                assert not posts
                page.unroute('**/device_settings_layout.json*')
                page.route('**/device_settings_layout.json*', lambda r: r.fulfill(json=layout))
                trigger.click()
                expect(dialog.locator('select option')).to_have_text(['All categories'] + categories)
                speed = next(o for o in options if o.get('value_type') == 'speed')
                search.fill(speed['key'])
                dialog.locator('[data-action-key]').filter(has_text=speed['label']).click()
                expect(dialog).to_have_count(0)
                expect(trigger).to_contain_text(speed['label'])
                assert posts[-1] == ('action', dict(slot=0, key=speed['key'], value=47)), posts
                trigger.click()
                expect(dialog.locator('[aria-pressed="true"]')).to_contain_text(speed['label'])
                dialog.locator('[data-action-key=""]').click()
                expect(trigger).to_contain_text('Not configured')
                assert posts[-1] == ('action', dict(slot=0, key='', value=None))
                # Last action slot must remain index 9; its learned input is slot 12.
                last = page.locator('[data-controller-action-slot="9"]')
                last.click()
                ordinary = next(o for o in options if o['key'] == '__starpilot_controller_action__:selfie')
                search.fill('driver camera')
                expect(dialog.locator('[data-action-key]').filter(has_text=ordinary['label'])).to_have_count(1)
                search.fill(ordinary['key'])
                dialog.locator('[data-action-key]').filter(has_text=ordinary['label']).click()
                expect(last).to_contain_text(ordinary['label'])
                assert posts[-1] == ('action', dict(slot=9, key=ordinary['key'], value=None))
                card = last.locator('xpath=ancestor::*[contains(@class,"wheelControllerCard") or contains(@class,"gx-card")][1]')
                with page.expect_response('**/api/wheel-controls/learn'):
                    card.get_by_role('button', name='Learn Button').click()
                assert posts[-1] == ('learn', dict(slot=12))
                # A saved key absent from today's eligible catalogue stays visible;
                # opening/cancelling must not clear or reassign it.
                state['controller_options'] = [o for o in options if o['key'] != ordinary['key']]
                last.click()
                expect(dialog.locator('[data-current]')).to_contain_text('(unavailable)', timeout=4000)
                expect(dialog.locator('[data-current]')).to_contain_text(ordinary['label'])
                before_cancel = len(posts)
                page.keyboard.press('Escape')
                assert len(posts) == before_cancel and slots[9]['key'] == ordinary['key']
                state['controller_options'] = options.copy()
                trigger.click()
                # Live eligibility changes cannot commit a stale offered action.
                removed = options[-1]
                state['controller_options'] = options[:-1]
                expect(dialog.locator('[data-action-key]').filter(has_text=removed['label'])).to_have_count(0, timeout=4000)
                state['offroad'] = False
                expect(dialog.locator('[data-action-key=""]')).to_be_disabled(timeout=4000)
                before = len(posts)
                page.keyboard.press('Escape')
                expect(trigger).to_be_disabled()
                assert len(posts) == before
                assert state['mappings'][0]['slot'] == 3
                assert not errors, errors
                report.append(dict(name=name, options=len(options), categories=len(categories), geometry=geometry, posts=posts, console_errors=errors, result='PASS'))
                (output / 'report.json').write_text(json.dumps(report, indent=2))
                context.close()
        browser.close()
    server.shutdown()
    print(json.dumps({'result': 'PASS', 'cases': len(report), 'original_options': len(options), 'output': str(output)}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
