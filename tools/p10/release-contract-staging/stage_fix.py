"""Stage a desktop dependency-receipt fix without modifying live source."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(text, old, new):
    assert text.count(old) == 1, old[:100]
    return text.replace(old, new)


builder_path = ROOT / "Assets/RacingBois/Editor/P08DesktopBuilder.cs"
audit_path = ROOT / "tools/p08/desktop/audit_desktop.py"
builder = builder_path.read_text(encoding="utf-8-sig")
builder = replace_once(builder,
    "public FileReceipt[] installedContent, playerFiles, sourceFiles; public string validationScope;",
    "public FileReceipt[] installedContent, playerFiles, sourceFiles; public string validationScope;\n"
    "            public int unityDependencySchema = 2; public string[] unityDependencyRoots;\n"
    "            public DependencyFileReceipt[] unityDependencies; public PackageReceipt[] unityPackages; public string[] unityBuiltInDependencies; public string unityDependencyFingerprint;")
builder = replace_once(builder,
    "var sourceFiles = SourceSnapshot(); string fingerprint = SourceFingerprint(sourceFiles);",
    "var sourceFiles = SourceSnapshot(out var dependencies); string fingerprint = SourceFingerprint(sourceFiles);\n"
    "                receipt.unityDependencyRoots = new[] { RaceBuilder.ScenePath, UrpProfileAuthoring.DesktopPipelinePath };\n"
    "                receipt.unityDependencies = dependencies.files; receipt.unityPackages = dependencies.packages; receipt.unityBuiltInDependencies = dependencies.builtIns; receipt.unityDependencyFingerprint = DependencyFingerprint(dependencies);")
builder = replace_once(builder,
    "receipt.sourceBindingPassed = fingerprint == SourceFingerprint(SourceSnapshot());",
    "var after = SourceSnapshot(out var dependenciesAfter);\n"
    "                receipt.sourceBindingPassed = fingerprint == SourceFingerprint(after) &&\n"
    "                    receipt.unityDependencyFingerprint == DependencyFingerprint(dependenciesAfter);")
start = builder.index("        private static FileReceipt[] SourceSnapshot()")
end = builder.index("        private static string SourceFingerprint", start)
builder = builder[:start] + (OUT / "dependency_capture.cs.fragment").read_text(encoding="utf-8") + "\n" + builder[end:]
(OUT / "P08DesktopBuilder.cs").write_text(builder, encoding="utf-8", newline="\n")

audit = audit_path.read_text(encoding="utf-8-sig")
(OUT / "baseline_audit_desktop.py").write_bytes(audit_path.read_bytes())
audit = replace_once(audit, "from pathlib import Path", "from pathlib import Path, PurePosixPath")
start = audit.index("def audit_sources(receipt: dict) -> None:")
end = audit.index("def audit_player(", start)
audit = audit[:start] + (OUT / "dependency_validation.py.fragment").read_text(encoding="utf-8") + "\n\n" + audit[end:]
(OUT / "audit_desktop.py").write_text(audit, encoding="utf-8", newline="\n")
test_path = ROOT / "tools/p08/desktop/test_audit_desktop.py"
tests = test_path.read_text(encoding="utf-8-sig")
tests = replace_once(tests, "from pathlib import Path", "from pathlib import Path\nfrom unittest.mock import patch")
tests = replace_once(tests, "from audit_desktop import PROJECT,", "from audit_desktop import dependency_fingerprint, SOURCE_SETTINGS, UNITY_DEPENDENCY_ROOTS, PROJECT,")
start = tests.index("    def test_source_snapshot_mutation_rejected(self):")
end = tests.index("    def test_actual_receipt_and_all_player_bytes_bound(self):", start)
tests = tests[:start] + (OUT / "legacy_source_test.py.fragment").read_text(encoding="utf-8") + "\n" + tests[end:]
(OUT / "test_audit_desktop.py").write_text(tests, encoding="utf-8", newline="\n")
manifest = {"schema": 1, "liveEdits": False, "files": [
    {"target": path.relative_to(ROOT).as_posix(), "beforeSha256": digest(path), "candidate": name,
     "candidateSha256": digest(OUT / name)}
    for path, name in [(builder_path, "P08DesktopBuilder.cs"), (audit_path, "audit_desktop.py"), (test_path, "test_audit_desktop.py")]]}
(OUT / "candidate-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(json.dumps(manifest, indent=2))
