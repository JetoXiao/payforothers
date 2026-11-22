"""One-time, guarded catalog import/deploy. Never logs credentials or buys CDKs."""
import hashlib
import html
import http.client
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time
import urllib.request

import paramiko
from cryptography.fernet import Fernet

sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parent
REMOTE='/opt/gptpaynow-autnine'
ITEMS=[('gptgo','GO','EG','Go','Egypt','埃及','埃及'),('gptplus','PLUS','PH','Plus','Philippines','菲律宾','菲律賓'),('gptpro5x','PRO5X','CL','Pro 5x','Chile','智利','智利'),('gptpro20x','PRO20X','PH','Pro 20x','Philippines','菲律宾','菲律賓'),('gptpro25x','PRO25X','CL','Pro 25x','Chile','智利','智利')]

def connect():
    raw=Path('D:/codex_workspace/cloud-dingrui.txt').read_bytes()
    ssh=paramiko.SSHClient();ssh.load_system_host_keys();ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(re.search(rb'\d+\.\d+\.\d+\.\d+',raw).group().decode(),username='root',password=raw.split()[-1].decode(),timeout=20)
    return ssh

def command(ssh,cmd,stdin=None):
    i,o,e=ssh.exec_command(cmd,timeout=45)
    if stdin is not None:i.write(stdin);i.channel.shutdown_write()
    out=o.read().decode('utf-8','replace');err=e.read().decode('utf-8','replace')
    status=o.channel.recv_exit_status()
    if status:raise RuntimeError(f'Remote operation failed ({status}): {out[-1500:]} {err[-1500:]}')
    return out

def api(ssh,method,path,body=None,token=None):
    conn=http.client.HTTPConnection('127.0.0.1',18003,timeout=45)
    conn.sock=ssh.get_transport().open_channel('direct-tcpip',('127.0.0.1',18003),('127.0.0.1',0))
    headers={'Content-Type':'application/json'}
    if token:headers['Authorization']='Bearer '+token
    conn.request(method,'/api/v1'+path,json.dumps(body).encode() if body is not None else None,headers)
    response=conn.getresponse();data=json.loads(response.read());conn.close()
    if response.status>=400 or data.get('status_code')!=0:raise RuntimeError(f'{path}: {data.get("msg","request failed")}')
    return data

def login(ssh):
    access=Path('D:/codex_workspace/payforothers-18003-access.txt').read_text(encoding='utf-8')
    return api(ssh,'POST','/admin/login',{'username':re.search(r'Username:\s*(\S+)',access)[1],'password':re.search(r'Password:\s*(\S+)',access)[1]})['data']['token']

