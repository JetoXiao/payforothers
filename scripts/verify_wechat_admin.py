"""Browser-test admin add/remove/save with all API calls mocked; no live writes."""
import json
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
with sync_playwright() as pw:
    browser = pw.chromium.launch(channel='chrome', headless=True)
    ctx = browser.new_context(viewport={'width': 1440, 'height': 1000})
    ctx.add_init_script("localStorage.setItem('admin_token','qa-mocked-token');localStorage.setItem('admin_is_super','1');")
    saved = {}
    site = {'brand': {'site_name': 'GptPayNow'}, 'contact': {'wechat': []}, 'currency': 'CNY'}
    def route_api(route):
        request = route.request
        url = urlparse(request.url)
        path = url.path
        if path.endswith('/authz/me'): data = {'is_super': True, 'roles': [], 'policies': []}
        elif path.endswith('/public/config'): data = site
        elif path.endswith('/settings'):
            if request.method == 'PUT':
                body = request.post_data_json
                saved[body['key']] = body['value']
                data = body['value']
            else:
                key = parse_qs(url.query).get('key', [''])[0]
                data = saved.get(key, site if key == 'site_config' else {})
        else: data = {}
        route.fulfill(json={'status_code': 0, 'msg': 'success', 'data': data})
    ctx.route('**/api/**', route_api)
    page = ctx.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto('http://127.0.0.1:4175/settings', wait_until='networkidle')
    section = page.locator('[data-testid="wechat-settings"]')
    expect(section).to_be_visible()
    for index, account in enumerate(['think-more-9', 'support_second', 'support_third']):
        section.get_by_role('button', name='添加微信客服').click()
        section.locator('input').nth(index).fill(account)
    page.get_by_role('button', name='保存更改', exact=True).click()
    page.wait_for_timeout(500)
    assert saved['site_config']['contact']['wechat'] == ['think-more-9', 'support_second', 'support_third']
    section.get_by_role('button', name='删除客服 2', exact=True).click()
    expect(section.locator('input')).to_have_count(2)
    page.get_by_role('button', name='保存更改', exact=True).click()
    page.wait_for_timeout(500)
    assert saved['site_config']['contact']['wechat'] == ['think-more-9', 'support_third']
    section.get_by_role('button', name='删除客服 2', exact=True).click()
    section.get_by_role('button', name='删除客服 1', exact=True).click()
    page.get_by_role('button', name='保存更改', exact=True).click()
    page.wait_for_timeout(500)
    assert saved['site_config']['contact']['wechat'] == []
    section.get_by_role('button', name='添加微信客服').click()
    section.locator('input').fill('think-more-9')
    section.scroll_into_view_if_needed()
    output = ROOT / 'output/verification/wechat-support'
    output.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(output/'admin-config.png'))
    assert not errors, errors
    print('ADMIN_ADD_REMOVE_SAVE_CLEAR_OK', flush=True)
    browser.close()
