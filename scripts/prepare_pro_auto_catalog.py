"""Prepare only the two requested Pro catalog entries; performs no purchases."""
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'deploy/autnine-bridge'))
from manage import api, command, connect, login

IOS_ID = 19
IOS_SKU_ID = 22
OUT = ROOT / 'output/operations/pro-auto-20261111'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ssh = connect()
    try:
        token = login(ssh)
        remote_path = '/opt/gptpaynow-autnine/catalog.json'
        with ssh.open_sftp() as sftp:
            with sftp.open(remote_path) as f:
                old = f.read()
        catalog = json.loads(old)
        original = copy.deepcopy(catalog)
        products = {pid: api(ssh, 'GET', f'/admin/products/{pid}', token=token)['data'] for pid in (9, 15)}
        assert products[9]['slug'] == 'gptpro100'
        assert products[15]['slug'] == 'chatgpt-pro-5x-ios'
        pro = next(x for x in catalog if x['product']['id'] == 2)
        assert pro['plan_code'] == 'PRO5X'
        pro.update(source_url='https://autnine.com/products/gptpro100', slug='gptpro100', country='EG')
        for key in ('title', 'description', 'content', 'seo_meta'):
            pro['product'][key] = copy.deepcopy(products[9][key])
        pro['product']['price_amount'] = '610.00'
        assert len(pro['product']['skus']) == 1 and pro['product']['skus'][0]['id'] == 2
        pro['product']['skus'][0]['price_amount'] = '610.00'

        assert not any(x['plan_code'] == 'PRO5X_IOS' or x['product']['id'] == IOS_ID for x in catalog)
        assert not any(s['id'] == IOS_SKU_ID for x in catalog for s in x['product']['skus'])
        p = products[15]
        ios = {
            'source_url': 'https://autnine.com/products/gpt5x-ios',
            'slug': 'gpt5x-ios', 'plan_code': 'PRO5X_IOS', 'country': 'US',
            'product': {
                'id': IOS_ID,
                **{key: copy.deepcopy(p.get(key) or {}) for key in ('title', 'description', 'content', 'seo_meta')},
                'price_amount': '605.00', 'currency': 'CNY', 'fulfillment_type': 'auto',
                'manual_form_schema': {}, 'is_active': True, 'category_id': p['category_id'],
                'images': ['/images/chatgpt.jpeg'], 'tags': copy.deepcopy(p.get('tags') or []),
                'skus': [{'id': IOS_SKU_ID, 'sku_code': 'PRO5X_IOS', 'spec_values': {},
                          'price_amount': '605.00', 'stock_quantity': 0, 'is_active': True}],
            },
        }
        catalog.append(ios)
        assert [x for x in catalog if x['product']['id'] not in (2, IOS_ID)] == [x for x in original if x['product']['id'] != 2]
        (OUT / 'catalog-before.json').write_bytes(old)
        (OUT / 'catalog-pro-auto.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        (OUT / 'products-before.json').write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding='utf-8')
        (OUT / 'expected-before-hash.txt').write_text(hashlib.sha256(old).hexdigest(), encoding='ascii')
        print(json.dumps({'entries': len(catalog), 'changes': [('PRO5X', 'EG', 2, 2), ('PRO5X_IOS', 'US', IOS_ID, IOS_SKU_ID)], 'path': str(OUT)}, ensure_ascii=False))
    finally:
        ssh.close()


if __name__ == '__main__':
    main()
