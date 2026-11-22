import sys,json,time
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0,'deploy/autnine-bridge')
from manage import connect,login,api
ssh=connect(); t=login(ssh)
try:
 mappings=api(ssh,'GET','/admin/product-mappings?page_size=100',token=t)['data']
 ids=[int(m['id']) for m in mappings if m.get('is_active') and m.get('upstream_status')!='deleted']
 print('SYNC_IDS',ids)
 result=api(ssh,'POST','/admin/product-mappings/batch-sync',{'ids':ids},token=t)
 print('BATCH_SYNC',json.dumps(result,ensure_ascii=False))
 time.sleep(1)
 rows=[]
 for mid in ids:
  d=api(ssh,'GET',f'/admin/product-mappings/{mid}',token=t)['data']
  m=d['mapping']; p=m.get('product') or {}
  rows.append({'mapping_id':mid,'local_product_id':m['local_product_id'],'upstream_product_id':m['upstream_product_id'],'upstream_status':m['upstream_status'],'upstream_fulfillment_type':m['upstream_fulfillment_type'],'last_synced_at':m.get('last_synced_at'),'sku_mappings':[{'local_sku_id':s['local_sku_id'],'upstream_sku_id':s['upstream_sku_id'],'upstream_price':s['upstream_price'],'upstream_stock':s['upstream_stock'],'upstream_is_active':s['upstream_is_active'],'stock_synced_at':s.get('stock_synced_at')} for s in d.get('sku_mappings',[])]})
 print('MAPPING_STOCK',json.dumps(rows,ensure_ascii=False,indent=2))
 for pid in sorted({r['local_product_id'] for r in rows}):
  p=api(ssh,'GET',f'/admin/products/{pid}',token=t)['data']
  print('PRODUCT_STOCK',json.dumps({'id':pid,'slug':p['slug'],'fulfillment_type':p['fulfillment_type'],'is_active':p['is_active'],'auto_stock_available':p.get('auto_stock_available'),'auto_stock_total':p.get('auto_stock_total'),'stock_status':p.get('stock_status'),'skus':[{'id':s['id'],'sku_code':s['sku_code'],'auto_stock_available':s.get('auto_stock_available'),'upstream_stock':s.get('upstream_stock'),'stock_status':s.get('stock_status'),'is_active':s.get('is_active')} for s in p.get('skus',[])]},ensure_ascii=False))
finally: ssh.close()
