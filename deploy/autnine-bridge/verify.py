"""Live read-only catalog/UI verification. No checkout/order creation."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from manage import ITEMS, ROOT, connect, api, login, command

def main():
    ssh=connect()
    token=login(ssh)
    public=api(ssh,'GET','/public/products?page_size=50')['data']
    assert len(public)==5 and {p['slug'] for p in public}=={i[0] for i in ITEMS}
    for p in public:
        assert p['fulfillment_type']=='auto'
        assert p['purchase_type']=='member'
        assert p['images'] and all(x.startswith('/uploads/') for x in p['images'])
        assert all(p['content'].get(lang) for lang in ['zh-CN','zh-TW','en-US'])
        assert 'pay.ldxp.cn' not in json.dumps(p) and 'qiujiuyi' not in json.dumps(p)
        assert p['min_purchase_quantity']==p['max_purchase_quantity']==1
        print(p['slug'],p['price_amount'],p['stock_status'])
    mappings=api(ssh,'GET','/admin/product-mappings',token=token)['data']
    assert len(mappings)==5 and all(m['is_active'] for m in mappings)
    errors=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel='chrome',headless=True)
        for theme,width,locale in [('light',1440,'zh-CN'),('dark',390,'en-US')]:
            context=browser.new_context(viewport={'width':width,'height':1000},locale=locale)
            context.add_init_script(f"localStorage.setItem('dujiao_theme','{theme}');localStorage.setItem('locale','{locale}');")
            page=context.new_page()
            page.on('pageerror',lambda e:errors.append(str(e)))
            for slug in ['']+[i[0] for i in ITEMS]:
                url='https://www.gptpaynow.com/'+('products/'+slug if slug else '')
                res=page.goto(url,wait_until='networkidle')
                assert res.status==200
                page.wait_for_timeout(250)
                body=page.locator('body').inner_text()
                assert 'qiujiuyi' not in body and '买U教程' not in body and '印度区' not in body
                if slug:
                    assert ('商品信息' in body if locale=='zh-CN' else 'Product overview' in body)
                    assert 'think-more-9' in body
                    assert page.locator('img[src^="/uploads/"]').count()>0
                else:
                    assert page.locator('a[href*="chatgpt-go-india"]').count()==0
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth+1')
                for image in page.locator('img').all():
                    if image.is_visible():image.scroll_into_view_if_needed()
                page.wait_for_timeout(500)
                broken=page.locator('img').evaluate_all('(images)=>images.filter(x=>x.complete&&x.naturalWidth===0).map(x=>x.src)')
                assert not broken,broken
                if slug in ('','gptplus'):
                    page.screenshot(path=str(ROOT/f'verify-{slug or "home"}-{theme}.png'),full_page=True)
            context.close()
        browser.close()
    assert not errors,errors
    # Internal guard test uses a nonexistent order: cannot cause a purchase.
    test=r'''import sys,json,hashlib,hmac,time,urllib.request,sqlite3
from pathlib import Path
sys.path.insert(0,'/app')
raw=json.dumps({'sku_id':5,'quantity':1,'downstream_order_no':'GPN-NONEXISTENT-VERIFY','trace_id':'NO-ORDER'}).encode()
ts=int(time.time());path='/api/v1/upstream/orders';secret=Path('/run/secrets/bridge_secret').read_text().strip()
sign=hmac.new(secret.encode(),f'POST\n{path}\n{ts}\n{hashlib.md5(raw).hexdigest()}'.encode(),hashlib.sha256).hexdigest()
headers={'Dujiao-Next-Api-Key':'gptpaynow-autnine','Dujiao-Next-Timestamp':str(ts),'Dujiao-Next-Signature':sign}
result=json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8080'+path,data=raw,headers=headers)))
assert result['error_code']=='order_unpaid',result
db=sqlite3.connect('/data/bridge.db');assert db.execute('SELECT COUNT(*) FROM purchases').fetchone()[0]==0;db.close()
key=Path('/run/secrets/upstream_api_key').read_text().strip()
wallet=json.load(urllib.request.urlopen(urllib.request.Request('https://966qjy.xyz/api/partners/v1/wallet',headers={'X-API-Key':key,'User-Agent':'GptPayNow-CDK-Bridge/1.0'})))
print(json.dumps({'paid_order_guard':'PASS','purchases':0,'available_cny':wallet['data']['available_cny']}))
'''
    print(command(ssh,'cd /opt/gptpaynow-autnine && docker compose -f compose.yml exec -T bridge python -',test))
    ssh.close()
    print('PASS: five mapped products, 12 responsive page checks, no JS page errors, no card purchases.')

if __name__=='__main__':main()