def content(plan,region,locale):
    if locale=='en-US':
        groups=[('Product overview',[f'ChatGPT {plan} · {region} region · one-month CDK for your own account.','The supplier lists 24-hour self-service redemption availability. CDK delivery and subscription activation are separate steps.']),
                ('Before purchase',['Check the region, account and subscription conditions before paying. This listing is for accounts without an active Go, Plus or Pro subscription; it does not promise stacking or renewal.','The supplier excludes Outlook/Hotmail accounts and Team workspaces. Previous App Store or Google Play subscriptions may need a 2–3 day grace period after expiry.','Use your own account and a stable connection. Disclose previous promotional or zero-price subscriptions to support before purchase.']),
                ('Delivery and redemption',['Once payment is confirmed, your CDK is procured and displayed in the order. Open the redemption service and follow its current instructions. Never share the CDK publicly.','The redemption provider may request sensitive account authorization data. Verify its domain and privacy terms before proceeding; do not send passwords, session tokens or recovery codes to GptPayNow support.','Check your plan and receipt in ChatGPT after completion. Do not enable renewal or change the plan using a supplier-provided payment method.']),
                ('Subscription warranty and support',['The supplier describes a 30-day subscription-loss warranty, excluding account suspension. Warranty eligibility and the actual cause need to be checked against the order.','Successfully delivered and redeemed products are generally not returnable for a change of mind, subject to applicable law and the agreed product terms. For issues, retain your order number and redacted screenshots.','For subscription loss, failed redemption or delivery issues, contact GptPayNow WeChat support: think-more-9. This is an independent service, not an OpenAI-affiliated store.'])]
        link='Redeem CDK'
    elif locale=='zh-TW':
        groups=[('商品資訊',[f'ChatGPT {plan} · {region}區 · 一個月卡充 CDK，充值至你自己的帳戶。','上游標示可 24 小時自助充值。卡密交付與訂閱到帳是不同步驟，以訂單及兌換頁實際狀態為準。']),
                ('購買前確認',['請核對地區、週期和帳戶條件。本商品適用於目前沒有 Go、Plus、Pro 等有效訂閱的帳戶，不承諾覆蓋或疊加現有權益。','上游不接受 Outlook、Hotmail 信箱帳戶或 Team 工作區充值。曾透過 App Store／Google Play 訂閱的帳戶，過期後可能仍需等待 2–3 天寬限期。','使用本人帳戶並維持穩定網路；如有過零元或促銷訂閱紀錄，請先聯絡客服確認。']),
                ('交付與兌換',['付款確認後，系統採購 CDK 並交付至訂單。到兌換服務頁按實際指引操作，請勿公開或轉發完整卡密。','第三方兌換服務可能要求帳戶授權資訊。Session／Token 屬敏感登入憑據，操作前請核對域名和資料規則；不要將密碼、Token 或復原碼發給本站客服。','完成後到 ChatGPT 訂閱頁確認權益，帳單與收據以帳戶實際可查看內容為準。不要使用供貨方支付方式自行開啟續費或變更套餐。']),
                ('訂閱質保與售後',['上游標示提供 30 天掉訂閱質保，不涵蓋封號保證；是否符合質保及原因需結合訂單核查。帳戶共用、反代、代認證等非個人正常使用情形可能不在上游質保範圍。','正常交付並成功充值後，原則上不接受因個人改變意願提出的退換申請；適用法律及有效商品約定另有規定的除外。','兌換失敗、未到帳或掉訂閱，請提供訂單號與去識別化截圖，聯絡本站微信客服 think-more-9。本店為獨立服務，不代表 OpenAI 官方。'])]
        link='前往卡密兌換服務'
    else:
        groups=[('商品信息',[f'ChatGPT {plan} · {region}区 · 一个月卡充 CDK，充值至你自己的账号。','上游标注可 24 小时自助充值。卡密交付与订阅到账是不同步骤，以订单及兑换页实际状态为准。']),
                ('购买前确认',['请核对地区、周期和账号条件。本商品适用于当前没有 Go、Plus、Pro 等有效订阅的账号，不承诺覆盖或叠加现有权益。','上游不接受 Outlook、Hotmail 邮箱账号或 Team 工作区充值。曾通过 App Store／Google Play 订阅的账号，过期后可能仍需等待 2–3 天宽限期。','使用本人账号并保持稳定网络；如有过零元或促销订阅记录，请先联系客服确认。']),
                ('交付与兑换',['支付确认后，系统采购 CDK 并交付至订单。到兑换服务页按实际指引操作，请勿公开或转发完整卡密。','第三方兑换服务可能要求账号授权信息。Session／Token 属敏感登录凭据，操作前请核对域名和数据规则；不要将密码、Token 或恢复码发给本站客服。','完成后到 ChatGPT 订阅页确认权益，账单与收据以账号实际可查看内容为准。不要使用供货方支付方式自行开启续费或变更套餐。']),
                ('订阅质保与售后',['上游标注提供 30 天掉订阅质保，不涵盖封号保证；是否符合质保及原因需结合订单核查。账号共享、反代、代认证等非个人正常使用情形可能不在上游质保范围。','正常交付并成功充值后，原则上不接受因个人改变意愿提出的退换申请；适用法律及有效商品约定另有规定的除外。','兑换失败、未到账或掉订阅，请提供订单号与脱敏截图，联系本站微信客服 think-more-9。本店为独立服务，不代表 OpenAI 官方。'])]
        link='前往卡密兑换服务'
    rendered = ''.join('<h2>'+html.escape(title)+'</h2>'+''.join('<p>'+html.escape(p)+'</p>' for p in paras) for title,paras in groups)
    # Storefront copy must describe our service, not expose supplier annotations.
    replacements = {
        '上游标注': '本商品说明', '上游標示': '本商品說明', '上游不接受': '本商品不支持', '上游不支援': '本商品不支援', '上游提供': '本商品说明',
        '上游提供': '本商品說明', '上游质保': '本商品质保', '上游質保': '本商品質保', '供货方支付方式': '其他支付方式', '供貨方支付方式': '其他支付方式', '供货方': '其他服务方', '供貨方': '其他服務方',
        'The supplier lists': 'This product offers', 'The supplier excludes': 'This product does not support',
        'The supplier describes': 'This product describes', 'supplier-provided payment method': 'other payment method',
        'supplier payment method': 'other payment method',
    }
    for old, new in replacements.items(): rendered = rendered.replace(old, new)
    if locale == 'zh-CN':
        warning = '<p><strong>重要购买须知：仅限当前处于 ChatGPT Free 状态的账号充值；不支持续费、覆盖或叠加已有 Go、Plus、Pro 等订阅。</strong></p>'
    elif locale == 'zh-TW':
        warning = '<p><strong>重要購買須知：僅限目前處於 ChatGPT Free 狀態的帳戶充值；不支援續費、覆蓋或疊加既有 Go、Plus、Pro 等訂閱。</strong></p>'
    else:
        warning = '<p><strong>Important: for ChatGPT Free accounts only. Renewal, covering, and stacking an existing Go, Plus, or Pro subscription are not supported.</strong></p>'
    return warning + rendered + f'<p><a href="https://966qjy.xyz" target="_blank" rel="noopener noreferrer">{link}</a></p>'

