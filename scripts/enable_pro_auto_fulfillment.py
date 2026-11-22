"""Guarded two-product operations. Never creates customer orders or buys CDKs."""
import hashlib
import json
from pathlib import Path
import shlex
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'deploy/autnine-bridge'))
from manage import api, command, connect, login

OUT = ROOT / 'output/operations/pro-auto-20261111'
REMOTE = '/opt/gptpaynow-autnine'
RUN = REMOTE + '/backups/pro-auto-20261111'
TEMP_SLUG = 'pro5x-ios-auto-import-20261111'


def save(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def deploy(ssh):
    expected = (OUT / 'expected-before-hash.txt').read_text().strip()
    script = f'''
import hashlib,json,os,sqlite3
from pathlib import Path
os.umask(0o077)
root=Path({RUN!r})
assert not root.exists(), 'Operation directory exists; inspect progress before retrying'
raw=Path('{REMOTE}/catalog.json').read_bytes()
assert hashlib.sha256(raw).hexdigest()=={expected!r}, 'Remote catalog changed'
db=sqlite3.connect('file:/var/lib/docker/volumes/payforothers18003_app_db/_data/dujiao.db?mode=ro',uri=True)
db.row_factory=sqlite3.Row
assert db.execute("SELECT COUNT(*) FROM order_items oi JOIN orders o ON o.id=oi.order_id WHERE oi.product_id IN (9,15) AND oi.deleted_at IS NULL AND o.deleted_at IS NULL AND o.status IN ('pending_payment','paid','fulfilling')").fetchone()[0]==0, 'Unfinished existing orders require review'
root.mkdir(mode=0o700)
(root/'catalog-before.json').write_bytes(raw)
dest=sqlite3.connect(str(root/'shop-before.db'));db.backup(dest);dest.close()
snapshot={{}}
for table,where in [('products','id IN (9,15)'),('product_skus','product_id IN (9,15)'),('product_mappings','local_product_id IN (9,15)'),('order_items','product_id IN (9,15)')]:
 rows=[{{k:(v.decode() if isinstance(v,bytes) else v) for k,v in dict(r).items()}} for r in db.execute('SELECT * FROM '+table+' WHERE '+where)]
 snapshot[table]=rows
(root/'rows-before.json').write_text(json.dumps(snapshot,ensure_ascii=False),encoding='utf-8')
db.close()
print('BACKUP_OK')
'''
    print(command(ssh, 'python3 -', script), flush=True)
    with ssh.open_sftp() as sftp:
        sftp.put(str(OUT / 'catalog-pro-auto.json'), REMOTE + '/catalog.pro-auto.new')
    # Only the bridge is rebuilt. Its purchase state and secrets stay in their volumes.
    job = f'''cd {REMOTE}
mv catalog.pro-auto.new catalog.json
nohup sh -c 'docker compose -f compose.yml up -d --build --wait; result=$?; echo "$result" > {RUN}/deploy.exit; exit "$result"' > {RUN}/deploy.log 2>&1 < /dev/null &
'''
    print(command(ssh, job), flush=True)
    save('operation.json', {'remote_backup': RUN, 'phase': 'bridge_build_started'})
    print('BRIDGE_BUILD_STARTED', flush=True)


def status(ssh):
    script = f'''
from pathlib import Path
p=Path({RUN!r})
f=p/'deploy.exit'
print('exit='+f.read_text().strip() if f.exists() else 'BUILD_RUNNING')
print((p/'deploy.log').read_text()[-2200:] if (p/'deploy.log').exists() else '')
'''
    print(command(ssh, 'python3 -', script))


def update_auto(ssh, token, pid, cost, active):
    p = api(ssh, 'GET', f'/admin/products/{pid}', token=token)['data']
    assert p['is_mapped'], 'Missing mapping'
    channels = p.get('payment_channel_ids') or []
    if isinstance(channels, str):
        channels = json.loads(channels)
    body = {k: p.get(k) for k in ['category_id','slug','seo_meta','title','description','content','instructions','images','tags','purchase_type','min_purchase_quantity','max_purchase_quantity','stock_display_mode','is_affiliate_enabled','sort_order','wholesale_prices']}
    body.update(price_amount=float(p['price_amount']),cost_price_amount=cost,
                fulfillment_type='upstream',local_manual_fulfillment=False,manual_stock_total=0,
                manual_form_schema={},is_active=active,payment_channel_ids=channels,
                skus=[{'id':s['id'],'sku_code':s['sku_code'],'spec_values':s.get('spec_values') or {},
                       'price_amount':float(s['price_amount']),'cost_price_amount':cost,
                       'manual_stock_total':0,'is_active':s['is_active'],'sort_order':s.get('sort_order',0)} for s in p['skus']])
    return api(ssh, 'PUT', f'/admin/products/{pid}', body, token=token)['data']


def activate(ssh):
    assert command(ssh, f'cat {RUN}/deploy.exit').strip() == '0', 'Bridge not ready'
    token = login(ssh)
    a = lambda method, path, body=None: api(ssh, method, path, body, token)['data']
    upstream = a('GET', '/admin/upstream-products?connection_id=1&page_size=100')['items']
    byid = {p['id']: p for p in upstream}
    assert byid[2]['price_amount'] == '610.0' and byid[19]['price_amount'] == '605.0'
    assert byid[2]['skus'][0]['id'] == 2 and byid[19]['skus'][0]['id'] == 22
    assert byid[2]['skus'][0]['stock_quantity'] > 0 and byid[19]['skus'][0]['stock_quantity'] > 0
    for pid, slug in ((9, 'gptpro100'),(15, 'chatgpt-pro-5x-ios')):
        p = a('GET', f'/admin/products/{pid}')
        assert p['slug'] == slug and p['fulfillment_type'] == 'manual'
    assert a('GET', '/admin/product-mappings/3')['mapping']['local_product_id'] == 9

    mapping = a('POST', '/admin/product-mappings/import', {
        'connection_id':1,'upstream_product_id':19,'category_id':1,'slug':TEMP_SLUG})
    mid = mapping['id']
    detail = a('GET', f'/admin/product-mappings/{mid}')
    temp_pid = detail['mapping']['local_product_id']
    sm = detail['sku_mappings']
    assert len(sm) == 1 and sm[0]['upstream_sku_id'] == 22
    temp_sid = sm[0]['local_sku_id']
    save('imported-mapping.json', {'mapping_id':mid,'temp_product_id':temp_pid,'temp_sku_id':temp_sid})
    # Briefly close only the requested listings while switching fulfillment and cost snapshots.
    for pid in (9,15):
        a('PATCH', f'/admin/products/{pid}', {'is_active':False})
    swap = f'''
import sqlite3
from datetime import datetime,timezone
db=sqlite3.connect('/var/lib/docker/volumes/payforothers18003_app_db/_data/dujiao.db',timeout=20)
try:
 db.execute('BEGIN IMMEDIATE')
 assert db.execute("SELECT COUNT(*) FROM order_items oi JOIN orders o ON o.id=oi.order_id WHERE oi.product_id IN (9,15) AND oi.deleted_at IS NULL AND o.deleted_at IS NULL AND o.status IN ('pending_payment','paid','fulfilling')").fetchone()[0]==0, 'Existing active orders'
 assert db.execute('SELECT local_product_id,upstream_product_id FROM product_mappings WHERE id=? AND deleted_at IS NULL',({mid},)).fetchone()==({temp_pid},19)
 assert db.execute('SELECT local_sku_id,upstream_sku_id FROM sku_mappings WHERE product_mapping_id=? AND deleted_at IS NULL',({mid},)).fetchone()==({temp_sid},22)
 assert db.execute('SELECT COUNT(*) FROM product_mappings WHERE local_product_id=15 AND deleted_at IS NULL').fetchone()[0]==0
 assert db.execute('SELECT product_id FROM product_skus WHERE id=15 AND deleted_at IS NULL').fetchone()==(15,)
 now=datetime.now(timezone.utc).isoformat(' ')
 db.execute('UPDATE product_mappings SET local_product_id=15,updated_at=? WHERE id=?',(now,{mid}))
 db.execute('UPDATE sku_mappings SET local_sku_id=15,updated_at=? WHERE product_mapping_id=?',(now,{mid}))
 db.execute("UPDATE products SET is_mapped=1,fulfillment_type='upstream',updated_at=? WHERE id=15 AND is_active=0",(now,))
 db.commit()
finally: db.close()
print('IOS_MAPPING_BOUND')
'''
    print(command(ssh, 'python3 -', swap), flush=True)
    for pid, cost, mapid in ((9,610,3),(15,605,mid)):
        update_auto(ssh, token, pid, cost, False)
        a('POST', f'/admin/product-mappings/{mapid}/sync')
        detail = a('GET', f'/admin/product-mappings/{mapid}')
        assert detail['mapping']['upstream_fulfillment_type'] == 'auto'
        assert detail['mapping']['is_active']
        assert detail['sku_mappings'][0]['upstream_stock'] > 0
        a('PATCH', f'/admin/products/{pid}', {'is_active':True})
        print('ENABLED',pid,mapid,flush=True)
    # The unlisted import clone has no orders and is no longer mapped.
    a('DELETE', f'/admin/products/{temp_pid}')
    save('operation.json', {'remote_backup':RUN,'phase':'activated','ios_mapping_id':mid,'removed_temp_product_id':temp_pid})
    print('ACTIVATION_DONE', flush=True)


def verify(ssh):
    token = login(ssh)
    results = []
    mappings = api(ssh,'GET','/admin/product-mappings?page_size=100',token=token)['data']
    for pid, sid, upid, upsid, sell, cost in ((9,9,2,2,'690.00','610.00'),(15,15,19,22,'728.00','605.00')):
        p = api(ssh,'GET',f'/admin/products/{pid}',token=token)['data']
        m = [x for x in mappings if x['local_product_id']==pid and x['is_active']]
        assert len(m)==1 and m[0]['upstream_product_id']==upid
        d = api(ssh,'GET',f'/admin/product-mappings/{m[0]["id"]}',token=token)['data']
        assert len(d['sku_mappings'])==1
        sm = d['sku_mappings'][0]
        assert sm['local_sku_id']==sid and sm['upstream_sku_id']==upsid and sm['upstream_stock']>0
        assert p['fulfillment_type']=='auto' and p['is_mapped'] and not p['local_manual_fulfillment'] and p['is_active']
        assert p['price_amount']==sell and p['cost_price_amount']==cost
        results.append({'product_id':pid,'slug':p['slug'],'fulfillment_type':p['fulfillment_type'],
                        'local_manual_fulfillment':p['local_manual_fulfillment'],'mapping_id':m[0]['id'],
                        'upstream_product_id':upid,'upstream_sku_id':upsid,'cost':cost,'price':sell,'stock':sm['upstream_stock']})
    save('verified-products.json', results)
    print(json.dumps(results,ensure_ascii=False),flush=True)
    # Check raw fulfillment and that all pre-existing order item snapshots were preserved exactly.
    script = f'''
import json,sqlite3
from pathlib import Path
db=sqlite3.connect('file:/var/lib/docker/volumes/payforothers18003_app_db/_data/dujiao.db?mode=ro',uri=True);db.row_factory=sqlite3.Row
before=json.loads(Path('{RUN}/rows-before.json').read_text())
for item in before['order_items']:
 row=db.execute('SELECT * FROM order_items WHERE id=?',(item['id'],)).fetchone()
 current={{k:(v.decode() if isinstance(v,bytes) else v) for k,v in dict(row).items()}}
 assert current==item, 'Order item snapshot changed'
for pid in (9,15):
 row=db.execute('SELECT fulfillment_type,is_mapped FROM products WHERE id=?',(pid,)).fetchone()
 assert tuple(row)==('upstream',1)
for old in before['product_skus']:
 row=db.execute('SELECT manual_stock_sold,manual_stock_locked FROM product_skus WHERE id=?',(old['id'],)).fetchone()
 assert row['manual_stock_sold']==old['manual_stock_sold'] and row['manual_stock_locked']==0
db.close()
print('RAW_UPSTREAM_AND_HISTORY_PRESERVED')
'''
    print(command(ssh,'python3 -',script),flush=True)


if __name__ == '__main__':
    ssh = connect()
    try:
        {'deploy':deploy,'status':status,'activate':activate,'verify':verify}[sys.argv[1]](ssh)
    finally:
        ssh.close()
