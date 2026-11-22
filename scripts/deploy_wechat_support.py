"""Scoped deployment of the WeChat support UI and settings normalizer only."""
import hashlib
import json
import shlex
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'deploy/autnine-bridge'))
from manage import connect, command, api, login

FILES = [
    'internal/modules/settings/application/site_normalize.go',
    'internal/modules/settings/application/wechat_support_test.go',
    'frontend/admin/src/views/admin/Settings.vue',
    'frontend/admin/src/i18n/storefrontControls.ts',
    'frontend/user/src/utils/wechatSupport.ts',
    'frontend/user/src/composables/useWechatSupport.ts',
    'frontend/user/src/components/WechatSupport.vue',
    'frontend/user/src/views/Home.vue',
    'frontend/user/src/views/ProductDetail.vue',
    'frontend/user/src/templates/vault/ProductDetail.vue',
    'frontend/user/src/templates/vault/layout/VaultLayout.vue',
    'frontend/user/src/i18n/index.ts',
    'frontend/user/src/i18n/locales/wechat-zh-CN.json',
    'frontend/user/src/i18n/locales/wechat-zh-TW.json',
    'frontend/user/src/i18n/locales/wechat-en-US.json',
    'frontend/user/tests/wechatSupport.test.ts',
]
REMOTE = '/opt/payforothers-18003'

def deploy(ssh):
    stamp = time.strftime('%Y%m%d-%H%M%S')
    backup = '/opt/gptpaynow-backups/wechat-' + stamp
    payload = json.dumps({'files': FILES, 'backup': backup})
    source_backup = '''import os,json,sqlite3,shutil
from pathlib import Path
data=json.loads(%r)
os.umask(0o077)
root=Path('/opt/payforothers-18003'); backup=Path(data['backup']);backup.mkdir(parents=True)
for name in data['files']:
 p=root/name
 if p.is_file():
  dest=backup/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
db=sqlite3.connect('file:/var/lib/docker/volumes/payforothers18003_app_db/_data/dujiao.db?mode=ro',uri=True)
dest=sqlite3.connect(str(backup/'before.db'));db.backup(dest);dest.close();db.close()
(backup/'files.json').write_text(json.dumps(data['files']))
''' % payload
    command(ssh, 'python3 -', source_backup)
    image_id = command(ssh, "docker inspect -f '{{.Image}}' payforothers18003-app-1").strip()
    rollback = 'payforothers18003-app:before-wechat-' + stamp
    command(ssh, f'docker image tag {shlex.quote(image_id)} {rollback}')
    before = command(ssh, "docker ps --format '{{.Names}} {{.ID}}'")
    with ssh.open_sftp() as sftp:
        for name in FILES:
            path = ROOT/name
            sftp.put(str(path), REMOTE+'/'+name)
            with sftp.open(REMOTE+'/'+name, 'rb') as f:
                assert hashlib.sha256(f.read()).digest() == hashlib.sha256(path.read_bytes()).digest()
        with sftp.open(backup+'/containers-before.txt', 'w') as f: f.write(before)
        with sftp.open(backup+'/rollback-image.txt', 'w') as f: f.write(rollback)
    job = 'deploy-wechat-' + stamp
    shell = f'docker compose --project-name payforothers18003 -f docker-compose.production.yml up -d --build --no-deps app; result=$?; echo $result > {job}.exit; exit $result'
    command(ssh, f'cd {REMOTE}; nohup sh -c {shlex.quote(shell)} > {job}.log 2>&1 < /dev/null &')
    print(json.dumps({'job': job, 'backup': backup, 'rollback': rollback, 'files': len(FILES)}), flush=True)

def initialize(ssh):
    token = login(ssh)
    before = api(ssh, 'GET', '/admin/settings?key=site_config', token=token)['data']
    contact = before.setdefault('contact', {})
    if 'wechat' not in contact:
        # Existing support ID was explicitly provided by the operator earlier.
        contact['wechat'] = ['think-more-9']
        api(ssh, 'PUT', '/admin/settings', {'key': 'site_config', 'value': before}, token=token)
    after = api(ssh, 'GET', '/admin/settings?key=site_config', token=token)['data']
    public = api(ssh, 'GET', '/public/config')['data']
    assert after['contact']['wechat'] == public['contact']['wechat']
    print('WECHAT_CONFIG', public['contact']['wechat'], flush=True)

if __name__ == '__main__':
    ssh = connect()
    try:
        if len(sys.argv) > 1 and sys.argv[1] == 'initialize': initialize(ssh)
        else: deploy(ssh)
    finally: ssh.close()
