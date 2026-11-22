import json,sys,sqlite3,time,shlex
from pathlib import Path
sys.path.insert(0,'deploy/autnine-bridge')
from manage import connect,login,api,command,ROOT,REMOTE

LOCAL_PRODUCT_ID=14
UPSTREAM_PRODUCT_ID=17
UPSTREAM_SKU_ID=20
TEMP_SLUG='chatgpt-plus-ios-upstream-temp'
BACKUP_TAG=time.strftime('%Y%m%d-%H%M%S')

ssh=connect()
try:
    token=login(ssh)
    # Read current state before making changes.
    product=api(ssh,'GET',f'/admin/products/{LOCAL_PRODUCT_ID}',token=token)['data']
    assert product['slug']=='chatgpt-plus-ios', product['slug']
    mappings=api(ssh,'GET','/admin/product-mappings?page_size=100',token=token)['data']
    assert not any(m.get('local_product_id')==LOCAL_PRODUCT_ID and m.get('is_active') for m in mappings), 'local product already has active mapping'

    # Back up the live shop DB before touching mapping rows.
    backup_cmd=f'''python3 - <<'PY'
import sqlite3
src=sqlite3.connect('file:/var/lib/docker/volumes/payforothers18003_app_db/_data/dujiao.db?mode=ro',uri=True)
dst=sqlite3.connect('/opt/gptpaynow-autnine/backups/shop-before-ios-remap-{BACKUP_TAG}.db')
src.backup(dst); dst.close(); src.close()
print('BACKUP_OK')
PY'''
    print(command(ssh,backup_cmd).strip())

    # Extend the bridge catalog with Autnine's iOS product so the existing importer can use the normal mapping workflow.
    catalog_path=ROOT/'catalog.json'
    catalog=json.loads(catalog_path.read_text(encoding='utf-8'))
    if not any(x.get('product',{}).get('id')==UPSTREAM_PRODUCT_ID for x in catalog):
        p=product
        new={
          'source_url':'https://autnine.com/products/gptplus-ios',
          'slug':'gptplus-ios',
          'plan_code':'PLUS_IOS',
          'country':'US',
          'product':{
            'id':UPSTREAM_PRODUCT_ID,
            'title':p.get('title') or {},
            'description':p.get('description') or {},
            'content':p.get('content') or {},
            'seo_meta':p.get('seo_meta') or {},
            'price_amount':str(p.get('price_amount') or '148.00'),
            'currency':'CNY',
            'fulfillment_type':'auto',
            'manual_form_schema':{},
            'is_active':True,
            'category_id':1,
            'images':['/images/chatgpt.jpeg'],
            'tags':['iOS','US','covering recharge','renewal unsupported'],
            'skus':[{'id':UPSTREAM_SKU_ID,'sku_code':'DEFAULT','spec_values':{},'price_amount':'118.00','stock_quantity':0,'is_active':True}],
          }
        }
        catalog.append(new)
        catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
        print('CATALOG_LOCAL_APPENDED')
    else:
        print('CATALOG_ALREADY_PRESENT')

    # Preserve the remote catalog and restart only the bridge service with the new catalog.
    with ssh.open_sftp() as sftp:
        remote_catalog=REMOTE+'/catalog.json'
        sftp.get(remote_catalog, str(ROOT/f'catalog-before-ios-remap-{BACKUP_TAG}.json'))
        sftp.put(str(catalog_path), remote_catalog+'.new')
    command(ssh,f'mv {REMOTE}/catalog.json.new {REMOTE}/catalog.json && cd {REMOTE} && docker compose -f compose.yml up -d --build --wait')
    print('BRIDGE_RESTARTED')

    # Import through the normal admin mapping API. This creates a temporary local clone and a complete SKU mapping.
    try:
        imp=api(ssh,'POST','/admin/product-mappings/import',{'connection_id':1,'upstream_product_id':UPSTREAM_PRODUCT_ID,'category_id':1,'slug':TEMP_SLUG},token=token)
    except Exception as e:
        # If an interrupted previous attempt left the temp mapping, reuse it after verifying it.
        mappings=api(ssh,'GET','/admin/product-mappings?page_size=100',token=token)['data']
        found=next((m for m in mappings if m.get('upstream_product_id')==UPSTREAM_PRODUCT_ID and m.get('is_active')),None)
        if not found: raise
        imp={'data':found}
        print('REUSED_EXISTING_TEMP_MAPPING')
    mapping=imp['data']
    mapping_id=int(mapping['id'])
    detail=api(ssh,'GET',f'/admin/product-mappings/{mapping_id}',token=token)['data']
    m=detail['mapping']; sku_maps=detail.get('sku_mappings') or []
    temp_pid=int(m['local_product_id'])
    assert int(m['upstream_product_id'])==UPSTREAM_PRODUCT_ID
    assert len(sku_maps)==1 and int(sku_maps[0]['upstream_sku_id'])==UPSTREAM_SKU_ID
    temp_sid=int(sku_maps[0]['local_sku_id'])
    assert temp_pid != LOCAL_PRODUCT_ID and temp_sid != 14
    print('TEMP_MAPPING',mapping_id,temp_pid,temp_sid)

    # Atomically re-point this mapping and its SKU mapping to the existing public product/SKU.
    swap_script=f'''
import sqlite3
path='/var/lib/docker/volumes/payforothers18003_app_db/_data/dujiao.db'
db=sqlite3.connect(path)
db.execute('PRAGMA foreign_keys=ON')
try:
    with db:
        row=db.execute("SELECT local_product_id,upstream_product_id,is_active FROM product_mappings WHERE id=?",({mapping_id},)).fetchone()
        assert row and row[0]=={temp_pid} and row[1]=={UPSTREAM_PRODUCT_ID} and row[2]==1, row
        assert db.execute("SELECT COUNT(*) FROM product_mappings WHERE local_product_id=? AND deleted_at IS NULL",({LOCAL_PRODUCT_ID},)).fetchone()[0]==0
        sm=db.execute("SELECT local_sku_id,upstream_sku_id FROM sku_mappings WHERE product_mapping_id=? AND deleted_at IS NULL",({mapping_id},)).fetchone()
        assert sm and sm[0]=={temp_sid} and sm[1]=={UPSTREAM_SKU_ID}, sm
        assert db.execute("SELECT COUNT(*) FROM product_skus WHERE id=? AND product_id=? AND deleted_at IS NULL",(14,{LOCAL_PRODUCT_ID})).fetchone()[0]==1
        db.execute("UPDATE product_mappings SET local_product_id=?, upstream_fulfillment_type='auto', is_active=1 WHERE id=?",({LOCAL_PRODUCT_ID},{mapping_id}))
        db.execute("UPDATE sku_mappings SET local_sku_id=? WHERE product_mapping_id=? AND local_sku_id=?",(14,{mapping_id},{temp_sid}))
        db.execute("UPDATE products SET fulfillment_type='upstream', is_mapped=1, manual_stock_total=0, manual_stock_locked=0, stock_display_mode='status', min_purchase_quantity=1, max_purchase_quantity=1, is_active=1 WHERE id=?",({LOCAL_PRODUCT_ID},))
        db.execute("UPDATE product_skus SET manual_stock_total=0, manual_stock_locked=0, is_active=1 WHERE id=? AND product_id=?",(14,{LOCAL_PRODUCT_ID}))
        assert db.execute("SELECT COUNT(*) FROM product_mappings WHERE local_product_id=? AND deleted_at IS NULL",({LOCAL_PRODUCT_ID},)).fetchone()[0]==1
        assert db.execute("SELECT COUNT(*) FROM sku_mappings WHERE product_mapping_id=? AND local_sku_id=? AND upstream_sku_id=? AND deleted_at IS NULL",({mapping_id},14,{UPSTREAM_SKU_ID})).fetchone()[0]==1
except Exception:
    db.rollback(); raise
finally: db.close()
print('SWAP_OK')
'''
    print(command(ssh,'python3 -',swap_script).strip())

    # Sync the mapping using the live bridge; this refreshes upstream price/stock metadata on the existing SKU.
    sync=api(ssh,'POST',f'/admin/product-mappings/{mapping_id}/sync',token=token)
    print('SYNCED',sync.get('data'))

    # Delete the temporary clone through the admin API now that the mapping points at product 14.
    try:
        api(ssh,'DELETE',f'/admin/products/{temp_pid}',token=token)
        print('TEMP_PRODUCT_DELETED',temp_pid)
    except Exception as e:
        print('TEMP_PRODUCT_DELETE_SKIPPED',str(e)[:180])

    # Read final state and assert the important invariants.
    final=api(ssh,'GET',f'/admin/products/{LOCAL_PRODUCT_ID}',token=token)['data']
    allmaps=api(ssh,'GET','/admin/product-mappings?page_size=100',token=token)['data']
    active=[x for x in allmaps if x.get('local_product_id')==LOCAL_PRODUCT_ID and x.get('is_active')]
    assert final['slug']=='chatgpt-plus-ios'
    assert final['fulfillment_type']=='upstream' and final['is_mapped'] is True and final['is_active'] is True
    assert active and int(active[0]['upstream_product_id'])==UPSTREAM_PRODUCT_ID
    print('FINAL',json.dumps({'product_id':final['id'],'slug':final['slug'],'fulfillment_type':final['fulfillment_type'],'is_mapped':final['is_mapped'],'price':final['price_amount'],'mapping_id':active[0]['id'],'upstream_product_id':active[0]['upstream_product_id']},ensure_ascii=False))
finally:
    ssh.close()
