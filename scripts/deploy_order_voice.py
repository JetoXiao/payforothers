"""Deploy only admin order-voice code and static audio; no settings/DB writes."""
import hashlib
import json
import shlex
import sys
import time
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'deploy/autnine-bridge'))
from manage import connect,command

FILES=[
 'frontend/admin/src/layouts/AdminLayout.vue',
 'frontend/admin/src/i18n/index.ts',
 'frontend/admin/src/i18n/orderVoice.ts',
 'frontend/admin/src/components/OrderVoiceControl.vue',
 'frontend/admin/src/composables/useOrderVoice.ts',
 'frontend/admin/src/utils/orderVoice.ts',
 'frontend/admin/src/utils/orderVoice.test.ts',
 'frontend/admin/src/api/orderVoice.ts',
 'frontend/admin/src/api/orderVoice.test.ts',
]+['frontend/admin/src/assets/audio/'+name for name in ['new-order-zh.wav','order-voice-enabled-zh.wav','new-order-en.wav','order-voice-enabled-en.wav']]
REMOTE='/opt/payforothers-18003'

def main():
 ssh=connect()
 try:
  stamp=time.strftime('%Y%m%d-%H%M%S')
  backup='/opt/gptpaynow-backups/order-voice-'+stamp
  data=json.dumps({'files':FILES,'backup':backup})
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
'''%data)
  image=command(ssh,"docker inspect -f '{{.Image}}' payforothers18003-app-1").strip()
  rollback='payforothers18003-app:before-order-voice-'+stamp
  command(ssh,'docker image tag '+shlex.quote(image)+' '+rollback)
  containers=command(ssh,"docker ps --format '{{.Names}} {{.ID}}'")
  directories=sorted({str(PurePosixPath(REMOTE+'/'+f).parent) for f in FILES})
  command(ssh,'mkdir -p '+' '.join(shlex.quote(d) for d in directories))
  with ssh.open_sftp() as sftp:
   for f in FILES:
    sftp.put(str(ROOT/f),REMOTE+'/'+f)
    with sftp.open(REMOTE+'/'+f,'rb') as remote:
     assert hashlib.sha256(remote.read()).digest()==hashlib.sha256((ROOT/f).read_bytes()).digest()
   with sftp.open(backup+'/containers-before.txt','w') as f:f.write(containers)
   with sftp.open(backup+'/rollback-image.txt','w') as f:f.write(rollback)
  job='deploy-order-voice-'+stamp
  shell=f'docker compose --project-name payforothers18003 -f docker-compose.production.yml up -d --build --no-deps app; result=$?; echo $result > {job}.exit; exit $result'
  command(ssh,f'cd {REMOTE}; nohup sh -c {shlex.quote(shell)} > {job}.log 2>&1 < /dev/null &')
  print(json.dumps({'job':job,'backup':backup,'rollback':rollback,'files':len(FILES)}),flush=True)
 finally:ssh.close()

if __name__=='__main__':main()
