"""Read-only browser QA; contact variations and admin saves are intercepted locally."""
import copy
import json
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'deploy/autnine-bridge'))
from manage import connect, api, login

def main():
    base = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:4173'
    live = not base.startswith('http://127.0.0.1')
    ssh = connect()
    try:
        config = api(ssh, 'GET', '/public/config')
        products = api(ssh, 'GET', '/public/products?page_size=50')
        details = {p['slug']: api(ssh, 'GET', '/public/products/' + p['slug']) for p in products['data']}
    finally:
        ssh.close()
    output = ROOT / 'output/verification/wechat-support'
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='chrome', headless=True)
        cases = [(1440, 'zh-CN', 'light', ids) for ids in [[], ['think-more-9'], ['think-more-9', 'support_second', 'support_third']]]
        cases += [(390, 'en-US', 'dark', ['think-more-9', 'support_second']), (768, 'zh-TW', 'light', ['think-more-9'])]
        if live:
            actual = config['data'].get('contact', {}).get('wechat', [])
            cases = [(1440, 'zh-CN', 'light', actual), (390, 'zh-CN', 'dark', actual)]
        for width, locale, theme, accounts in cases:
            ctx = browser.new_context(viewport={'width': width, 'height': 960}, locale=locale, permissions=['clipboard-read', 'clipboard-write'])
            ctx.add_init_script(f"localStorage.setItem('locale',{json.dumps(locale)});localStorage.setItem('dujiao_theme',{json.dumps(theme)});")
            if not live:
                conf = copy.deepcopy(config)
                conf['data'].setdefault('contact', {})['wechat'] = accounts
                def intercept(route):
                    path = urlparse(route.request.url).path
                    assert route.request.method == 'GET', 'Unexpected mutation in user QA'
                    if path.endswith('/public/config'): data = conf
                    elif path.endswith('/public/products'): data = products
                    elif '/public/products/' in path: data = details[path.rsplit('/', 1)[-1]]
                    else: data = {'status_code': 0, 'msg': 'success', 'data': []}
                    route.fulfill(json=data)
                ctx.route('**/api/**', intercept)
                ctx.route('**/uploads/**', lambda route: route.fulfill(response=route.fetch(url='https://www.gptpaynow.com'+urlparse(route.request.url).path)))
            page = ctx.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)
            paths = ['/', '/products/gptplus']
            if live and width == 1440: paths += ['/products/gptpro100', '/products/gptpro200', '/products/gptpro500']
            for path in paths:
                page.goto(base+path, wait_until='networkidle')
                expect(page.locator('[data-testid="wechat-account"]')).to_have_count(len(accounts))
                expect(page.locator('[data-testid="wechat-support"]')).to_have_count(1 if accounts else 0)
                assert page.locator('[data-testid="wechat-account"]').evaluate_all('(els)=>els.map(el=>el.dataset.account)') == accounts
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (width, path)
                if path.startswith('/products/'):
                    assert 'think-more-9' not in page.locator('.theme-prose').inner_text(), 'Legacy contact still shown'
                if accounts:
                    page.locator('[data-testid="wechat-account"]').first.click()
                    assert page.evaluate('navigator.clipboard.readText()') == accounts[0]
                    page.locator('[data-testid="wechat-support"]').scroll_into_view_if_needed()
                    if (live or len(accounts) == 3) and path in ['/', '/products/gptplus']:
                        page.screenshot(path=str(output/f'{"live" if live else "mock"}-{width}-{theme}-{path.replace("/", "-") or "home"}.png'))
                assert not errors, errors
            print(json.dumps({'width': width, 'locale': locale, 'theme': theme, 'contacts': len(accounts), 'pages': len(paths), 'errors': errors}), flush=True)
            ctx.close()
        browser.close()

if __name__ == '__main__':
    main()
