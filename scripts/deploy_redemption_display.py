import hashlib
import json
import shlex
import sys
import time
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "deploy/autnine-bridge"))
from manage import connect, command

FILES = [
    "internal/modules/settings/application/site_normalize.go",
    "frontend/admin/src/views/admin/Settings.vue",
    "frontend/user/src/composables/useOrderDisplayHelpers.ts",
    "frontend/user/src/views/GuestOrderDetail.vue",
    "frontend/user/src/views/OrderDetail.vue",
    "frontend/user/src/i18n/locales/zh-CN.json",
    "frontend/user/src/i18n/locales/en-US.json",
    "frontend/user/src/i18n/locales/zh-TW.json",
]
REMOTE = "/opt/payforothers-18003"

ssh = connect()
try:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = "/opt/gptpaynow-backups/redemption-display-" + stamp
    data = json.dumps({"files": FILES, "backup": backup})
    script = """import json,os,shutil,sqlite3
from pathlib import Path
d=json.loads(%r)
os.umask(0o077)
b=Path(d["backup"])
b.mkdir(parents=True)
root=Path("/opt/payforothers-18003")
for n in d["files"]:
 s=root/n
 if s.is_file():
  t=b/"source"/n
  t.parent.mkdir(parents=True,exist_ok=True)
  shutil.copy2(s,t)
db=sqlite3.connect("file:/var/lib/docker/volumes/payforothers18003_app_db/_data/dujiao.db?mode=ro",uri=True)
t=sqlite3.connect(str(b/"before.db"))
db.backup(t)
t.close()
db.close()
""" % data
    command(ssh, "python3 -", script)
    dirs = sorted({str(PurePosixPath(REMOTE + "/" + f).parent) for f in FILES})
    command(ssh, "mkdir -p " + " ".join(shlex.quote(x) for x in dirs))
    with ssh.open_sftp() as sftp:
        for n in FILES:
            local = ROOT / n
            remote = REMOTE + "/" + n
            sftp.put(str(local), remote)
            with sftp.open(remote, "rb") as handle:
                if hashlib.sha256(handle.read()).digest() != hashlib.sha256(local.read_bytes()).digest():
                    raise RuntimeError("upload hash mismatch")
    job = "deploy-redemption-display-" + stamp
    shell = f"docker compose --project-name payforothers18003 -f docker-compose.production.yml up -d --build --no-deps app; result=$?; echo $result > {job}.exit; exit $result"
    command(ssh, f"cd {REMOTE}; nohup sh -c {shlex.quote(shell)} > {job}.log 2>&1 < /dev/null &")
    print(json.dumps({"job": job, "backup": backup}))
finally:
    ssh.close()
