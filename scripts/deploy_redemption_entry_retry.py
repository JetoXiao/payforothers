import hashlib,json,shlex,sys,time
from pathlib import Path, PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'deploy/autnine-bridge'))
from manage import connect,command
REMOTE='/opt/payforothers-18003'
FILES=['frontend/user/src/utils/content.ts','frontend/user/src/views/ProductDetail.vue','frontend/user/src/templates/vault/ProductDetail.vue','frontend/user/src/components/Navbar.vue','frontend/user/src/templates/vault/layout/VaultLayout.vue','frontend/user/src/i18n/locales/zh-CN.json','frontend/user/src/i18n/locales/zh-TW.json','frontend/user/src/i18n/locales/en-US.json']
ssh=connect()
try:
 stamp=time.strftime('%Y%m%d-%H%M%S'); backup=f'/opt/gptpaynow-backups/redemption-entry-{stamp}'
 payload=json.dumps({'files':FILES,'backup':backup})
 script='''import json,os,shutil,sqlite3\nfrom pathlib import Path\nd=json.loads(%r)\nos.umask(0o077)\nb=Path(d['backup']); b.mkdir(parents=True)\nroot=Path('/opt/payforothers-18003')\nfor n in d['files']:\n s=root/n\n if s.is_file():\n  t=b/'source'/n; t.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(s,t)\ndb=sqlite3.connect('file:/var/lib/docker/volumes/payforothers18003_app_db/_data/dujiao.db?mode=ro',uri=True)\ndest=sqlite3.connect(str(b/'before.db')); db.backup(dest); dest.close(); db.close()\n''' % payload
 print(command(ssh,'python3 -',script))
 image_id=command(ssh,"docker inspect -f '{{.Image}}' payforothers18003-app-1").strip(); rollback=f'payforothers18003-app:before-redemption-entry-{stamp}'
 command(ssh,f'docker image tag {shlex.quote(image_id)} {shlex.quote(rollback)}')
 dirs=sorted({str(PurePosixPath(REMOTE,f).parent) for f in FILES}); command(ssh,'mkdir -p '+' '.join(shlex.quote(x) for x in dirs))
 with ssh.open_sftp() as sftp:
  for name in FILES:
   local=ROOT/name; remote=REMOTE+'/'+name; sftp.put(str(local),remote)
   with sftp.open(remote,'rb') as h:
    assert hashlib.sha256(h.read()).digest()==hashlib.sha256(local.read_bytes()).digest(),name
 job=f'deploy-redemption-entry-{stamp}'; shell=f'docker compose --project-name payforothers18003 -f docker-compose.production.yml up -d --build --no-deps app; result=$?; echo $result > {job}.exit; exit $result'
 command(ssh,f'cd {REMOTE}; nohup sh -c {shlex.quote(shell)} > {job}.log 2>&1 < /dev/null &')
 print(json.dumps({'job':job,'backup':backup,'rollback':rollback,'files':len(FILES)}))
finally: ssh.close()
