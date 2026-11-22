"""Create one Autnine mapped ChatGPT Go product with guarded pricing and images."""
import hashlib, http.client, json, mimetypes, sys, time
from pathlib import Path
sys.path.insert(0, 'deploy/autnine-bridge')
from manage import connect, login, api

ROOT=Path(__file__).resolve().parents[1]
HOME=ROOT/'assets/products/chatgpt-go-reference.png'
DETAIL=ROOT/'assets/products/chatgpt-go-reference.png'

def upload(ssh, token, path):
    boundary='----GptPayNowGo'+str(int(time.time()*1000)); content=path.read_bytes(); mime=mimetypes.guess_type(path.name)[0] or 'image/png'
    body=(f'--{boundary}\r\nContent-Disposition: form-data; name="scene"\r\n\r\nproducts\r\n--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{path.name}"\r\nContent-Type: {mime}\r\n\r\n').encode()+content+f'\r\n--{boundary}--\r\n'.encode()
    c=http.client.HTTPConnection('127.0.0.1',18003,timeout=90); c.sock=ssh.get_transport().open_channel('direct-tcpip',('127.0.0.1',18003),('127.0.0.1',0)); c.request('POST','/api/v1/admin/upload',body,{'Authorization':'Bearer '+token,'Content-Type':'multipart/form-data; boundary='+boundary,'Content-Length':str(len(body))}); r=c.getresponse(); data=json.loads(r.read()); c.close()
    if r.status>=400 or data.get('status_code')!=0: raise RuntimeError('image upload failed')
    return data['data']['url']

