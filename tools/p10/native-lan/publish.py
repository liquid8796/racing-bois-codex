"""Publish and locally validate a self-contained native offline LAN candidate.

No Unity Web prerequisite, cloud operation or existing realm/process mutation.
The actual restart smoke owns only its two loopback host process instances.
"""
from __future__ import annotations

import datetime as dt
import ctypes
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from package_desktop_candidate import digest, json_bytes, no_links, tree_rows, zip_info


def sources() -> dict:
    selected = set()
    for base in [ROOT / "src", ROOT / "Packages/com.racingbois.foundation/Runtime", HERE]:
        for path in base.rglob("*"):
            if path.is_file() and not {"bin", "obj", "__pycache__"}.intersection(path.parts) and path.suffix in {".cs", ".csproj", ".props", ".targets", ".json", ".py", ".ps1", ".bat", ".txt"}:
                selected.add(path)
    selected.update([ROOT / "global.json", HERE.parent / "package_desktop_candidate.py",
                     ROOT / "tools/p08/desktop/audit_desktop.py", ROOT / "tools/p08/content-pack/audit_publish.py"])
    return {path.relative_to(ROOT).as_posix(): digest(path) for path in sorted(selected)}


def command(args: list[str], output: Path, timeout: int = 180, environment: dict | None = None) -> None:
    with output.open("xb") as log:
        run = subprocess.run(args, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=timeout,
                             env=environment, creationflags=subprocess.CREATE_NO_WINDOW)
    if run.returncode:
        raise RuntimeError("command_failed:" + output.name)


def verify_payload(package: Path) -> None:
    required = ["RacingBois.Server.Host.exe", "RacingBois.Server.Host.dll", "RacingBois.Server.Host.runtimeconfig.json",
                "coreclr.dll", "hostfxr.dll", "hostpolicy.dll", "System.Private.CoreLib.dll", "e_sqlite3.dll",
                "Microsoft.AspNetCore.Server.Kestrel.Core.dll", "launch-native-lan.ps1", "launch-native-lan.bat", "README.txt", "public/README.txt"]
    if any(not (package / name).is_file() for name in required):
        raise ValueError("self_contained_native_package_incomplete")
    runtime = json.loads((package / required[2]).read_text(encoding="utf-8-sig"))["runtimeOptions"]
    if runtime.get("framework") or runtime.get("frameworks") or not runtime.get("includedFrameworks"):
        raise ValueError("host_requires_external_runtime")
    spec = importlib.util.spec_from_file_location("native_lan_desktop_audit", ROOT / "tools/p08/desktop/audit_desktop.py")
    assert spec is not None and spec.loader is not None
    auditor = importlib.util.module_from_spec(spec); spec.loader.exec_module(auditor)
    for name in ["RacingBois.Server.Host.exe", "coreclr.dll", "hostfxr.dll", "hostpolicy.dll", "e_sqlite3.dll"]:
        auditor.pe_machine(package / name)
    for row in tree_rows(package):
        path = Path(row["path"])
        if path.suffix.lower() in {".db", ".sqlite", ".sqlite3", ".key", ".pem", ".pfx", ".log", ".blend"} or path.name.startswith(".env") or any(part.lower() in {"data", "realm-data", "web"} for part in path.parts):
            raise ValueError("private_or_web_payload_in_candidate")


