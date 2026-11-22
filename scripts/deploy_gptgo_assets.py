"""Deploy only the generated Go asset and its update helper, with a read-only backup."""
import hashlib
import json
import shlex
import sys
import time
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "deploy/autnine-bridge"))
from manage import connect, command

FILES = ["scripts/update_gptgo_assets.py", "output/imagegen/gptpaynow-gptgo-20261009/gptgo.png"]
REMOTE = "/opt/payforothers-18003"

ssh = connect()
try:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = f"/opt/gptpaynow-backups/gptgo-assets-{stamp}"
    data = json.dumps({"files": FILES, "backup": backup})
    script = '''import json,os,shutil,sqlite3
from pathlib import Path
d=json.loads(%r); os.umask(0o077); b=Path(d["backup"]); b.mkdir(parents=True)
root=Path("/opt/payforothers-18003")
for name in d["files"]:
 src=root/name
 if src.is_file():
  dst=b/"source"/name; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
db=sqlite3.connect("file:/var/lib/docker/volumes/payforothers18003_app_db/_data/dujiao.db?mode=ro",uri=True)
dst=sqlite3.connect(str(b/"before.db")); db.backup(dst); dst.close(); db.close()
''' % data
    command(ssh, "python3 -", script)
    dirs = sorted({str(PurePosixPath(REMOTE + "/" + f).parent) for f in FILES})
    command(ssh, "mkdir -p " + " ".join(shlex.quote(x) for x in dirs))
    with ssh.open_sftp() as sftp:
        for name in FILES:
            local = ROOT / name
            remote = REMOTE + "/" + name
            sftp.put(str(local), remote)
            with sftp.open(remote, "rb") as remote_file:
                if hashlib.sha256(remote_file.read()).digest() != hashlib.sha256(local.read_bytes()).digest():
                    raise RuntimeError("upload hash mismatch")
    job = "deploy-gptgo-assets-" + stamp
    shell = f"docker compose --project-name payforothers18003 -f docker-compose.production.yml up -d --build --no-deps app; result=$?; echo $result > {job}.exit; exit $result"
    command(ssh, f"cd {REMOTE}; nohup sh -c {shlex.quote(shell)} > {job}.log 2>&1 < /dev/null &")
    print(json.dumps({"job": job, "backup": backup, "files": len(FILES)}))
finally:
    ssh.close()
