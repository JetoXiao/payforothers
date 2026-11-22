import hashlib
import hmac
import json
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from cryptography.fernet import Fernet
from bridge import Bridge, Failure

class BridgeTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        root=Path(self.temp.name)
        self.shop=root/'shop.db'
        with sqlite3.connect(self.shop) as db:
            db.executescript('''
            CREATE TABLE orders(id INTEGER,order_no TEXT,status TEXT,paid_at TEXT,refunded_amount TEXT,deleted_at TEXT);
            CREATE TABLE order_items(order_id INTEGER,product_id INTEGER,sku_id INTEGER,quantity INTEGER,fulfillment_type TEXT,cost_price TEXT,deleted_at TEXT);
            CREATE TABLE sku_mappings(local_sku_id INTEGER,product_mapping_id INTEGER,upstream_sku_id INTEGER,deleted_at TEXT);
            CREATE TABLE product_mappings(id INTEGER,local_product_id INTEGER,upstream_product_id INTEGER,connection_id INTEGER,is_active INTEGER,deleted_at TEXT);
            CREATE TABLE site_connections(id INTEGER,base_url TEXT,status TEXT,deleted_at TEXT);
            CREATE TABLE procurement_orders(local_order_id INTEGER,trace_id TEXT,deleted_at TEXT);
            INSERT INTO orders VALUES(1,'ORDER-TEST-001','paid','2026-10-08','0',NULL);
            INSERT INTO order_items VALUES(1,7,17,1,'upstream','35.00',NULL);
            INSERT INTO sku_mappings VALUES(17,1,5,NULL);
            INSERT INTO product_mappings VALUES(1,7,5,1,1,NULL);
            INSERT INTO site_connections VALUES(1,'http://autnine-bridge:8080','active',NULL);
            INSERT INTO procurement_orders VALUES(1,'TRACE-001',NULL);
            ''')
        db.close()
        self.catalog=[{'plan_code':'GO','country':'EG','product':{'id':5,'price_amount':'35.00','skus':[{'id':5}]}}]
        self.key=Fernet.generate_key()
        self.app=Bridge(root/'bridge.db',self.shop,self.catalog,'TEST-KEY','shared',self.key)
        self.posts=[]
        self.plan_price=35
        self.response={'count':1,'batch_id':'TEST-BATCH','total_cost_cny':35,'items':[{'cdk':'TEST-CODE-NOT-REAL','plan_code':'GO'}]}
        def request(method,path,body=None,idem=None):
            if path=='/plans':return [{'code':'GO','country':'EG','product_type':'subscription','unit_price_cny':self.plan_price,'can_generate':True}]
            if path=='/wallet':return {'available_cny':100,'currency':'CNY'}
            self.posts.append((body,idem))
            return self.response
        self.app.request=request
        self.body={'sku_id':5,'quantity':1,'downstream_order_no':'ORDER-TEST-001','trace_id':'TRACE-001'}

    def tearDown(self):self.temp.cleanup()
    def assertFailure(self, body, code):
        with self.assertRaises(Failure) as e:self.app.create(body)
        self.assertEqual(e.exception.code,code)

    def test_paid_delivery_and_idempotency(self):
        first=self.app.create(self.body);second=self.app.create(self.body)
        self.assertEqual(first,second);self.assertEqual(len(self.posts),1)
        detail=self.app.order(first['order_id'])
        self.assertEqual(detail['fulfillment']['payload'],'TEST-CODE-NOT-REAL')
        with self.app.db() as db:
            self.assertNotIn(b'TEST-CODE',db.execute('SELECT payload FROM purchases').fetchone()[0])

    def test_unpaid_rejected_without_purchase(self):
        with sqlite3.connect(self.shop) as db:db.execute("UPDATE orders SET status='pending_payment',paid_at=NULL")
        db.close()
        self.assertFailure(self.body,'order_unpaid');self.assertFalse(self.posts)

    def test_quantity_trace_and_credentials_rejected(self):
        for body in [{**self.body,'quantity':2},{**self.body,'trace_id':'WRONG'},{**self.body,'manual_form_data':{'session':'secret'}}]:
            self.assertFailure(body,'invalid_request')
        self.assertFalse(self.posts)

    def test_cost_increase_rejected(self):
        self.plan_price=40
        self.assertFailure(self.body,'price_changed');self.assertFalse(self.posts)

    def test_wrong_response_quarantined(self):
        self.response['items'][0]['plan_code']='PLUS'
        self.assertFailure(self.body,'manual_review')
        self.assertFailure(self.body,'manual_review');self.assertEqual(len(self.posts),1)

    def test_timeout_retries_same_body_and_key_after_restart(self):
        original=self.app.request
        def timeout(method,path,body=None,idem=None):
            if method=='POST':
                self.posts.append((body,idem));raise Failure('upstream_unavailable','timeout',503)
            return original(method,path,body,idem)
        self.app.request=timeout
        self.assertFailure(self.body,'upstream_unavailable')
        self.app=Bridge(self.app.state,self.shop,self.catalog,'TEST-KEY','shared',self.key)
        self.app.request=original
        self.app.create(self.body)
        self.assertEqual(self.posts[0],self.posts[1])

    def test_auth_invalid_and_stale(self):
        raw=b'{}';ts=int(time.time());path='/api/v1/upstream/orders'
        signature=hmac.new(b'shared',f'POST\n{path}\n{ts}\n{hashlib.md5(raw).hexdigest()}'.encode(),hashlib.sha256).hexdigest()
        headers={'Dujiao-Next-Api-Key':'gptpaynow-autnine','Dujiao-Next-Timestamp':str(ts),'Dujiao-Next-Signature':signature}
        self.app.authorize('POST',path,headers,raw)
        with self.assertRaises(Failure):self.app.authorize('POST',path,headers,b'{"x":1}')
        headers['Dujiao-Next-Timestamp']='1'
        with self.assertRaises(Failure):self.app.authorize('POST',path,headers,raw)

    def test_region_change_hides_inventory(self):
        self.catalog[0]['country']='IN'
        self.assertEqual(self.app.products()[0]['skus'][0]['stock_quantity'],0)

    def test_pro_catalog_routes_to_matching_plan_and_delivers_once(self):
        catalog=json.loads(Path(__file__).with_name('catalog.json').read_text(encoding='utf-8'))
        for pid,sku,local,plan,country,price in [(2,2,9,'PRO5X','EG',610),(19,22,15,'PRO5X_IOS','US',605)]:
            with self.subTest(plan=plan):
                entry=next(x for x in catalog if x['product']['id']==pid)
                self.assertEqual((entry['plan_code'],entry['country']),(plan,country))
                self.assertEqual([s['id'] for s in entry['product']['skus']],[sku])
                self.app.catalog=[entry]
                number='ORDER-TEST-'+plan
                with sqlite3.connect(self.shop) as db:
                    db.execute('UPDATE orders SET order_no=?',(number,))
                    db.execute('UPDATE order_items SET product_id=?,sku_id=?,cost_price=?',(local,local,str(price)))
                    db.execute('UPDATE product_mappings SET local_product_id=?,upstream_product_id=?',(local,pid))
                    db.execute('UPDATE sku_mappings SET local_sku_id=?,upstream_sku_id=?',(local,sku))
                db.close()
                posts=[]
                def request(method,path,body=None,idem=None):
                    if path=='/plans':return [{'code':plan,'country':country,'product_type':'subscription','unit_price_cny':price,'can_generate':True}]
                    if path=='/wallet':return {'available_cny':2200,'currency':'CNY'}
                    self.assertEqual((method,path),('POST','/cdks/batches'))
                    self.assertEqual(body['plan_code'],plan)
                    posts.append((body,idem))
                    return {'count':1,'batch_id':'TEST-'+plan,'total_cost_cny':price,'items':[{'cdk':'TEST-NOT-REAL-'+plan,'plan_code':plan}]}
                self.app.request=request
                body={**self.body,'sku_id':sku,'downstream_order_no':number}
                first=self.app.create(body)
                self.assertEqual(self.app.create(body),first)
                self.assertEqual(len(posts),1)
                fulfillment=self.app.order(first['order_id'])['fulfillment']
                self.assertEqual(fulfillment['status'],'delivered')
                self.assertEqual(fulfillment['payload'],'TEST-NOT-REAL-'+plan)

if __name__=='__main__':unittest.main()