def verify_forced_probe_cleanup(probe: Path, package: Path, private: Path, output: Path) -> dict:
    """Hold the exact owned child handle across forced parent termination."""
    ready = private / "forced-stop-ready.json"
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    kernel.WaitForSingleObject.restype = ctypes.c_uint32
    kernel.TerminateProcess.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    host_handle = None
    with (output / "forced-stop-probe.txt").open("xb") as log:
        process = subprocess.Popen(["dotnet", str(probe), str(package), str(private / "forced-stop-smoke"), str(ready), "--wait-for-termination"],
                                   cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            limit = time.monotonic() + 30
            while not ready.is_file() and process.poll() is None and time.monotonic() < limit:
                time.sleep(.05)
            if not ready.is_file():
                raise ValueError("forced_stop_fixture_start_failed")
            identity = json.loads(ready.read_text())
            if identity["probePid"] != process.pid:
                raise ValueError("forced_stop_fixture_identity_mismatch")
            host_handle = kernel.OpenProcess(0x100000 | 0x1000 | 0x0001, 0, identity["hostPid"])
            if not host_handle:
                raise ValueError("owned_host_handle_unavailable")
            process.kill(); process.wait(timeout=10)
            stopped = kernel.WaitForSingleObject(host_handle, 5000) == 0
            if not stopped:
                raise ValueError("job_failed_to_stop_owned_host_after_probe_termination")
            return {"passed": True, "probePid": process.pid, "hostPid": identity["hostPid"],
                    "forcedProbeTerminationStoppedOwnedHost": True,
                    "scope": "Actual forced probe termination; exact previously opened host handle signalled exit through its kill-on-close Windows Job Object."}
        finally:
            if process.poll() is None:
                process.kill(); process.wait(timeout=10)
            if host_handle:
                if kernel.WaitForSingleObject(host_handle, 0) != 0:
                    kernel.TerminateProcess(host_handle, 1)
                    kernel.WaitForSingleObject(host_handle, 5000)
                kernel.CloseHandle(host_handle)


def archive_package(package: Path, archive: Path) -> dict:
    rows = tree_rows(package)
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_STORED, allowZip64=True) as target:
        for row in rows:
            info = zip_info("RacingBois-LanHost/" + row["path"]); info.file_size = row["bytes"]
            with (package / row["path"]).open("rb") as source, target.open(info, "w", force_zip64=row["bytes"] >= 2**31) as output:
                shutil.copyfileobj(source, output, 1024 * 1024)
    with zipfile.ZipFile(archive) as source:
        if source.namelist() != ["RacingBois-LanHost/" + row["path"] for row in rows]:
            raise ValueError("native_archive_entry_set_mismatch")
        for row in rows:
            info = source.getinfo("RacingBois-LanHost/" + row["path"])
            value = hashlib.sha256()
            with source.open(info) as entry:
                for block in iter(lambda: entry.read(1024 * 1024), b""):
                    value.update(block)
            if info.file_size != row["bytes"] or value.hexdigest() != row["sha256"]:
                raise ValueError("native_archive_payload_mismatch")
    if rows != tree_rows(package):
        raise ValueError("native_package_changed_during_archive")
    return {"path": archive.relative_to(ROOT).as_posix(), "bytes": archive.stat().st_size, "sha256": digest(archive), "entries": len(rows), "allEntriesVerified": True}