def prepare():
    raw=subprocess.check_output(['curl.exe','-fsSL','--max-time','30','https://autnine.com/api/v1/public/products?page_size=50'])
    data=json.loads(raw);assert data['status_code']==0
    byslug={p['slug']:p for p in data['data']}
    catalog=[]
    for slug,code,country,label,en,cn,tw in ITEMS:
        p=byslug[slug]
        title={'zh-CN':p['title']['zh-CN'],'zh-TW':f'ChatGPT {label} {tw}區 卡充CDK 一個月（訂閱質保）','en-US':f'ChatGPT {label} {en} CDK — 1 Month (Subscription Warranty)'}
        desc={'zh-CN':f'{region_short(cn)}区 {label} 一个月订阅卡密，充值至本人账号；不支持覆盖现有订阅，含订阅质保，不承诺封号保障。','zh-TW':f'{tw}區 {label} 一個月訂閱卡密，充值至本人帳戶；不支援覆蓋現有訂閱，含訂閱質保，不承諾封號保障。','en-US':f'One-month {label} subscription CDK for your own account. {en} region; no subscription stacking. Subscription warranty does not guarantee against account suspension.'}
        product={'id':p['id'],'title':title,'description':desc,'content':{loc:content(label,region,loc) for loc,region in [('zh-CN',cn),('zh-TW',tw),('en-US',en)]},'seo_meta':{'description':desc},'price_amount':p['price_amount'],'currency':'CNY','fulfillment_type':'auto','manual_form_schema':{},'is_active':True,'category_id':1,'images':['/images/chatgpt.jpeg'],'tags':[],
                 'skus':[{'id':s['id'],'sku_code':code,'spec_values':{},'price_amount':s['price_amount'],'stock_quantity':0,'is_active':True} for s in p['skus']]}
        catalog.append({'source_url':'https://autnine.com/products/'+slug,'slug':slug,'plan_code':code,'country':country,'product':product})
    assert len(catalog)==5
    (ROOT/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'source-snapshot.json').write_bytes(raw)
    image='https://autnine.com'+byslug['gptgo']['images'][0]
    subprocess.run(['curl.exe','-fsSL','--max-time','30',image,'-o',str(ROOT/'chatgpt.jpeg')],check=True)
    print('Prepared five products:',[(x['slug'],x['product']['price_amount']) for x in catalog])

def region_short(cn):return '菲' if cn=='菲律宾' else cn

def deploy(ssh):
    key=sys.stdin.read().strip()
    assert key.startswith('ops_live_') and len(key)>30
    command(ssh,f'test ! -e {REMOTE} && install -d -m 700 {REMOTE} {REMOTE}/secrets {REMOTE}/data {REMOTE}/backups')
    sftp=ssh.open_sftp()
    for name in ['bridge.py','Dockerfile','compose.yml','.dockerignore','catalog.json','source-snapshot.json','chatgpt.jpeg']:
        sftp.put(str(ROOT/name),REMOTE+'/'+name)
    for name,value in {'upstream_api_key':key,'bridge_secret':secrets.token_urlsafe(48),'storage_key':Fernet.generate_key().decode()}.items():
        with sftp.open(REMOTE+'/secrets/'+name,'w') as f:f.write(value)
        sftp.chmod(REMOTE+'/secrets/'+name,0o600)
    sftp.close()
    print(command(ssh,f"cd {REMOTE}; nohup sh -c 'docker compose -f compose.yml up -d --build --wait; result=$?; echo $result > deploy.exit; exit $result' > deploy.log 2>&1 < /dev/null &"))