def main():
    ssh=connect(); token=login(ssh)
    products=api(ssh,'GET','/admin/products?page_size=100',token=token)['data']
    local_slug='gptgo-egypt'
    if any(p.get('slug')==local_slug for p in products): raise RuntimeError('gptgo already exists; refusing duplicate creation')
    mappings=api(ssh,'GET','/admin/product-mappings?page_size=100',token=token)['data']
    if any(m.get('upstream_product_id')==5 for m in mappings): raise RuntimeError('Autnine upstream product 5 already mapped; refusing duplicate')
    conns=api(ssh,'GET','/admin/site-connections?page_size=100',token=token)['data']; conn=next((c for c in conns if c.get('base_url')=='http://autnine-bridge:8080' and c.get('status')=='active'),None)
    if not conn: raise RuntimeError('active Autnine bridge connection not found')
    image_urls=[upload(ssh,token,HOME), upload(ssh,token,DETAIL)]
    mapping=api(ssh,'POST','/admin/product-mappings/import',{'connection_id':conn['id'],'upstream_product_id':5,'category_id':1,'slug':local_slug},token=token)['data']
    pid=mapping['local_product_id']; p=api(ssh,'GET',f'/admin/products/{pid}',token=token)['data']
    title={'zh-CN':'ChatGPT Go 埃及区 卡充CDK 一个月（质保订阅）','zh-TW':'ChatGPT Go 埃及區 卡充CDK 一個月（訂閱質保）','en-US':'ChatGPT Go Egypt CDK — 1 Month (Subscription Warranty)'}
    desc={'zh-CN':'埃及区 ChatGPT Go 一个月充值卡，自动交付至订单；仅限当前 Free 账号，不支持续费、覆盖或叠加已有订阅。','zh-TW':'埃及區 ChatGPT Go 一個月充值卡，自動交付至訂單；僅限目前 Free 帳戶，不支援續費、覆蓋或疊加既有訂閱。','en-US':'One-month ChatGPT Go Egypt recharge card with automatic delivery. For ChatGPT Free accounts only; renewal, covering, and stacking existing subscriptions are not supported.'}
    content={'zh-CN':'<p><strong>重要购买须知：本商品仅限当前处于 ChatGPT Free 状态的账号；不支持续费、覆盖或叠加已有 Go、Plus、Pro 等订阅。</strong></p><h2>商品信息</h2><p>ChatGPT Go · 埃及区 · 一个月卡充 CDK，充值至你自己的账号。</p><p>支付成功后自动交付卡密至订单。卡密交付与订阅到账是不同步骤，以订单及兑换页实际状态为准。</p><h2>购买前确认</h2><p>请核对地区、周期和账号条件。请使用本人账号并保持稳定网络，不要向客服发送密码、Session、Token 或恢复码。</p><h2>交付与兑换</h2><p>支付确认后，在订单详情复制卡密并按兑换页面指引操作。请勿公开或转发完整卡密，完成后到 ChatGPT 订阅页面核对权益。</p><h2>订阅质保与售后</h2><p>平台为符合条件的订单提供订阅支持期；是否符合及原因需结合订单核查。兑换失败、未到账或掉订阅，请提供订单号与脱敏截图联系平台客服。</p><p>本平台为独立服务，不代表 OpenAI 官方。</p>','zh-TW':'<p><strong>重要購買須知：本商品僅限目前處於 ChatGPT Free 狀態的帳戶；不支援續費、覆蓋或疊加既有 Go、Plus、Pro 等訂閱。</strong></p><h2>商品資訊</h2><p>ChatGPT Go · 埃及區 · 一個月卡充 CDK，充值至你自己的帳戶。</p><p>付款成功後自動交付卡密至訂單。卡密交付與訂閱到帳是不同步驟，以訂單及兌換頁實際狀態為準。</p><h2>購買前確認</h2><p>請核對地區、週期和帳戶條件。請使用本人帳戶並維持穩定網路，不要向客服發送密碼、Session、Token 或復原碼。</p><h2>交付與兌換</h2><p>付款確認後，在訂單詳情複製卡密並按兌換頁指引操作。請勿公開或轉發完整卡密，完成後到 ChatGPT 訂閱頁核對權益。</p><h2>訂閱質保與售後</h2><p>平台為符合條件的訂單提供訂閱支援期；是否符合及原因需結合訂單核查。兌換失敗、未到帳或掉訂閱，請提供訂單號與去識別化截圖聯絡平台客服。</p><p>本平台為獨立服務，不代表 OpenAI 官方。</p>','en-US':'<p><strong>Important: this product is for ChatGPT Free accounts only. Renewal, covering, and stacking an existing Go, Plus, or Pro subscription are not supported.</strong></p><h2>Product overview</h2><p>ChatGPT Go · Egypt region · one-month CDK for your own account.</p><p>After payment, the CDK is delivered automatically to your order. CDK delivery and subscription activation are separate steps.</p><h2>Before purchase</h2><p>Check the region, term, and account conditions. Use your own account and never send passwords, Session, Token, or recovery codes to support.</p><h2>Delivery and redemption</h2><p>Copy the CDK from your order and follow the redemption page instructions. Keep the CDK private and verify your plan in ChatGPT after completion.</p><h2>Support</h2><p>Eligible orders receive subscription support. For failed redemption, non-delivery, or subscription loss, provide the order number and redacted screenshots to support.</p><p>GptPayNow is an independent service and is not affiliated with OpenAI.</p>'}
    body={k:p.get(k) for k in ['category_id','slug','seo_meta','tags']}; body.update(slug=local_slug,title=title,description=desc,content=content,instructions={'zh-CN':'支付成功后，复制订单中的卡密，按兑换页面指引操作。请勿公开卡密。','zh-TW':'付款成功後，複製訂單中的卡密，按兌換頁指引操作。請勿公開卡密。','en-US':'After payment, copy the CDK from your order and follow the redemption instructions. Keep it private.'},images=image_urls,purchase_type='guest',fulfillment_type='auto',price_amount=48.0,cost_price_amount=float(p.get('cost_price_amount') or 0),min_purchase_quantity=1,max_purchase_quantity=1,stock_display_mode='status',manual_stock_total=0,payment_channel_ids=[1],is_affiliate_enabled=True,is_active=True,sort_order=10,skus=[{'id':s['id'],'sku_code':s['sku_code'],'spec_values':s.get('spec_values') or {},'price_amount':48.0,'cost_price_amount':float(s.get('cost_price_amount') or 0),'is_active':True,'manual_stock_total':0} for s in p.get('skus') or []])
    api(ssh,'PUT',f'/admin/products/{pid}',body,token=token); api(ssh,'POST',f'/admin/product-mappings/{mapping["id"]}/sync',token=token)
    result=api(ssh,'GET',f'/admin/products/{pid}',token=token)['data']; assert result['slug']==local_slug and result['price_amount']=='48.00' and result['purchase_type']=='guest' and result['fulfillment_type']=='auto' and result['is_active'] and len(result['images'])==2
    print(json.dumps({'product_id':pid,'mapping_id':mapping['id'],'slug':local_slug,'price':'48.00','purchase_type':'guest','fulfillment_type':'auto','images':len(result['images'])}))
    ssh.close()
if __name__=='__main__': main()
