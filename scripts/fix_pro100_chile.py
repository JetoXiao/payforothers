import copy,json,hashlib,sys,time
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(r'D:\codex_workspace\projects\payForOthers')
OUT=ROOT/'output/operations/pro100-chile-20261114'; OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,'deploy/autnine-bridge')
from manage import connect,login,api,command

ssh=connect()
try:
 token=login(ssh)
 p=api(ssh,'GET','/admin/products/9',token=token)['data']
 assert p['slug']=='gptpro100'
 # Remote catalog and DB backups before mutation.
 remote='/opt/gptpaynow-autnine/catalog.json'
 stamp='20261114-1512'
 with ssh.open_sftp() as sftp:
  sftp.get(remote,str(OUT/f'catalog-before-{stamp}.json'))
  with sftp.open(remote) as f: old_catalog=f.read()
 expected=hashlib.sha256(old_catalog).hexdigest()
 backup_script=f'''python3 - <<'PY'
import sqlite3
src=sqlite3.connect('file:/var/lib/docker/volumes/payforothers18003_app_db/_data/dujiao.db?mode=ro',uri=True)
dst=sqlite3.connect('/opt/gptpaynow-autnine/backups/pro100-chile-20261114.db')
src.backup(dst); dst.close(); src.close(); print('DB_BACKUP_OK')
PY'''
 print(command(ssh,backup_script).strip())
 (OUT/'catalog-before-hash.txt').write_text(expected,encoding='ascii')
 (OUT/'product-before.json').write_text(json.dumps(p,ensure_ascii=False,indent=2),encoding='utf-8')

 def repl(v):
  if isinstance(v,str):
   return v.replace('Egypt','Chile').replace('埃及','智利').replace('Egyptian','Chilean')
  if isinstance(v,dict): return {k:repl(x) for k,x in v.items()}
  if isinstance(v,list): return [repl(x) for x in v]
  return v
 title=repl(p.get('title') or {})
 desc=repl(p.get('description') or {})
 seo=repl(p.get('seo_meta') or {})
 content=repl(p.get('content') or {})
 # Keep the product's current SKU ID and sale price; only region/copy/route changes.
 channels=p.get('payment_channel_ids') or []
 if isinstance(channels,str):
  try: channels=json.loads(channels)
  except: channels=[]
 body={k:p.get(k) for k in ['category_id','slug','images','tags','purchase_type','min_purchase_quantity','max_purchase_quantity','stock_display_mode','is_affiliate_enabled','sort_order','wholesale_prices']}
 body.update(seo_meta=seo,title=title,description=desc,content=content,instructions=p.get('instructions') or {},
             price_amount=690.0,cost_price_amount=610.0,fulfillment_type='upstream',local_manual_fulfillment=False,
             manual_stock_total=0,manual_form_schema={},payment_channel_ids=channels,is_active=True,
             skus=[{'id':s['id'],'sku_code':s['sku_code'],'spec_values':s.get('spec_values') or {},'price_amount':float(s['price_amount']),'cost_price_amount':610.0,'manual_stock_total':0,'is_active':s.get('is_active',True),'sort_order':s.get('sort_order',0)} for s in p['skus']])
 updated=api(ssh,'PUT','/admin/products/9',body,token=token)['data']
 assert '智利' in updated['title']['zh-CN'] and '埃及' not in updated['title']['zh-CN']
 print('LOCAL_PRODUCT_UPDATED')
 # Update bridge catalog only if it is unchanged since backup; keep all other entries unchanged.
 catalog=json.loads(old_catalog)
 entry=next(x for x in catalog if x['product']['id']==2)
 assert entry['plan_code']=='PRO5X'
 entry['source_url']='https://autnine.com/products/gptpro100'; entry['country']='CL'
 for key in ('title','description','content','seo_meta'):
  entry['product'][key]=copy.deepcopy(updated.get(key) or {})
 entry['product']['price_amount']='610.00'; entry['product']['fulfillment_type']='auto'; entry['product']['skus'][0]['price_amount']='610.00'; entry['product']['skus'][0]['spec_values']={'zh-CN':'智利区'}
 new=json.dumps(catalog,ensure_ascii=False,indent=2)+'\n'
 (OUT/'catalog-pro100-chile.json').write_text(new,encoding='utf-8')
 with ssh.open_sftp() as sftp:
  sftp.put(str(OUT/'catalog-pro100-chile.json'),remote+'.new')
 # Verify current remote file is still the backed-up version before replacing it.
 check=command(ssh,f"sha256sum {remote} | awk '{{print $1}}'").strip()
 assert check==expected,(check,expected)
 command(ssh,f"mv {remote}.new {remote}; cd /opt/gptpaynow-autnine; docker compose -f compose.yml up -d --build --wait")
 print('BRIDGE_UPDATED')
 # Sync mapping and validate only PRO5X / CL is used.
 sync=api(ssh,'POST','/admin/product-mappings/3/sync',token=token)
 detail=api(ssh,'GET','/admin/product-mappings/3',token=token)['data']
 sm=detail['sku_mappings'][0]
 assert detail['mapping']['upstream_product_id']==2 and detail['mapping']['upstream_status']=='active'
 assert sm['upstream_sku_id']==2 and sm['upstream_stock']>0
 final=api(ssh,'GET','/admin/products/9',token=token)['data']
 assert final['fulfillment_type']=='upstream' and final['is_mapped'] and final['is_active']
 print('FINAL',json.dumps({'slug':final['slug'],'title':final['title']['zh-CN'],'fulfillment_type':final['fulfillment_type'],'mapping_upstream_product_id':detail['mapping']['upstream_product_id'],'mapping_upstream_sku_id':sm['upstream_sku_id'],'upstream_stock':sm['upstream_stock'],'price':final['price_amount'],'cost':final['cost_price_amount']},ensure_ascii=False))
 (OUT/'product-after.json').write_text(json.dumps(final,ensure_ascii=False,indent=2),encoding='utf-8')
finally:
 ssh.close()
