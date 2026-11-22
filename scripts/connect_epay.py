"""Configure Epay via the existing admin API; secrets never enter source/output.

Verifies merchant metadata with read-only queries, creates a disabled channel,
and makes ONE unpaid CNY 0.01 gateway test order. Enables only on usable pay URL.
No payment, success callback, fulfillment or upstream CDK purchase is performed.
"""
import hashlib
import hmac
import http.client
import json
from pathlib import Path
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'deploy/autnine-bridge'))
from manage import connect, command, api, login

GATEWAY='https://pay.gptpaynow.com'
NOTIFY='https://www.gptpaynow.com/api/v1/payments/callback'
RETURN='https://www.gptpaynow.com/pay'

def main():
    expected=sys.stdin.read().strip()
    if len(expected)!=32:raise ValueError('Pass the provided MD5 key via stdin')
    ssh=connect()
    try:
        token=login(ssh)
        a=lambda method,path,body=None:api(ssh,method,path,body,token)
        current=a('GET','/admin/payment-channels')['data']
        if current:raise RuntimeError('Existing payment channels found; review before changing configuration')
        php=r'''<?php
require '/var/www/html/config.php';
$db=new PDO('mysql:host='.$dbconfig['host'].';dbname='.$dbconfig['dbname'],$dbconfig['user'],$dbconfig['pwd']);
$u=$db->query('SELECT uid,`key`,keytype,status,pay FROM pay_user WHERE uid=1000')->fetch(PDO::FETCH_ASSOC);
echo json_encode($u);
?>'''
        # Capture through SSH, never print this credential-bearing response.
        merchant=json.loads(command(ssh,'cd /opt/epay-gptpaynow && docker compose exec -T php php',php))
        if not hmac.compare_digest(expected,merchant['key']) or merchant['keytype']!=0 or merchant['status']!=1 or merchant['pay']!=1:
            raise RuntimeError('Merchant mode/status/key mismatch; no changes made')
        config={'epay_version':'v1','gateway_url':GATEWAY,'merchant_id':'1000','merchant_key':expected,'sign_type':'MD5','notify_url':NOTIFY,'return_url':RETURN}
        payload={'name':'支付宝','provider_type':'epay','channel_type':'alipay','interaction_mode':'qr',
                 'fee_rate':'0','fixed_fee':'0','min_amount':'0.01','max_amount':'10000.00',
                 'hide_amount_out_range':True,'payment_roles':['guest','member'],'payment_types':['order'],
                 'config_json':config,'is_active':False,'sort_order':10}
        channel=a('POST','/admin/payment-channels',payload)['data']
        cid=channel['id']
        assert channel['config_json']['merchant_key']!=expected
        print('Payment channel saved, ID:',cid,'(disabled pending gateway verification)')
        out_no='GPNVERIFY'+time.strftime('%Y%m%d%H%M%S')+secrets.token_hex(3)
        params={'pid':'1000','type':'alipay','out_trade_no':out_no,'notify_url':NOTIFY,'return_url':RETURN,
                'name':'GptPayNow 支付接口联调（请勿付款）','money':'0.01','clientip':'43.163.239.213','device':'pc'}
        signed='&'.join(k+'='+params[k] for k in sorted(params))
        params['sign']=hashlib.md5((signed+expected).encode()).hexdigest();params['sign_type']='MD5'
        # Use the same origin network as the storefront, preserving TLS verification.
        probe=r'''import urllib.request,json,sys
params=sys.stdin.buffer.read()
request=urllib.request.Request('https://pay.gptpaynow.com/mapi.php',data=params,headers={'Content-Type':'application/x-www-form-urlencoded','User-Agent':'GptPayNow-Payment-Integration/1.0'})
with urllib.request.urlopen(request,timeout=25) as r:
 data=json.load(r)
 print(json.dumps({'http_code':r.status,'code':data.get('code'),'msg':data.get('msg'),'trade_no':data.get('trade_no'),'has_payurl':bool(data.get('payurl')),'has_qrcode':bool(data.get('qrcode')),'has_urlscheme':bool(data.get('urlscheme'))},ensure_ascii=False))
'''
        # Read POST form from stdin and Python source as command argument, with no credentials in command.
        import shlex
        result=json.loads(command(ssh,'python3 -c '+shlex.quote(probe),urllib.parse.urlencode(params)))
        success=result['code']==1 and any(result.get(k) for k in ['has_payurl','has_qrcode','has_urlscheme'])
        if success:
            a('PUT',f'/admin/payment-channels/{cid}',{'is_active':True})
        # Invalid callback targets a nonexistent verification reference and cannot complete any order.
        callback=urllib.request.Request(NOTIFY,data=urllib.parse.urlencode({'pid':'1000','out_trade_no':out_no,'trade_status':'TRADE_SUCCESS','money':'0.01','sign':'INVALID','sign_type':'MD5'}).encode())
        with urllib.request.urlopen(callback,timeout=15) as r:
            callback_body=r.read().decode();callback_status=r.status
        assert callback_body.strip()=='fail'
        public=api(ssh,'GET','/public/config')['data']
        exposed=public.get('payment_channels',[])
        assert expected not in json.dumps(public)
        assert not any('config_json' in c for c in exposed)
        state={'channel_id':cid,'gateway':GATEWAY,'merchant_id':1000,'version':'v1 / MD5',
               'notify_url':NOTIFY,'return_url':RETURN,'enabled':success,'test_order_no':out_no,
               'gateway_probe':result,'invalid_callback_rejected':callback_status==200,
               'public_channel_present':any(c.get('id')==cid for c in exposed),'paid':False}
        backup=Path('D:/codex_workspace/epay-shop-integration-result.json')
        backup.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(state,ensure_ascii=False))
    finally: ssh.close()

if __name__=='__main__':main()
