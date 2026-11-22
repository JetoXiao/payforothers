"""Read-only deployed UI checks. Does not create orders or send messages."""
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'deploy/autnine-bridge'))
from manage import connect,login,command

ssh=connect()
try:
 token=login(ssh)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(channel='chrome',headless=True)
  for width,lang in [(1440,'zh-CN'),(390,'en-US')]:
   ctx=browser.new_context(viewport={'width':width,'height':1000})
   ctx.add_init_script('localStorage.setItem("admin_token",'+json.dumps(token)+');localStorage.setItem("admin_locale",'+json.dumps(lang)+');')
   mutations=[]
   def guard(route):
    if route.request.method=='GET':route.continue_()
    else:mutations.append(route.request.url);route.abort()
   ctx.route('**/api/**',guard)
   p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
   p.goto('https://www.gptpaynow.com/ops-56a6029ce437/settings/notifications',wait_until='networkidle')
   card=p.locator('[data-testid="wecom-settings"]');expect(card).to_be_visible()
   expect(card.locator('input[type=checkbox]')).to_be_checked()
   expect(card.locator('#wecom-webhook')).to_have_value('')
   expect(card.locator('button').nth(1)).to_be_enabled()
   assert not errors,errors
   assert not mutations,mutations
   assert p.evaluate('document.documentElement.scrollWidth <= innerWidth')
   out=ROOT/'output/verification/wecom';out.mkdir(parents=True,exist_ok=True)
   p.screenshot(path=str(out/f'live-{width}-{lang}.png'))
   print('LIVE_WECOM_UI_OK',width,lang,flush=True)
   ctx.close()
  browser.close()
 print(command(ssh,"docker inspect -f '{{.State.Health.Status}}' payforothers18003-app-1").strip())
 before=command(ssh,'cat /opt/gptpaynow-backups/wecom-20261009-034750/containers-before.txt')
 after=command(ssh,"docker ps --format '{{.Names}} {{.ID}}'")
 old=dict(line.split() for line in before.splitlines());new=dict(line.split() for line in after.splitlines())
 for name,identifier in old.items():
  if name!='payforothers18003-app-1':assert new.get(name)==identifier, name+' changed unexpectedly'
 print('UNRELATED_CONTAINERS_UNCHANGED',flush=True)
finally:ssh.close()
