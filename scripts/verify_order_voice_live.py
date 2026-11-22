"""Authenticated read-only smoke check for deployed voice assets and order polling."""
import hashlib
import io
import json
import sys
import wave
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'deploy/autnine-bridge'))
from manage import connect,login,command

def main():
 ssh=connect()
 try:
  token=login(ssh)
  with sync_playwright() as pw:
   browser=pw.chromium.launch(channel='chrome',headless=True)
   ctx=browser.new_context(viewport={'width':1440,'height':1000})
   # Track real media objects without mocking playback or authentication.
   ctx.add_init_script('localStorage.setItem("admin_token",'+json.dumps(token)+''');
window.actualAudio=[];
const OriginalAudio=window.Audio;
window.Audio=function(...args){ const result=new OriginalAudio(...args);window.actualAudio.push(result);return result; };
''')
   mutations=[]
   def guard(route):
    if route.request.method=='GET':route.continue_()
    else:mutations.append(route.request.url);route.abort()
   ctx.route('**/api/**',guard)
   page=ctx.new_page();errors=[];polls=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   page.on('response',lambda r:polls.append(r.status) if '/api/v1/admin/orders?' in r.url else None)
   page.goto('https://www.gptpaynow.com/ops-56a6029ce437/settings',wait_until='networkidle')
   page.locator('[data-testid="order-voice-control"]').click()
   expect(page.locator('[data-testid="order-voice-status"]')).to_have_attribute('data-status','off')
   page.locator('[data-testid="order-voice-enabled"]').check()
   expect(page.locator('[data-testid="order-voice-status"]')).to_have_attribute('data-status','listening',timeout=15000)
   page.wait_for_function('actualAudio.some(a=>a.currentTime>0.1 && !a.error)',timeout=10000)
   page.wait_for_function('actualAudio.some(a=>a.ended)',timeout=10000)
   actual_src=page.evaluate('actualAudio[0].src')
   assert '/ops-56a6029ce437/assets/' in actual_src
   response=ctx.request.get(actual_src)
   assert response.status==200
   with wave.open(io.BytesIO(response.body()),'rb') as wav:
    assert wav.getnframes()/wav.getframerate()>1
   assert hashlib.sha256(response.body()).digest()==hashlib.sha256((ROOT/'frontend/admin/src/assets/audio/order-voice-enabled-zh.wav').read_bytes()).digest()
   page.wait_for_timeout(16000)
   assert len(polls)>=2 and all(p==200 for p in polls),polls
   # Empty initial history replay: no synthetic orders or payment writes performed.
   page.locator('[data-testid="order-voice-enabled"]').uncheck()
   count=len(polls);page.wait_for_timeout(16000)
   assert len(polls)==count
   output=ROOT/'output/verification/order-voice';output.mkdir(parents=True,exist_ok=True)
   page.screenshot(path=str(output/'live-control.png'))
   assert not errors,errors
   assert not mutations,mutations
   print('LIVE_REAL_AUDIO_ENDED_ORDER_POLL_OFF_NO_MUTATIONS_OK',flush=True)
   ctx.close();browser.close()
  print(command(ssh,"docker inspect -f '{{.State.Health.Status}}' payforothers18003-app-1").strip())
 finally:ssh.close()

if __name__=='__main__':main()
