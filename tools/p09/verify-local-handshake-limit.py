"""Observe the existing HTTP handshake rate boundary on a new owned loopback host."""
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
RUN = "20260928T021243Z"
base = ROOT / "_local/p09/local-multiroom" / RUN / "server"
binding = json.loads((ROOT / "docs/p09/local-multiroom" / RUN / "run.json").read_text())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
assert {p.relative_to(base).as_posix(): sha(p) for p in base.rglob("*") if p.is_file()} == binding["serverFiles"]
private = ROOT / "_local/p09/handshake-limit-20260928"
private.mkdir(parents=True, exist_ok=False)
web = private / "empty-public"
web.mkdir()
output = ROOT / "docs/p09/local-multiroom/handshake-limit-20260928.json"
assert not output.exists()
with socket.socket() as reservation:
    reservation.bind(("127.0.0.1", 0))
    port = reservation.getsockname()[1]
origin = "http://127.0.0.1:" + str(port)
record = {"schema": 1, "passed": False, "boundServerRun": RUN, "serverFiles": binding["serverFiles"], "requests": [],
          "scope": "31 sequential non-upgrade HTTP requests to a fresh local multiplayer route; first30pass the limiter then return400 at the WebSocket check,31streturns429. No production configuration changed; no account, room or WebSocket created."}
server = None
try:
    with (private / "server.log").open("wb") as log:
        server = subprocess.Popen(["dotnet", str(base / "RacingBois.Server.Host.dll"), "--Port", str(port), "--AllowLan", "false", "--EnableTls", "false",
                                   "--RealmKind", "offline", "--DataRoot", str(private / "private-realm"), "--WebRoot", str(web), "--Logging:LogLevel:Default", "Warning"],
                                  cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        record["ownedServerPid"] = server.pid
        for attempt in range(100):
            assert server.poll() is None
            try:
                with urllib.request.urlopen(origin + "/ready", timeout=1) as ready:
                    assert ready.status == 200
                break
            except OSError:
                time.sleep(.1)
        else:
            raise RuntimeError("readiness_timeout")
        began = time.monotonic()
        for index in range(31):
            try:
                with urllib.request.urlopen(origin + "/multiplayer", timeout=3) as response:
                    status = response.status
            except urllib.error.HTTPError as error:
                status = error.code
                error.close()
            record["requests"].append({"index": index + 1, "status": status, "elapsedSeconds": time.monotonic() - began})
        record["passed"] = [x["status"] for x in record["requests"]] == [400] * 30 + [429] and record["requests"][-1]["elapsedSeconds"] < 60
finally:
    if server is not None:
        if server.poll() is None:
            server.terminate()
            server.wait(timeout=10)
        record["ownedServerExitCode"] = server.returncode
    record["recipeSha256"] = sha(Path(__file__))
    output.write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({"passed": record["passed"], "requests": len(record["requests"]), "lastStatus": record["requests"][-1]["status"] if record["requests"] else None}))
raise SystemExit(0 if record["passed"] else 1)
