"""Verify freshly published P07 hosts and create immutable release archives.

Run only after publishing both runtimes and starting the packaged Windows host.
This tool never launches a server, copies player data, changes trust/firewalls, or contacts OCI.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import struct
import subprocess
import tarfile
import urllib.request
from urllib.parse import urlparse
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs/p07/backend"
SOURCE_ROOTS = (
    "src", "Packages", "tools/foundation", "tools/p05", "tools/p07",
    "Assets/RacingBois/Client", "Assets/RacingBois/UI", "Assets/WebGLTemplates", "ProjectSettings",
)
CODE_SUFFIXES = {".cs", ".csproj", ".props", ".targets", ".json", ".asmdef", ".ps1", ".py", ".js", ".jslib", ".html", ".css", ".uss", ".uxml", ".bat", ".sh"}
RECIPE_ONLY = {"tools/p07/package-release.py", "tools/p07/VALIDATION.md"}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def relative(path):
    return path.resolve().relative_to(ROOT).as_posix()


def artifact(path):
    return {"path": relative(path), "bytes": path.stat().st_size, "sha256": sha(path)}


def list_files(folder):
    require(folder.is_dir(), f"Required directory missing: {relative(folder)}")
    resolved = folder.resolve()
    result = []
    for path in sorted(folder.rglob("*")):
        require(not path.is_symlink() and not getattr(path, "is_junction", lambda: False)(),
                f"Links are not allowed in release payload: {path.relative_to(folder)}")
        require(path.resolve().is_relative_to(resolved), "Release path escaped its directory.")
        if path.is_file():
            result.append(path)
    return result


def manifest_entries(folder, paths):
    return [{"path": path.relative_to(folder).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path)} for path in paths]


def source_file(path):
    return path.startswith("ProjectSettings/") or Path(path).suffix.lower() in CODE_SUFFIXES


def verify_source(commit):
    require(re.fullmatch(r"[0-9a-fA-F]{7,40}", commit) is not None, "--commit must be a Git commit hash, 7-40 hexadecimal characters.")
    full = subprocess.check_output(["git", "rev-parse", "--verify", commit + "^{commit}"], cwd=ROOT, text=True).strip()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    changed = subprocess.check_output(["git", "diff", "--name-only", full, head, "--", *SOURCE_ROOTS], cwd=ROOT, text=True).splitlines()
    require(not any(path not in RECIPE_ONLY for path in changed),
            "Runtime or build inputs changed since the selected package commit; publish from the new source instead.")
    dirty = subprocess.check_output(["git", "status", "--porcelain=v1", "--untracked-files=all", "-z", "--", *SOURCE_ROOTS], cwd=ROOT).decode("utf-8").split("\0")
    require(not any(source_file(line[3:].replace("\\", "/")) for line in dirty if line),
            "Runtime/build source is dirty or untracked. Commit the actual release source before packaging.")
    tracked = subprocess.check_output(["git", "ls-files", "-z", "--", *SOURCE_ROOTS], cwd=ROOT).decode("utf-8").split("\0")
    source = []
    for name in sorted(path for path in tracked if path and path not in RECIPE_ONLY and source_file(path)):
        path = ROOT / name
        require(path.is_file(), f"Tracked release source missing: {name}")
        source.append(artifact(path))
    return full, head, source


def reject_private_content(package):
    private_directories = {"data", "realm-data", "player-data", "backups", "backup", ".ssh", "_local"}
    for path in package.rglob("*"):
        rel = path.relative_to(package)
        lower_parts = [part.lower() for part in rel.parts]
        name = path.name.lower()
        require(not any(part in private_directories for part in lower_parts), f"Private data directory in package: {rel}")
        require(not any("_donotship" in part for part in lower_parts), f"Unity debug payload in package: {rel}")
        require(not (name.startswith("realm.json") or name.startswith("realm.sqlite") or name == "realm.lock" or
                     re.search(r"\.(?:sqlite3?|db)(?:-(?:wal|shm|journal)|\.(?:bak|backup|old))?$", name)),
                f"Private database/realm file in package: {rel}")
        require(path.suffix.lower() not in {".pfx", ".p12", ".pem", ".key"} and
                name not in {"credentials.json", "secrets.json", "id_ed25519", "id_rsa", "lan_join.html"},
                f"Credential or machine-specific file in package: {rel}")


def elf_aarch64(path):
    with path.open("rb") as stream:
        header = stream.read(64)
    require(len(header) == 64 and header[:6] == b"\x7fELF\x02\x01" and struct.unpack_from("<H", header, 18)[0] == 183,
            f"Expected ELF64 little-endian AArch64 binary: {relative(path)}")
    return artifact(path)


def pe_x64(path):
    with path.open("rb") as stream:
        header = stream.read(64)
        require(len(header) == 64 and header[:2] == b"MZ", f"Expected PE binary: {relative(path)}")
        stream.seek(struct.unpack_from("<I", header, 60)[0])
        signature = stream.read(6)
    require(signature[:4] == b"PE\0\0" and struct.unpack_from("<H", signature, 4)[0] == 0x8664,
            f"Expected native x64 PE binary: {relative(path)}")
    return artifact(path)


def require_self_contained(package, rid):
    runtime = read_json(package / "RacingBois.Server.Host.runtimeconfig.json")["runtimeOptions"]
    require(runtime.get("includedFrameworks") and not runtime.get("framework") and not runtime.get("frameworks"),
            f"Runtime is not self-contained: {rid}")
    require(rid in read_json(package / "RacingBois.Server.Host.deps.json")["runtimeTarget"]["name"], f"Runtime target mismatch: {rid}")
    for name in ("README-P07.md", "web/index.html", "RacingBois.Server.Host.dll", "Microsoft.Data.Sqlite.dll"):
        require((package / name).is_file(), f"Missing P07 payload: {rid}/{name}")


def native_self_test(windows):
    command = subprocess.run([str(windows / "RacingBois.Server.Host.exe"), "--SelfTest"], cwd=windows,
                             capture_output=True, text=True, timeout=30, check=False)
    # Never forward arbitrary stdout/stderr: a failed host can print configuration or runtime diagnostics.
    require(command.returncode == 0, "Packaged Windows SelfTest failed; inspect its controlled invocation separately.")
    result = json.loads(command.stdout)
    require(result.get("status") == "PASS" and result.get("sqliteNativeRollback") is True and
            result.get("multiplayerProtocolRoundtrip") == 3 and result.get("architecture") == "X64",
            "Packaged SelfTest lacks required P07 native SQLite rollback/protocol/x64 proof.")
    fields = ("status", "architecture", "framework", "ticks", "distanceMillimeters", "speedMillimetersPerSecond",
              "protocolRoundtrip", "raceProtocolRoundtrip", "raceTick", "raceDistanceMillimeters", "multiplayerProtocolRoundtrip",
              "exactTickInputSmoke", "sqliteNativeRollback", "scope")
    return {key: result[key] for key in fields if key in result}


def verify_live_delivery(windows, web_manifest):
    session = read_json(ROOT / "_local/p07-server-session.json")
    origins = []
    for field, scheme in (("httpUrl", "http"), ("httpsUrl", "https")):
        value = session.get(field, "")
        parsed = urlparse(value)
        require(parsed.scheme == scheme and parsed.hostname in {"localhost", "127.0.0.1", "::1"} and parsed.port
                and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment
                and parsed.path in {"", "/"}, "Live URLs must be explicit credential-free loopback base URLs.")
        origins.append(value.rstrip("/") + "/")
    http_origin, https_origin = origins
    require(Path(session["exe"]).resolve() == (windows / "RacingBois.Server.Host.exe").resolve(), "P07 session does not run the final packaged executable.")
    require(Path(session["webRoot"]).resolve() == (windows / "web").resolve(), "P07 session does not serve the final packaged web root.")
    data = Path(session["dataRoot"]).resolve()
    require(data.is_relative_to(ROOT / "_local") and data.relative_to(ROOT / "_local").parts[0].lower().startswith("p07-"),
            "P07 live verification requires its own _local/p07-* private data root.")
    require(not data.is_relative_to(windows) and not data.is_relative_to(windows / "web"), "Private live data must stay outside the immutable package.")
    pid = int(session["pid"])
    require(pid > 0, "Invalid P07 session PID.")
    script = f"$p = Get-Process -Id {pid} -ErrorAction Stop; @{{pid=$p.Id;exe=$p.Path;startTimeUtc=$p.StartTime.ToUniversalTime().ToString('o')}} | ConvertTo-Json -Compress"
    process = json.loads(subprocess.check_output(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script], text=True))
    require(Path(process["exe"]).resolve() == Path(session["exe"]).resolve(), "P07 process identity changed.")
    expected_time = dt.datetime.fromisoformat(session["startTimeUtc"].replace("Z", "+00:00"))
    actual_time = dt.datetime.fromisoformat(process["startTimeUtc"].replace("Z", "+00:00"))
    require(abs((expected_time - actual_time).total_seconds()) < 1, "P07 process start time no longer matches its session record.")
    with urllib.request.urlopen(https_origin + "multiplayer/health", timeout=10) as response:
        health = json.loads(response.read())
    require(health.get("protocolVersion") == 3 and health.get("profilePersistence") is True, "P07 live multiplayer health failed.")
    headers = []
    for entry in (item for item in web_manifest if item["path"].endswith(".gz")):
        for origin in (http_origin, https_origin):
            url = origin + entry["path"]
            with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=30) as response:
                item = {"url": url, "status": response.status, "contentType": response.headers["Content-Type"],
                        "contentEncoding": response.headers["Content-Encoding"], "contentLength": int(response.headers["Content-Length"]),
                        "certificateValidation": "Ordinary OS trust; no bypass" if origin.startswith("https") else "N/A: plaintext LAN HTTP",
                        "method": "GET, raw compressed bytes SHA-256 checked"}
                digest = hashlib.sha256()
                for chunk in iter(lambda: response.read(1024 * 1024), b""):
                    digest.update(chunk)
            require(item["status"] == 200 and item["contentEncoding"] == "gzip" and item["contentLength"] == entry["bytes"], "Live gzip response headers mismatch.")
            mime = "application/wasm" if ".wasm." in entry["path"] else "text/javascript" if ".js." in entry["path"] else "application/octet-stream"
            require(item["contentType"].startswith(mime), "Live gzip payload MIME mismatch.")
            require(digest.hexdigest() == entry["sha256"], "Live HTTP payload is not the exact selected Web build.")
            item["sha256"] = digest.hexdigest()
            headers.append(item)
    require(len(headers) >= 6, "Expected at least data/framework/wasm gzip payloads through both HTTP and HTTPS.")
    return {"url": https_origin, "httpUrl": http_origin, "multiplayerEndpoint": https_origin.replace("https://", "wss://", 1) + "multiplayer", "pid": pid,
            "exe": relative(Path(session["exe"])), "webRoot": relative(Path(session["webRoot"])),
            "privateDataRoot": relative(data), "startTimeUtc": process["startTimeUtc"], "bind": "loopback only",
            "health": health}, headers


def tar_permissions(member):
    member.uid = member.gid = 0
    member.uname = member.gname = ""
    name = Path(member.name).name
    member.mode = 0o755 if member.isdir() or name in {"RacingBois.Server.Host", "createdump", "launch-local.sh", "launch-lan.sh"} else 0o644
    return member


def make_archives(windows, arm, win_zip, arm_tar):
    win_zip.parent.mkdir(parents=True, exist_ok=True)
    win_files, arm_files = list_files(windows), list_files(arm)
    with zipfile.ZipFile(win_zip, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in win_files:
            archive.write(path, path.relative_to(windows).as_posix())
    with zipfile.ZipFile(win_zip) as archive:
        require(archive.testzip() is None, "ZIP CRC verification failed.")
        expected = {path.relative_to(windows).as_posix(): path for path in win_files}
        require(len(archive.namelist()) == len(expected) and set(archive.namelist()) == set(expected), "ZIP file set mismatch or duplicate entries.")
        for name, path in expected.items():
            require(hashlib.sha256(archive.read(name)).hexdigest() == sha(path), f"ZIP hash mismatch: {name}")
    with tarfile.open(arm_tar, "x:gz", compresslevel=6) as archive:
        archive.add(arm, arcname=".", filter=tar_permissions)
    with tarfile.open(arm_tar, "r:gz") as archive:
        raw_members = [member for member in archive.getmembers() if member.isfile()]
        members = {member.name.removeprefix("./"): member for member in raw_members}
        expected = {path.relative_to(arm).as_posix(): path for path in arm_files}
        require(len(raw_members) == len(members) and set(members) == set(expected), "TAR file set mismatch or duplicate entries.")
        for name, path in expected.items():
            with archive.extractfile(members[name]) as stream:
                require(hashlib.sha256(stream.read()).hexdigest() == sha(path), f"TAR hash mismatch: {name}")
        require(all(members[name].mode == 0o755 for name in ("RacingBois.Server.Host", "launch-local.sh", "launch-lan.sh")), "ARM launcher executable permissions missing.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--web-root", required=True)
    args = parser.parse_args()
    commit = args.commit.lower()
    full_commit, recipe_commit, source_files = verify_source(commit)
    web = (ROOT / args.web_root).resolve()
    require(web.is_relative_to(ROOT / "Build"), "Selected Web root must be under this project's Build directory.")
    windows = ROOT / f"Build/LanHost/win-x64-p07-{commit}"
    arm = ROOT / f"Build/LanHost/linux-arm64-p07-{commit}"
    win_zip = ROOT / f"Build/Packages/RacingBois-P07-win-x64-{commit}.zip"
    arm_tar = ROOT / f"Build/Packages/RacingBois-P07-linux-arm64-{commit}.tar.gz"
    require(not win_zip.exists() and not arm_tar.exists(), "Archive already exists. Use a fresh release; archives are never overwritten.")
    require(not (EVIDENCE / "delivery.json").exists(), "Existing delivery receipt must be archived explicitly before producing another release.")
    web_files = [path for path in list_files(web) if not any("_donotship" in part.lower() for part in path.relative_to(web).parts)]
    web_manifest = manifest_entries(web, web_files)
    unity_receipt = read_json(ROOT / "docs/p07/unity/build.json")
    unity_commit = subprocess.check_output(["git", "rev-parse", "--verify", unity_receipt["runtimeCommit"] + "^{commit}"], cwd=ROOT, text=True).strip()
    require(unity_commit == full_commit and unity_receipt["output_path"] == relative(web)
            and unity_receipt["result"] == "succeeded" and unity_receipt["errors"] == 0
            and unity_receipt["totalBytes"] == sum(item["bytes"] for item in web_manifest), "Unity receipt/source/payload binding mismatch.")
    require("index.html" in {item["path"] for item in web_manifest}, "Complete Unity Web output is required.")
    for package, rid in ((windows, "win-x64"), (arm, "linux-arm64")):
        require_self_contained(package, rid)
        reject_private_content(package)
        packaged_web = {path.relative_to(package / "web").as_posix(): path for path in list_files(package / "web")}
        require(set(packaged_web) == {item["path"] for item in web_manifest}, f"Packaged Web file set mismatch: {rid}")
        for entry in web_manifest:
            require(sha(packaged_web[entry["path"]]) == entry["sha256"], f"Packaged Web hash mismatch: {rid}/{entry['path']}")
    for path in (windows / "RacingBois.Server.Host.exe", windows / "e_sqlite3.dll"):
        pe_x64(path)
    arm_binaries = [elf_aarch64(arm / name) for name in ("RacingBois.Server.Host", "libe_sqlite3.so", "libcoreclr.so", "libhostfxr.so")]
    for name in ("launch-local.sh", "launch-lan.sh"):
        launcher = (arm / name).read_text(encoding="utf-8")
        require("--DataRoot" in launcher and "--RealmKind offline" in launcher, "ARM launcher lacks explicit private offline realm.")
    require("--DataRoot" in (windows / "launch-local.bat").read_text() and (windows / "launch-lan.ps1").is_file(), "Windows private-data launcher missing.")
    self_test = native_self_test(windows)
    demo, headers = verify_live_delivery(windows, web_manifest)
    manifests = {}
    for package, rid in ((windows, "win-x64"), (arm, "linux-arm64")):
        entries = manifest_entries(package, [path for path in list_files(package) if path.name != "package-manifest.json"])
        write_json(package / "package-manifest.json", {"generatedUtc": dt.datetime.now(dt.timezone.utc).isoformat(),
                   "runtime": rid + " self-contained", "packageSourceCommit": full_commit, "files": entries})
        manifests[rid] = {"entries": len(entries), "artifact": artifact(package / "package-manifest.json")}
    make_archives(windows, arm, win_zip, arm_tar)
    report = {
        "generatedUtc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "PASS_PACKAGING_ARM_NATIVE_AND_EXTERNAL_NETWORK_UNVERIFIED",
        "release": "0.7.0", "packageSourceCommit": full_commit,
        "compiledUnityCommit": unity_commit, "packagingToolsCommit": recipe_commit,
        "packagingTool": artifact(Path(__file__)), "unityBuildReceipt": artifact(ROOT / "docs/p07/unity/build.json"),
        "sourceBinding": "Selected committed runtime/build inputs are unchanged at recipe HEAD; only the packaging verifier/docs may differ. Actual source hashes, Unity receipt and final package hashes are bound separately; Windows native P07 SQLite smoke executed.",
        "sourceFiles": source_files, "webRoot": relative(web), "webBytes": sum(item["bytes"] for item in web_manifest),
        "webFiles": web_manifest, "webPayloadMatchedInBothPackages": True, "privateDataBundled": False,
        "windows": {"directory": relative(windows), "selfContained": True, "nativeSelfTest": self_test,
                    "sqliteNativeLibrary": artifact(windows / "e_sqlite3.dll"), "immutableFilesValidated": manifests["win-x64"]["entries"],
                    "manifest": manifests["win-x64"]["artifact"], "archive": artifact(win_zip), "allArchiveFilesVerified": True},
        "linuxArm64": {"directory": relative(arm), "selfContained": True, "elfArchitecture": "ELF64 little-endian AArch64 (183)",
                       "nativeBinaries": arm_binaries, "nativeSelfTest": {"status": "NOT_RUN", "reason": "Windows x64 host; no native ARM or OCI execution performed."},
                       "immutableFilesValidated": manifests["linux-arm64"]["entries"], "manifest": manifests["linux-arm64"]["artifact"],
                       "archive": artifact(arm_tar), "allArchiveFilesVerified": True, "executablePermissionsVerified": True},
        "demo": demo, "httpHeaders": headers, "noOciOrFirewallChanges": True,
        "limitations": "Packaging, exact Web hashes over live HTTP/HTTPS and packaged Windows SQLite smoke only. Browser career/gameplay, native ARM, two physical offline LAN machines and Internet regions require separate evidence."
    }
    write_json(EVIDENCE / "delivery.json", report)
    print(json.dumps({"status": report["status"], "commit": full_commit, "webBytes": report["webBytes"],
                      "windows": report["windows"]["archive"], "arm64": report["linuxArm64"]["archive"]}, indent=2))


if __name__ == "__main__":
    main()