def main() -> int:
    if sys.platform != "win32":
        raise RuntimeError("Actual Windows x64 native validation requires Windows")
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    package = ROOT / "Build/LanHost" / ("native-win-x64-" + run_id)
    output = ROOT / "docs/p10/native-lan" / run_id
    private = ROOT / "_local/p10/native-lan" / run_id
    archive = ROOT / "Build/Packages" / ("RacingBois-NativeLan-" + run_id + ".zip")
    for path in [package, output, private, archive]:
        no_links(path)
        if path.exists():
            raise ValueError("candidate_destination_exists")
    output.mkdir(parents=True); private.mkdir(parents=True)
    record = {"schema": 1, "runId": run_id, "status": "PREPARING", "releaseAccepted": False,
              "physicalLanAccepted": False, "package": package.relative_to(ROOT).as_posix(),
              "scope": "Native Windows self-contained candidate packaging and isolated loopback/restart smoke only. No Unity player or physical two-PC WAN-disconnected acceptance."}
    before = sources()
    record["sources"] = before
    record["sourceSha256"] = hashlib.sha256(json_bytes(before)).hexdigest()
    def save():
        (output / "receipt.json").write_bytes(json_bytes(record))
    save()
    try:
        command(["dotnet", "publish", "src/Server/RacingBois.Server.Host", "-c", "Release", "-r", "win-x64", "--self-contained", "true", "-p:PublishSingleFile=false", "-o", str(package), "--nologo"], output / "publish.txt")
        for name in ["launch-native-lan.ps1", "launch-native-lan.bat", "README.txt"]:
            shutil.copyfile(HERE / name, package / name)
        (package / "public").mkdir()
        (package / "public/README.txt").write_text("Racing Bois native LAN: each Windows player uses its installed content. No browser build is served.\n", encoding="utf-8")
        verify_payload(package)
        published_rows = tree_rows(package)
        environment = dict(os.environ, DOTNET_ROOT=str(private / "absent-runtime"), DOTNET_ROOT_X64=str(private / "absent-runtime"), DOTNET_MULTILEVEL_LOOKUP="0")
        command([str(package / "RacingBois.Server.Host.exe"), "--SelfTest"], output / "native-selftest.json", 30, environment)
        selftest = json.loads((output / "native-selftest.json").read_text(encoding="utf-8-sig"))
        if selftest.get("status") != "PASS" or selftest.get("architecture") != "X64" or selftest.get("sqliteNativeRollback") is not True:
            raise ValueError("actual_native_selftest_failed")
        command(["dotnet", "publish", str(HERE / "Smoke/Smoke.csproj"), "-c", "Release", "--no-self-contained", "-o", str(private / "probe"), "--nologo"], output / "probe-build.txt")
        if sources() != before:
            raise ValueError("source_changed_during_build")
        command(["dotnet", str(private / "probe/Smoke.dll"), str(package), str(private / "smoke"), str(output / "native-smoke.json")], output / "native-smoke.txt", 90)
        smoke = json.loads((output / "native-smoke.json").read_text())
        if smoke.get("passed") is not True or smoke.get("allOwnedHostsStopped") is not True or smoke.get("starts") != 2:
            raise ValueError("actual_native_restart_smoke_failed")
        cleanup = verify_forced_probe_cleanup(private / "probe/Smoke.dll", package, private, output)
        (output / "forced-stop.json").write_bytes(json_bytes(cleanup))
        if tree_rows(package) != published_rows:
            raise ValueError("native_execution_changed_package_bytes")
        manifest = {"schema": 1, "kind": "native-lan-host-candidate", "runtime": "win-x64", "realmKind": "offline", "releaseAccepted": False,
                    "sourceSha256": record["sourceSha256"], "protocolVersion": smoke["protocolVersion"], "contentHash": smoke["contentHash"], "files": published_rows}
        (package / "package-manifest.json").write_bytes(json_bytes(manifest))
        record.update(protocolVersion=smoke["protocolVersion"], contentHash=smoke["contentHash"],
                      nativeSelfTestPassed=True, nativeRestartSmokePassed=True, forcedProbeCleanupPassed=True,
                      packageManifestSha256=digest(package / "package-manifest.json"))
        command(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(package / "launch-native-lan.ps1"), "-VerifyOnly"], output / "powershell51-verify.txt", 30)
        command(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(package / "launch-native-lan.ps1"), "-LocalOnly", "-DataRoot", str(private / "uncreated-plan-realm"), "-PlanOnly"], output / "powershell51-plan.txt", 30)
        if (private / "uncreated-plan-realm").exists():
            raise ValueError("plan_only_created_data")
        archive.parent.mkdir(parents=True, exist_ok=True)
        record["archive"] = archive_package(package, archive)
        after = sources()
        record["changedSources"] = sorted(name for name in before.keys() | after.keys() if before.get(name) != after.get(name))
        record["sourceStable"] = not record["changedSources"]
        if not record["sourceStable"]:
            raise ValueError("source_changed_during_package_validation")
        record["status"] = "PASS_CANDIDATE_PACKAGING_AND_LOCAL_RESTART"
    except Exception as error:
        record.update(status="FAIL", errorCode=str(error) if isinstance(error, (ValueError, RuntimeError)) else type(error).__name__)
    finally:
        record["completedUtc"] = dt.datetime.now(dt.timezone.utc).isoformat()
        record["evidence"] = [{"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": digest(path)} for path in sorted(output.iterdir()) if path.is_file() and path.name != "receipt.json"]
        save()
    print(json.dumps({key: record.get(key) for key in ["status", "errorCode", "package", "protocolVersion", "contentHash", "sourceStable", "archive", "releaseAccepted"]}, indent=2), flush=True)
    return 0 if record["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
