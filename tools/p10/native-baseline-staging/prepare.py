"""Stage the native baseline wrapper and a tiny opt-in workload bridge; no Assets writes."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
copied = []


def stage(source, destination, transforms):
    original = (ROOT / source).read_bytes()
    text = original.decode('utf-8-sig')
    for before, after in transforms:
        if before not in text:
            raise ValueError('Source shape changed: ' + source)
        text = text.replace(before, after)
    target = HERE / destination
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding='utf-8', newline='')
    copied.append({'source': source, 'sourceSha256': hashlib.sha256(original).hexdigest(),
                   'candidate': destination, 'candidateSha256': hashlib.sha256(target.read_bytes()).hexdigest()})


stage('Assets/RacingBois/Client/Bootstrap/P06BenchmarkRunner.cs', 'Bridge/P06BenchmarkRunner.cs', [
    ('public long CurrentTick => world == null ? 0 : world.Tick;', '''public long CurrentTick => world == null ? 0 : world.Tick;
        public bool IsMeasuring => measuring;
        public double MeasurementStarted => measurementBegan;
        public int CurrentCycle => cycles;
        public long DiagnosticMeasuredTicks => measuredTicks;
        private bool nativeDiagnostic;
        private bool nativeTimingApplied;
        private int originalDiagnosticVSync;
        /// <summary>Explicit bounded Windows diagnostic; ordinary benchmark Begin remains 60-120 seconds.</summary>
        public void BeginNativeDiagnostic()
        {
            if (UnityApplication.isEditor || UnityApplication.platform != RuntimePlatform.WindowsPlayer || Running || Completed)
                throw new InvalidOperationException("A fresh native Windows diagnostic instance is required.");
            nativeDiagnostic = true;
            frames = new float[1000000];
            Begin();
        }
        public void RestoreNativeDiagnosticTiming()
        {
            if (!nativeTimingApplied) return;
            UnityApplication.targetFrameRate = originalTargetFrameRate;
            QualitySettings.vSyncCount = originalDiagnosticVSync;
            nativeTimingApplied = false;
        }'''),
    ('private readonly float[] frames = new float[FrameCapacity];', 'private float[] frames = new float[FrameCapacity];'),
    ('SampleSeconds = Mathf.Clamp(SampleSeconds, 60, 120);', 'SampleSeconds = nativeDiagnostic ? 600 : Mathf.Clamp(SampleSeconds, 60, 120);'),
    ('UnityApplication.targetFrameRate = 60;', '''UnityApplication.targetFrameRate = nativeDiagnostic ? -1 : 60;
            if (nativeDiagnostic) { originalDiagnosticVSync = QualitySettings.vSyncCount; nativeTimingApplied = true; QualitySettings.vSyncCount = 0; }'''),
    ('targetFrameRate = 60, vSyncCount = QualitySettings.vSyncCount,', 'targetFrameRate = UnityApplication.targetFrameRate, vSyncCount = QualitySettings.vSyncCount,'),
    ('if (frameCount < FrameCapacity)', 'if (frameCount < frames.Length)'),
    ('effects.ResetEvents(); UnityApplication.targetFrameRate = originalTargetFrameRate;', 'effects.ResetEvents(); if (!nativeDiagnostic) UnityApplication.targetFrameRate = originalTargetFrameRate;'),
    ('if (receipt != null) UnityApplication.targetFrameRate = originalTargetFrameRate;', 'if (nativeDiagnostic) RestoreNativeDiagnosticTiming(); else if (receipt != null) UnityApplication.targetFrameRate = originalTargetFrameRate;')])
for name in ['PreviewBuildScope.cs']:
    stage('Assets/RacingBois/Diagnostics/PoseEnvelopePreview/Editor/' + name,
          'Editor/' + name.replace('Preview', 'Baseline'), [
              ('RacingBois.Diagnostics.PoseEnvelopePreview.Editor', 'RacingBois.Diagnostics.NativeBaseline.Editor'),
              ('PreviewBuildScope', 'BaselineBuildScope'),
              *([('PreviewProjectSettingsScope', 'BaselineProjectSettingsScope')] if 'ProjectSettings' in name else [])])
stage('tools/p10/pose-envelope-native-staging/CompileAudit/Program.cs', 'CompileAudit/Program.cs', [
    ('docs/p10/pose-envelope-native-staging/compiled-sources.json', 'docs/p10/native-baseline/compiled-sources.json'),
    ('"RacingBois.Diagnostics.PoseEnvelopePreview", "RacingBois.Diagnostics.PoseEnvelopePreview.Editor", "RacingBois.Client.Presentation", "RacingBois.Gameplay.Definitions", "RacingBois.Golden"',
     '"RacingBois.Diagnostics.NativeBaseline", "RacingBois.Diagnostics.NativeBaseline.Editor", "RacingBois.Client.Bootstrap", "RacingBois.Client.Presentation", "RacingBois.Client.Application", "RacingBois.Client.Adapters", "RacingBois.Simulation", "RacingBois.Gameplay.Definitions", "RacingBois.Authoring.Editor"')])
(HERE / 'prepared-inputs.json').write_text(json.dumps({'schema': 1, 'liveEdits': False, 'copied': copied}, indent=2)+'\n', encoding='utf-8')
print('Staged', len(copied), 'hash-bound copies; live sources unchanged.')
