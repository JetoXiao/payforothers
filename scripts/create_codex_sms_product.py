import json, http.client, mimetypes, re, sys
from pathlib import Path
sys.path.insert(0,'deploy/autnine-bridge')
from manage import connect,login,api

ROOT=Path(r'D:\codex_workspace\projects\payForOthers')
ASSET=ROOT/'output/imagegen/codex-sms-service-20261117'

def tunnel_request(ssh, method, path, body, headers):
    conn=http.client.HTTPConnection('127.0.0.1',18003,timeout=60)
    conn.sock=ssh.get_transport().open_channel('direct-tcpip',('127.0.0.1',18003),('127.0.0.1',0))
    conn.request(method,'/api/v1'+path,body,headers)
    response=conn.getresponse(); raw=response.read(); conn.close()
    data=json.loads(raw)
    if response.status>=400 or data.get('status_code')!=0:
        raise RuntimeError(f'{path}: {response.status} {data.get("msg", raw[:300])!r}')
    return data

def upload(ssh,token,path,scene='product'):
    boundary='----CodexUploadBoundary17'
    data=Path(path).read_bytes(); filename=Path(path).name
    parts=[]
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="scene"\r\n\r\n{scene}\r\n'.encode())
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: image/png\r\n\r\n'.encode()+data+b'\r\n')
    body=b''.join(parts)+f'--{boundary}--\r\n'.encode()
    return tunnel_request(ssh,'POST','/admin/upload',body,{'Authorization':'Bearer '+token,'Content-Type':f'multipart/form-data; boundary={boundary}','Content-Length':str(len(body))})

ssh=connect()
try:
 token=login(ssh)
 existing=api(ssh,'GET','/admin/products?page_size=200',token=token)['data']
 assert not any(p.get('slug')=='codex-sms-service' for p in existing), 'codex-sms-service already exists'
 uploads=[]
 for name in ['codex-sms-cover.png','codex-sms-detail.png']:
  result=upload(ssh,token,ASSET/name)
  url=result['data']['url']; uploads.append(url); print('UPLOADED',name,url)
 title={'zh-CN':'Codex 接码服务｜人工协助接收验证短信','zh-TW':'Codex 接碼服務｜人工協助接收驗證簡訊','en-US':'Codex SMS Verification Assistance | Manual Support'}
 desc={'zh-CN':'用于本人 Codex 登录或验证流程中需要短信验证码时的人工接码协助。随机国家，人工处理，10 元/次。','zh-TW':'用於本人 Codex 登入或驗證流程需要簡訊驗證碼時的人工接碼協助。隨機國家，人工處理，10 元/次。','en-US':'Manual assistance for receiving SMS during your own Codex login or verification flow. Random country, manual handling, CNY 10 per request.'}
 content={
  'zh-CN':'<h2>服务说明</h2><p>适用于本人 Codex 登录或验证时出现短信验证码要求的情况。下单后由人工处理，随机国家接收短信，并在订单中交付结果。</p><h2>购买须知</h2><p>请提供必要的页面信息，不要提交密码、Cookie、Session、Token 或其他无关隐私。服务不承诺绕过平台规则、身份验证或风控，也不保证每次验证成功。</p>',
  'zh-TW':'<h2>服務說明</h2><p>適用於本人 Codex 登入或驗證時出現簡訊驗證碼要求的情況。下單後由人工處理，隨機國家接收簡訊，並在訂單中交付結果。</p><h2>購買須知</h2><p>請提供必要的頁面資訊，不要提交密碼、Cookie、Session、Token 或其他無關隱私。服務不承諾繞過平台規則、身份驗證或風控，也不保證每次驗證成功。</p>',
  'en-US':'<h2>Service</h2><p>For your own Codex login or verification flow when an SMS code is requested. We handle the request manually, use a randomly selected country, and deliver the result in the order.</p><h2>Before purchase</h2><p>Provide only the necessary page information. Never submit passwords, cookies, sessions, tokens, or unrelated private data. This service does not bypass platform rules, identity checks, or risk controls, and success is not guaranteed.</p>'
 }
 instr={'zh-CN':'下单后提交必要页面信息，等待人工处理；请勿发送密码、Cookie、Session 或 Token。','zh-TW':'下單後提交必要頁面資訊，等待人工處理；請勿發送密碼、Cookie、Session 或 Token。','en-US':'Submit only the necessary page information after ordering and wait for manual handling. Never send passwords, cookies, sessions, or tokens.'}
 body={'category_id':1,'slug':'codex-sms-service','seo_meta':{'description':desc,'keywords':{'zh-CN':'Codex接码,短信验证,人工协助','zh-TW':'Codex接碼,簡訊驗證,人工協助','en-US':'Codex SMS verification assistance'}},'title':title,'description':desc,'content':content,'instructions':instr,'manual_form_schema':{'fields':[]},'price_amount':10.0,'cost_price_amount':0.0,'images':uploads,'tags':['Codex','接码服务','人工交付','随机国家'],'purchase_type':'guest','min_purchase_quantity':1,'max_purchase_quantity':1,'stock_display_mode':'exact','fulfillment_type':'manual','manual_stock_total':999,'payment_channel_ids':[1],'is_affiliate_enabled':True,'is_active':True,'sort_order':50,'skus':[{'sku_code':'CODEX_SMS','spec_values':{'zh-CN':'随机国家'},'price_amount':10.0,'cost_price_amount':0.0,'manual_stock_total':999,'is_active':True,'sort_order':0}]}
 created=api(ssh,'POST','/admin/products',body,token=token)['data']
 print('CREATED',json.dumps({'id':created['id'],'slug':created['slug'],'title':created['title'],'price':created['price_amount'],'fulfillment_type':created['fulfillment_type'],'manual_stock_total':created['manual_stock_total'],'images':created['images'],'is_active':created['is_active']},ensure_ascii=False))
 assert created['slug']=='codex-sms-service' and created['fulfillment_type']=='manual' and created['price_amount']=='10.00' and created['manual_stock_total']==999 and created['is_active']
 (ASSET/'product-payload.json').write_text(json.dumps(body,ensure_ascii=False,indent=2),encoding='utf-8')
finally: ssh.close()
