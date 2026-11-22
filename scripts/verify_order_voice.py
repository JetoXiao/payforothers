"""Browser QA with mocked orders/audio; never creates or pays production orders."""
import base64
import json
import sys
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
BASE = sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:4175'
TOKEN = 'test.'+base64.urlsafe_b64encode(b'{"admin_id":999}').decode().rstrip('=')+'.signature'

with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='chrome',headless=True)
    def context(width=1440, allowed=True, mock_audio=True, locale='zh-CN'):
        ctx=browser.new_context(viewport={'width':width,'height':950})
        init='localStorage.setItem("admin_token",'+json.dumps(TOKEN)+');localStorage.setItem("admin_locale",'+json.dumps(locale)+');'
        if mock_audio:
            init+='''window.voicePlays=[];window.voiceBlock=false;
HTMLMediaElement.prototype.play=function(){ if(window.voiceBlock)return Promise.reject(new DOMException('blocked','NotAllowedError'));window.voicePlays.push({src:this.src,volume:this.volume});return Promise.resolve() };
HTMLMediaElement.prototype.pause=function(){}; HTMLMediaElement.prototype.load=function(){};'''
        ctx.add_init_script(init)
        state={'rows':[{'id':1,'order_no':'QA-EXISTING','status':'pending_payment','total_amount':'1.00','currency':'CNY','items':[]}], 'polls':0,'denied':False}
        def route_api(route):
            assert route.request.method=='GET', 'Unexpected mutation during voice QA'
            path=urlparse(route.request.url).path
            data={}
            if path.endswith('/authz/me'): data={'is_super':allowed,'roles':[],'policies':[] if allowed else [{'action':'GET','object':'/admin/settings'}]}
            elif path.endswith('/public/config'):data={'brand':{'site_name':'GptPayNow'}}
            elif path.endswith('/admin/orders'):
                state['polls']+=1
                if state['denied']:
                    route.fulfill(json={'status_code':403,'msg':'Forbidden','data':None});return
                data=state['rows']
            elif '/admin/orders/' in path:data=state['rows'][0]
            route.fulfill(json={'status_code':0,'msg':'success','data':data,'pagination':{'page':1,'page_size':100,'total':len(state['rows']),'total_page':1}})
        ctx.route('**/api/**',route_api)
        return ctx,state

    ctx,state=context()
    p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
    p.goto(BASE+'/settings',wait_until='networkidle')
    p.locator('[data-testid="order-voice-control"]').click()
    expect(p.locator('[data-testid="order-voice-status"]')).to_have_attribute('data-status','off')
    p.locator('[data-testid="order-voice-enabled"]').check()
    expect(p.locator('[data-testid="order-voice-status"]')).to_have_attribute('data-status','listening')
    assert len(p.evaluate('voicePlays'))==1
    assert state['polls']==1
    state['rows'].insert(0,{'id':2,'order_no':'QA-NEW','status':'pending_payment','total_amount':'1.00','currency':'CNY','items':[]})
    p.wait_for_function('voicePlays.filter(x=>x.src.includes("new-order-")).length===1',timeout=22000)
    expect(p.locator('[data-testid="order-voice-count"]')).to_have_text('1')
    p.locator('#order-voice-volume').fill('35')
    p.locator('[data-testid="order-voice-test"]').click()
    assert p.evaluate('voicePlays.at(-1).volume')==0.35
    # A second activated tab shares the live cursor and does not announce old orders.
    q=ctx.new_page();q.goto(BASE+'/settings',wait_until='networkidle')
    q.locator('[data-testid="order-voice-control"]').click()
    expect(q.locator('[data-testid="order-voice-status"]')).to_have_attribute('data-status','activate')
    q.locator('[data-testid="order-voice-test"]').click()
    state['rows'].insert(0,{'id':3,'order_no':'QA-MULTITAB','status':'paid','total_amount':'1.00','currency':'CNY','items':[]})
    q.wait_for_timeout(16000)
    both=p.evaluate('voicePlays.filter(x=>x.src.includes("new-order-")).length')+q.evaluate('voicePlays.filter(x=>x.src.includes("new-order-")).length')
    assert both==2, ('duplicate tab announcement',both)
    q.close()
    # Disabling in the browser stops polling and playback.
    if not p.locator('[data-testid="order-voice-enabled"]').is_visible():p.locator('[data-testid="order-voice-control"]').click()
    p.locator('[data-testid="order-voice-enabled"]').uncheck()
    polls=state['polls']; plays=len(p.evaluate('voicePlays'))
    p.wait_for_timeout(16000)
    assert state['polls']==polls and len(p.evaluate('voicePlays'))==plays
    # Explicit blocked-playback state, recover via another user gesture.
    p.evaluate('voiceBlock=true')
    p.locator('[data-testid="order-voice-enabled"]').check()
    expect(p.locator('[data-testid="order-voice-status"]')).to_have_attribute('data-status','blocked')
    p.evaluate('voiceBlock=false')
    p.locator('[data-testid="order-voice-test"]').click()
    expect(p.locator('[data-testid="order-voice-status"]')).to_have_attribute('data-status','listening')
    # A denied request stops polling without repeated global notifications.
    state['denied']=True
    expect(p.locator('[data-testid="order-voice-status"]')).to_have_attribute('data-status','unauthorized',timeout=22000)
    polls=state['polls'];p.wait_for_timeout(16000);assert polls==state['polls']
    assert not errors,errors
    ctx.close()
    print('VOICE_BASELINE_NEW_DUPLICATE_MULTITAB_DISABLE_BLOCKED_AUTH_OK',flush=True)

    for width,locale in [(390,'zh-CN'),(1440,'en-US')]:
        ctx,state=context(width=width,locale=locale)
        page=ctx.new_page();page.goto(BASE+'/settings',wait_until='networkidle')
        page.locator('[data-testid="order-voice-control"]').click()
        page.locator('[data-testid="order-voice-enabled"]').check()
        expect(page.locator('[data-testid="order-voice-status"]')).to_have_attribute('data-status','listening')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        output=ROOT/'output/verification/order-voice';output.mkdir(parents=True,exist_ok=True)
        page.screenshot(path=str(output/f'control-{width}-{locale}.png'))
        ctx.close()
    ctx,state=context(allowed=False)
    page=ctx.new_page();page.goto(BASE+'/settings',wait_until='networkidle')
    expect(page.locator('[data-testid="order-voice-control"]')).to_have_count(0)
    assert state['polls']==0
    ctx.close()
    # Real media decode and ended event (not a simulated audio implementation).
    ctx,state=context(mock_audio=False)
    ctx.add_init_script('window.audioEnded=0;document.addEventListener("ended",()=>window.audioEnded++,true);')
    page=ctx.new_page();page.goto(BASE+'/settings',wait_until='networkidle')
    page.locator('[data-testid="order-voice-control"]').click()
    page.locator('[data-testid="order-voice-enabled"]').check()
    expect(page.locator('[data-testid="order-voice-status"]')).to_have_attribute('data-status','listening')
    print('REAL_BROWSER_AUDIO_PLAY_ACCEPTED',flush=True)
    ctx.close();browser.close()
