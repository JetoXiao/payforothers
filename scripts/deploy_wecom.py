"""Scoped WeCom deployment. Never prints configuration or changes orders/payments."""
import hashlib
import json
import shlex
import sys
import time
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'deploy/autnine-bridge'))
from manage import connect,command,login,api

FILES=[
 'internal/constants/constants.go',
 'internal/modules/settings/schema/messaging/notification.go',
 'internal/modules/settings/schema/messaging/wecom.go',
 'internal/modules/settings/schema/messaging/wecom_test.go',
 'internal/modules/settings/transport/http/admin_handler.go',
 'internal/modules/settings/transport/http/admin_handler_test.go',
 'internal/modules/notification/contract/ports.go',
 'internal/modules/notification/application/service.go',
 'internal/modules/notification/application/dedupe.go',
 'internal/modules/notification/application/send.go',
 'internal/modules/notification/application/wecom.go',
 'internal/modules/notification/application/wecom_test.go',
 'internal/modules/notification/infrastructure/wecom/sender.go',
 'internal/modules/notification/infrastructure/wecom/sender_test.go',
 'internal/modules/notification/transport/http/admin_handler.go',
 'internal/modules/order/application/order_service.go',
 'internal/modules/order/application/order_wecom_test.go',
 'internal/modules/order/integrationtest/application/order_created_notification_test.go',
 'internal/app/container/services_integration.go',
 'internal/architecture/notification_service_structure_test.go',
 'frontend/admin/src/i18n/index.ts',
 'frontend/admin/src/i18n/wecom.ts',
 'frontend/admin/src/views/admin/Notifications.vue',
 'frontend/admin/src/views/admin/components/SettingsWeComCard.vue',
 'frontend/user/index.html',
 'frontend/user/public/llms.txt',
 'frontend/user/src/composables/usePageSeo.ts',
 'frontend/user/src/i18n/locales/zh-CN.json',
 'frontend/user/src/i18n/locales/zh-TW.json',
 'frontend/user/src/i18n/locales/en-US.json',
 'frontend/user/src/views/Home.vue',
 'internal/modules/sitemap/application/service.go',
]
REMOTE='/opt/payforothers-18003'

def deploy(ssh):
 stamp=time.strftime('%Y%m%d-%H%M%S')
 backup='/opt/gptpaynow-backups/wecom-'+stamp
 command(ssh,'python3 -', '''import json,os,sqlite3,shutil
from pathlib import Path
d=json.loads(%r)
os.umask(0o077)
backup=Path(d['backup']);backup.mkdir(parents=True)
root=Path('/opt/payforothers-18003')
for name in d['files']:
 source=root/name
 if source.is_file():
  dest=backup/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
db=sqlite3.connect('file:/var/lib/docker/volumes/payforothers18003_app_db/_data/dujiao.db?mode=ro',uri=True)
dest=sqlite3.connect(str(backup/'before.db'));db.backup(dest);dest.close();db.close()
(backup/'files.json').write_text(json.dumps(d['files']))
'''%json.dumps({'files':FILES,'backup':backup}))
 image=command(ssh,"docker inspect -f '{{.Image}}' payforothers18003-app-1").strip()
 rollback='payforothers18003-app:before-wecom-'+stamp
 command(ssh,'docker image tag '+shlex.quote(image)+' '+rollback)
 containers=command(ssh,"docker ps --format '{{.Names}} {{.ID}}'")
 dirs=sorted({str(PurePosixPath(REMOTE+'/'+f).parent) for f in FILES})
 command(ssh,'mkdir -p '+' '.join(shlex.quote(d) for d in dirs))
 with ssh.open_sftp() as sftp:
  for f in FILES:
   sftp.put(str(ROOT/f),REMOTE+'/'+f)
   with sftp.open(REMOTE+'/'+f,'rb') as remote:
    assert hashlib.sha256(remote.read()).digest()==hashlib.sha256((ROOT/f).read_bytes()).digest()
  with sftp.open(backup+'/containers-before.txt','w') as f:f.write(containers)
  with sftp.open(backup+'/rollback-image.txt','w') as f:f.write(rollback)
 job='deploy-wecom-'+stamp
 shell=f'docker compose --project-name payforothers18003 -f docker-compose.production.yml up -d --build --no-deps app; result=$?; echo $result > {job}.exit; exit $result'
 command(ssh,f'cd {REMOTE}; nohup sh -c {shlex.quote(shell)} > {job}.log 2>&1 < /dev/null &')
 print(json.dumps({'job':job,'backup':backup,'rollback':rollback,'files':len(FILES)}),flush=True)

def configure(ssh):
 # Input from stdin only; no webhook in source code, argv or printed output.
 data=json.load(sys.stdin)
 token=login(ssh)
 result=api(ssh,'PUT','/admin/settings/notification-center',{'channels':{'wecom':{'enabled':True,'webhook':data['webhook']}}},token)['data']
 w=result['channels']['wecom']
 assert w['enabled'] and w['has_webhook'] and w['webhook']==''
 print('WECOM_CONFIGURED_MASKED',flush=True)
 # A single explicit test, never creates an order or starts a purchase.
 result=api(ssh,'POST','/admin/settings/notification-center/test',{'channel':'wecom','target':'configured-group','scene':'order_created','locale':'zh-CN'},token)['data']
 assert result['sent']
 print('WECOM_TEST_ACCEPTED',flush=True)
 logs=api(ssh,'GET','/admin/settings/notification-center/logs?channel=wecom&is_test=true&page_size=1',token=token)['data']
 assert logs and logs[0]['status']=='success'
 generic=api(ssh,'GET','/admin/settings?key=notification_center_config',token=token)['data']
 assert generic['channels']['wecom']['webhook']==''
 public=api(ssh,'GET','/public/config')['data']
 assert data['webhook'] not in json.dumps(public) and 'wecom' not in public
 print(json.dumps({'test_log_id':logs[0]['id'],'status':logs[0]['status'],'generic_api_masked':True,'public_config_safe':True}),flush=True)

if __name__=='__main__':
 ssh=connect()
 try:
  if len(sys.argv)>1 and sys.argv[1]=='configure':configure(ssh)
  else:deploy(ssh)
 finally:ssh.close()
