"""Mocked browser regression: no production requests or real messages."""
import base64
import json
import sys
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
BASE=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:4175'
TOKEN='test.'+base64.urlsafe_b64encode(b'{"admin_id":999}').decode().rstrip('=')+'.signature'
with sync_playwright() as pw:
 browser=pw.chromium.launch(channel='chrome',headless=True)
 for width,lang in [(1440,'zh-CN'),(390,'en-US'),(768,'zh-TW')]:
  ctx=browser.new_context(viewport={'width':width,'height':1000})
  ctx.add_init_script('localStorage.setItem("admin_token",'+json.dumps(TOKEN)+');localStorage.setItem("admin_locale",'+json.dumps(lang)+');')
  state={'enabled':False,'has_webhook':False,'tests':0,'saves':0}
  def route_api(route):
   path=urlparse(route.request.url).path;method=route.request.method;data={}
   if path.endswith('/authz/me'):data={'is_super':True,'roles':[],'policies':[]}
   elif path.endswith('/public/config'):data={'brand':{'site_name':'GptPayNow'}}
   elif path.endswith('/notification-center'):
    if method=='PUT':
     w=route.request.post_data_json['channels']['wecom'];state['saves']+=1
     state['enabled']=w['enabled']
     state['has_webhook']=False if w['clear_webhook'] else bool(w['webhook'] or state['has_webhook'])
    data={'channels':{'wecom':{'enabled':state['enabled'],'has_webhook':state['has_webhook'],'webhook':''}}}
   elif path.endswith('/notification-center/test'):
    assert route.request.post_data_json['channel']=='wecom'
    assert route.request.post_data_json['target']=='configured-group'
    state['tests']+=1;data={'sent':True}
   elif path.endswith('/logs'):data=[]
   else:assert method=='GET','Unexpected mutation'
   route.fulfill(json={'status_code':0,'msg':'ok','data':data,'pagination':{'page':1,'page_size':10,'total':0,'total_page':1}})
  ctx.route('**/api/**',route_api)
  page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(BASE+'/settings/notifications',wait_until='networkidle')
  card=page.locator('[data-testid="wecom-settings"]');expect(card).to_be_visible()
  checkbox=card.locator('input[type=checkbox]');hook=card.locator('#wecom-webhook');buttons=card.locator('button')
  expect(buttons.nth(1)).to_be_disabled()
  checkbox.check();hook.fill('https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=0123456789abcdef')
  buttons.nth(0).click();expect(hook).to_have_value('');expect(buttons.nth(1)).to_be_enabled()
  buttons.nth(1).click();expect(buttons.nth(1)).to_be_enabled();assert state['tests']==1
  checkbox.uncheck();expect(buttons.nth(1)).to_be_disabled();buttons.nth(0).click();expect(buttons.nth(1)).to_be_enabled()
  assert state['has_webhook'] and not state['enabled']
  page.on('dialog',lambda d:d.accept());buttons.nth(2).click();expect(buttons).to_have_count(2)
  assert not state['has_webhook'] and state['saves']==3
  assert not errors,errors
  assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'horizontal overflow'
  out=ROOT/'output/verification/wecom';out.mkdir(parents=True,exist_ok=True)
  page.screenshot(path=str(out/f'config-{width}-{lang}.png'))
  print('WECOM_UI_OK',width,lang,flush=True);ctx.close()
 browser.close()
