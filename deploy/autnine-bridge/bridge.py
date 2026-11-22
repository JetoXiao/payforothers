"""Private Dujiao-Next protocol adapter for the documented 966qjy CDK API.

Purchases require a matching paid local order. No redemption/session-token APIs
are exposed. Durable idempotency and encrypted CDK storage survive retries.
"""
import base64
import hashlib
import hmac
import json
import os
import re
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from contextlib import contextmanager

from cryptography.fernet import Fernet


class Failure(Exception):
    def __init__(self, code, message, status=200):
        self.code, self.message, self.status = code, message, status


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # Never forward the API key to a redirect destination.


class Bridge:
    def __init__(self, state, shop, catalog, api_key, shared_secret, storage_key):
        self.state, self.shop, self.catalog = str(state), str(shop), catalog
        self.api_key, self.shared_secret = api_key, shared_secret
        self.cipher = Fernet(storage_key)
        self.lock = threading.Lock()
        self.client = urllib.request.build_opener(NoRedirect())
        with self.db() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE IF NOT EXISTS purchases (id INTEGER PRIMARY KEY, order_no TEXT UNIQUE NOT NULL, fingerprint TEXT NOT NULL, body TEXT NOT NULL, upstream_key TEXT UNIQUE NOT NULL, state TEXT NOT NULL, payload BLOB, amount TEXT, batch_id TEXT, created REAL NOT NULL, updated REAL NOT NULL)')

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.state, timeout=25)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def request(self, method, path, body=None, idem=None):
        headers = {'X-API-Key': self.api_key, 'Accept': 'application/json', 'User-Agent': 'GptPayNow-CDK-Bridge/1.0'}
        if idem:
            headers['Idempotency-Key'] = idem
        data = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False, separators=(',', ':')).encode()
            headers['Content-Type'] = 'application/json'
        req = urllib.request.Request('https://966qjy.xyz/api/partners/v1' + path, data=data, headers=headers, method=method)
        try:
            with self.client.open(req, timeout=20) as response:
                result = json.loads(response.read(2_000_000))
        except urllib.error.HTTPError as e:
            # Error bodies can contain card codes; never log or reflect them.
            if e.code in (401, 403):
                raise Failure('unauthorized', 'Upstream API authorization denied') from None
            if e.code == 409:
                raise Failure('idempotency_conflict', 'Upstream idempotency conflict; manual review required') from None
            if e.code == 422:
                raise Failure('purchase_unavailable', 'Upstream rejected purchase; check balance and plan limits') from None
            raise Failure('upstream_unavailable', 'Upstream request unavailable; retry the same order', 503) from None
        except (OSError, ValueError):
            raise Failure('upstream_unavailable', 'Upstream response unavailable; retry the same order', 503) from None
        if result.get('code') != 0:
            raise Failure('upstream_unavailable', 'Upstream operation failed', 503)
        return result['data']

    def products(self):
        plans = {p['code']: p for p in self.request('GET', '/plans')}
        wallet = self.request('GET', '/wallet')
        balance = Decimal(str(wallet['available_cny']))
        products = []
        for item in self.catalog:
            product = json.loads(json.dumps(item['product']))
            plan = plans.get(item['plan_code'], {})
            price = Decimal(str(plan.get('unit_price_cny') or 0))
            enabled = plan.get('can_generate') is True and price > 0 and plan.get('product_type') == 'subscription'
            # A changed upstream region needs an operator review of the listing.
            enabled = enabled and plan.get('country') == item['country']
            stock = min(100, max(0, int(balance // price))) if enabled else 0
            product['price_amount'] = str(price if price > 0 else Decimal(product['price_amount']))
            # Keep visible sold-out listings instead of silently dropping products.
            product['is_active'] = True
            for sku in product['skus']:
                sku.update(price_amount=product['price_amount'], stock_quantity=stock,
                           stock_status='in_stock' if stock else 'sold_out', is_active=True)
            products.append(product)
        return products

    def authorize(self, method, path, headers, raw):
        if headers.get('Dujiao-Next-Api-Key') != 'gptpaynow-autnine':
            raise Failure('unauthorized', 'Invalid bridge credential', 401)
        try:
            ts = int(headers.get('Dujiao-Next-Timestamp', '0'))
        except ValueError:
            raise Failure('unauthorized', 'Invalid timestamp', 401)
        if abs(time.time() - ts) > 60:
            raise Failure('unauthorized', 'Expired signature', 401)
        message = f'{method}\n{path}\n{ts}\n{hashlib.md5(raw).hexdigest()}'
        signature = hmac.new(self.shared_secret.encode(), message.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, headers.get('Dujiao-Next-Signature', '')):
            raise Failure('unauthorized', 'Invalid signature', 401)

    def verify_paid_order(self, body):
        number = body.get('downstream_order_no', '')
        sku, quantity = body.get('sku_id'), body.get('quantity')
        if not re.fullmatch(r'[A-Za-z0-9_-]{8,80}', number) or type(quantity) is not int or not 1 <= quantity <= 100 or type(sku) is not int:
            raise Failure('invalid_request', 'Invalid order parameters')
        if body.get('manual_form_data'):
            raise Failure('invalid_request', 'Account credentials are not accepted')
        match = next((i for i in self.catalog if any(s['id'] == sku for s in i['product']['skus'])), None)
        if not match:
            raise Failure('sku_not_found', 'Unknown upstream SKU')
        db = sqlite3.connect('file:' + self.shop + '?mode=ro', uri=True, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            order = db.execute('SELECT * FROM orders WHERE order_no=? AND deleted_at IS NULL', (number,)).fetchone()
            if not order or not order['paid_at'] or order['status'] not in ('paid', 'fulfilling', 'delivered', 'completed') or Decimal(str(order['refunded_amount'])) > 0:
                raise Failure('order_unpaid', 'Purchase requires a paid, non-refunded local order')
            items = db.execute('SELECT * FROM order_items WHERE order_id=? AND deleted_at IS NULL', (order['id'],)).fetchall()
            if len(items) != 1 or items[0]['quantity'] != quantity or items[0]['fulfillment_type'] != 'upstream':
                raise Failure('invalid_request', 'Local order item mismatch')
            item = items[0]
            mapping = db.execute('SELECT sm.upstream_sku_id,pm.upstream_product_id,c.base_url,c.status FROM sku_mappings sm JOIN product_mappings pm ON pm.id=sm.product_mapping_id JOIN site_connections c ON c.id=pm.connection_id WHERE sm.local_sku_id=? AND pm.local_product_id=? AND pm.is_active=1 AND pm.deleted_at IS NULL AND sm.deleted_at IS NULL AND c.deleted_at IS NULL', (item['sku_id'],item['product_id'])).fetchone()
            if not mapping or mapping['upstream_sku_id'] != sku or mapping['upstream_product_id'] != match['product']['id'] or mapping['base_url'] != 'http://autnine-bridge:8080' or mapping['status'] != 'active':
                raise Failure('invalid_request', 'Local mapping mismatch or connection disabled')
            proc = db.execute('SELECT trace_id FROM procurement_orders WHERE local_order_id=? AND deleted_at IS NULL', (order['id'],)).fetchone()
            if not proc or proc['trace_id'] != body.get('trace_id'):
                raise Failure('invalid_request', 'Procurement trace mismatch')
            return match, Decimal(str(item['cost_price'])) * quantity
        finally:
            db.close()

    def create(self, body):
        with self.lock:
            entry, cost_limit = self.verify_paid_order(body)
            number, quantity = body['downstream_order_no'], body['quantity']
            identity = {'order': number, 'sku': body['sku_id'], 'quantity': quantity, 'plan': entry['plan_code']}
            fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
            with self.db() as db:
                row = db.execute('SELECT * FROM purchases WHERE order_no=?', (number,)).fetchone()
                if row and row['fingerprint'] != fingerprint:
                    raise Failure('idempotency_conflict', 'Order parameters changed; manual review required')
                if row and row['state'] == 'delivered':
                    return self.accepted(row)
                if row and row['state'] == 'manual_review':
                    raise Failure('manual_review', 'Purchase requires manual reconciliation')
                if row and time.time() - row['created'] > 43200:
                    raise Failure('manual_review', 'Unresolved purchase is older than 12 hours; reconcile before retrying')
                if not row:
                    product = next(p for p in self.products() if p['id'] == entry['product']['id'])
                    price = Decimal(product['price_amount'])
                    if product['skus'][0]['stock_quantity'] < quantity:
                        raise Failure('insufficient_balance', 'Insufficient upstream balance or plan unavailable')
                    if cost_limit <= 0 or price * quantity > cost_limit:
                        raise Failure('price_changed', 'Upstream price exceeds order cost snapshot; manual review required')
                    payload = {'plan_code':entry['plan_code'], 'count':quantity, 'prefix':'GPTPAYNOW',
                               'credit_quantity':0, 'batch_name':'GptPayNow '+number, 'note':'GptPayNow CDK delivery'}
                    idem = 'GPN-' + hashlib.sha256(number.encode()).hexdigest()
                    db.execute('INSERT INTO purchases(order_no,fingerprint,body,upstream_key,state,created,updated) VALUES (?,?,?,?,?,?,?)',
                               (number,fingerprint,json.dumps(payload,sort_keys=True),idem,'pending',time.time(),time.time()))
                    row = db.execute('SELECT * FROM purchases WHERE order_no=?', (number,)).fetchone()
            # Persist before the paid POST; lost responses always reuse the saved key AND body.
            result = self.request('POST', '/cdks/batches', json.loads(row['body']), row['upstream_key'])
            cards = result.get('items', [])
            codes = [c.get('cdk') for c in cards]
            valid = result.get('count') == quantity and len(cards) == quantity and all(isinstance(c,str) and c and '\n' not in c and '\r' not in c for c in codes)
            valid = valid and len(set(codes)) == quantity and all(c.get('plan_code') == entry['plan_code'] for c in cards)
            try:
                amount = Decimal(str(result['total_cost_cny']))
                valid = valid and amount.is_finite() and amount > 0 and amount <= cost_limit and bool(result.get('batch_id'))
            except (KeyError, ArithmeticError, ValueError):
                valid = False
                amount = Decimal(0)
            with self.db() as db:
                db.execute('UPDATE purchases SET state=?,payload=?,amount=?,batch_id=?,updated=? WHERE id=?',
                           ('delivered' if valid else 'manual_review', self.cipher.encrypt(json.dumps(result).encode()), str(amount), str(result.get('batch_id','')), time.time(),row['id']))
                updated = db.execute('SELECT * FROM purchases WHERE id=?',(row['id'],)).fetchone()
            if not valid:
                raise Failure('manual_review', 'Unexpected upstream purchase response; reconcile before retrying')
            return self.accepted(updated)

    @staticmethod
    def accepted(row):
        return {'ok':True,'order_id':row['id'],'order_no':'GPN-CDK-'+str(row['id']),
                'status':'delivered','amount':row['amount'],'currency':'CNY'}

    def order(self, number):
        with self.db() as db:
            row = db.execute('SELECT * FROM purchases WHERE id=?',(number,)).fetchone()
        if not row:
            raise Failure('order_not_found','No such procurement',404)
        if row['state'] != 'delivered':
            return {'order_id':number,'order_no':'GPN-CDK-'+str(number),'status':'pending','amount':'0.00','currency':'CNY'}
        data = json.loads(self.cipher.decrypt(row['payload']))
        return {**self.accepted(row),'refunded_amount':'0.00','fulfillment':{
            'type':'auto','status':'delivered','payload':'\n'.join(c['cdk'] for c in data['items']),
            'delivery_data':{},'delivered_at':datetime.fromtimestamp(row['updated'],timezone.utc).isoformat()}}


class Handler(BaseHTTPRequestHandler):
    server_version = 'GptPayNow-Bridge'
    def log_message(self, *args):
        pass  # No bodies, card codes, credentials or request URLs in logs.

    def handle_request(self):
        try:
            path = urllib.parse.urlsplit(self.path).path
            if path == '/health' and self.command == 'GET':
                return self.send_json(200, {'ok':True})
            if path == '/images/chatgpt.jpeg' and self.command == 'GET':
                data = Path('/app/chatgpt.jpeg').read_bytes()
                self.send_response(200); self.send_header('Content-Type','image/jpeg');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
            length = int(self.headers.get('Content-Length','0'))
            if not 0 <= length <= 65536:
                raise Failure('invalid_request','Request too large',413)
            raw = self.rfile.read(length)
            app = self.server.app
            app.authorize(self.command,path,self.headers,raw)
            if path == '/api/v1/upstream/ping' and self.command == 'POST':
                wallet = app.request('GET','/wallet')
                return self.send_json(200, {'ok':True,'site_name':'Autnine · 966qjy CDK','protocol_version':'1','user_id':0,'balance':str(wallet['available_cny']),'currency':'CNY'})
            if path == '/api/v1/upstream/categories' and self.command == 'GET':
                return self.send_json(200,{'ok':True,'categories':[{'id':1,'parent_id':0,'slug':'chatgpt','name':{'zh-CN':'ChatGPT','en-US':'ChatGPT','zh-TW':'ChatGPT'},'icon':'','sort_order':0}]})
            if path == '/api/v1/upstream/products' and self.command == 'GET':
                products = app.products()
                page = int(urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get('page',['1'])[0])
                return self.send_json(200,{'total':len(products),'items':products if page==1 else [],'includes_inactive':True})
            m = re.fullmatch(r'/api/v1/upstream/products/(\d+)',path)
            if m and self.command=='GET':
                product = next((p for p in app.products() if p['id']==int(m[1])),None)
                if product is None:raise Failure('product_not_found','Unknown product',404)
                return self.send_json(200,{'ok':True,'product':product})
            if path == '/api/v1/upstream/orders' and self.command == 'POST':
                return self.send_json(200,app.create(json.loads(raw)))
            m = re.fullmatch(r'/api/v1/upstream/orders/(\d+)',path)
            if m and self.command=='GET':
                return self.send_json(200,app.order(int(m[1])))
            raise Failure('not_supported','Operation not supported',404)
        except Failure as e:
            self.send_json(e.status,{'ok':False,'error_code':e.code,'error_message':e.message})
        except (ValueError,TypeError,KeyError):
            self.send_json(400,{'ok':False,'error_code':'invalid_request','error_message':'Invalid request'})
        except Exception:
            self.send_json(503,{'ok':False,'error_code':'bridge_unavailable','error_message':'Bridge unavailable; retry the same order'})

    def send_json(self, code, value):
        raw = json.dumps(value,ensure_ascii=False).encode()
        self.send_response(code); self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(raw)));self.end_headers()
        self.wfile.write(raw)

    do_GET = handle_request
    do_POST = handle_request


if __name__=='__main__':
    os.umask(0o077)
    secret = lambda name: Path('/run/secrets/'+name).read_text().strip()
    app = Bridge('/data/bridge.db','/shopdb/dujiao.db',json.loads(Path('/app/catalog.json').read_text()),secret('upstream_api_key'),secret('bridge_secret'),secret('storage_key'))
    server = ThreadingHTTPServer(('0.0.0.0',8080),Handler)
    server.app = app
    server.serve_forever()