def migrate(ssh):
    token=login(ssh);a=lambda method,path,body=None:api(ssh,method,path,body,token)
    old=a('GET','/admin/products?page_size=100')['data']
    assert len(old)==6 and {p['id'] for p in old}==set(range(1,7))
    assert all(re.search(r'-[1-6]$',p['title']['zh-CN']) and p['slug'].startswith('chatgpt-go-india-cdk-1-month') for p in old)
    catalog=json.loads((ROOT/'catalog.json').read_text(encoding='utf-8'))
    with ssh.open_sftp() as sftp:
        with sftp.open(REMOTE+'/backups/products-before.json','w') as f:f.write(json.dumps(old,ensure_ascii=False))
        sftp.chmod(REMOTE+'/backups/products-before.json',0o600)
        with sftp.open(REMOTE+'/secrets/bridge_secret') as f:shared=f.read().decode()
    backup="""import sqlite3,os,json
os.umask(0o077)
path='/var/lib/docker/volumes/payforothers18003_app_db/_data/dujiao.db'
s=sqlite3.connect('file:'+path+'?mode=ro',uri=True)
d=sqlite3.connect('/opt/gptpaynow-autnine/backups/shop-before.db');s.backup(d);d.close()
print('Old product order references:',s.execute('SELECT product_id,count(*) FROM order_items WHERE product_id BETWEEN 1 AND 6 GROUP BY product_id').fetchall());s.close()
"""
    print(command(ssh,'python3 -',backup))
    conn=a('POST','/admin/site-connections',{'name':'Autnine 卡台 · 966qjy','base_url':'http://autnine-bridge:8080','api_key':'gptpaynow-autnine','api_secret':shared,'protocol':'dujiao-next','retry_max':5,'retry_intervals':'[30,60,300]','exchange_rate':1,'price_markup_percent':0,'auto_sync_price':False})['data']
    print('Connection created',conn['id'])
    ping=a('POST',f'/admin/site-connections/{conn["id"]}/ping')['data'];print('Ping verified',ping['site_name'],ping['currency'])
    result={'connection_id':conn['id'],'created':[],'deleted':[],'archived':[]}
    for index,entry in enumerate(catalog):
        mapping=a('POST','/admin/product-mappings/import',{'connection_id':conn['id'],'upstream_product_id':entry['product']['id'],'category_id':1,'slug':entry['slug']})['data']
        pid=mapping['local_product_id'];p=a('GET',f'/admin/products/{pid}')['data']
        body={k:p.get(k) for k in ['category_id','slug','seo_meta','title','description','content','images','tags','purchase_type','stock_display_mode','fulfillment_type']}
        body.update(price_amount=float(p['price_amount']),is_active=False,sort_order=100-index,max_purchase_quantity=1,min_purchase_quantity=1,stock_display_mode='status',payment_channel_ids=[],is_affiliate_enabled=False,
                    instructions={'zh-CN':'请复制订单中的卡密，前往 https://966qjy.xyz 按指引兑换。不要公开卡密；问题请联系微信 think-more-9。','en-US':'Redeem your order CDK at https://966qjy.xyz. Keep it private; support: WeChat think-more-9.','zh-TW':'請複製訂單卡密，至 https://966qjy.xyz 按指引兌換。請勿公開卡密；客服微信 think-more-9。'},
                    skus=[{'id':s['id'],'sku_code':s['sku_code'],'spec_values':s['spec_values'],'price_amount':float(s['price_amount']),'cost_price_amount':float(s['cost_price_amount']),'is_active':True,'manual_stock_total':0} for s in p['skus']])
        a('PUT',f'/admin/products/{pid}',body)
        a('POST',f'/admin/product-mappings/{mapping["id"]}/sync')
        result['created'].append({'id':pid,'slug':entry['slug'],'mapping_id':mapping['id']})
    # Only after all five are ready do we switch the live catalog.
    for p in old:
        a('PATCH',f'/admin/products/{p["id"]}',{'is_active':False})
        try:
            a('DELETE',f'/admin/products/{p["id"]}')
            result['deleted'].append(p['id'])
        except RuntimeError as e:
            if '订单' not in str(e) and 'order' not in str(e):raise
            result['archived'].append(p['id'])
    for p in result['created']:a('PATCH',f'/admin/products/{p["id"]}',{'is_active':True})
    with ssh.open_sftp() as sftp:
        with sftp.open(REMOTE+'/migration-result.json','w') as f:f.write(json.dumps(result,ensure_ascii=False,indent=2))
    print('CATALOG_MIGRATION',json.dumps(result,ensure_ascii=False))

if __name__=='__main__':
    action=sys.argv[1]
    if action=='prepare':prepare()
    else:
        ssh=connect()
        try:
            if action=='deploy':deploy(ssh)
            elif action=='migrate':migrate(ssh)
            elif action=='cmd':print(command(ssh,sys.argv[2]))
        finally:ssh.close()
