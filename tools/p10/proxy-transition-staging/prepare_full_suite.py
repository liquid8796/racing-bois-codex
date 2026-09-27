"""Run unchanged gameplay test bodies against the isolated candidate, with truthful output/source paths."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
s=(ROOT/'src/Tests/RacingBois.Gameplay.Tests/Program.cs').read_text(encoding='utf8')
s=s.replace('docs/p03','docs/p10/proxy-transition-staging/full-gameplay')
s=s.replace('sourcePaths.AddRange(Directory.GetFiles("Packages/com.racingbois.foundation/Runtime/Simulation", "*.cs"));','''foreach (string path in Directory.GetFiles("Packages/com.racingbois.foundation/Runtime/Simulation", "*.cs"))
    if (Path.GetFileName(path) != "PedestrianSimulation.cs" && Path.GetFileName(path) != "RiderPrediction.cs" && Path.GetFileName(path) != "DrivingDynamics.cs" && Path.GetFileName(path) != "CombatResolver.cs") sourcePaths.Add(path);
sourcePaths.AddRange(Directory.GetFiles("tools/p10/proxy-transition-staging/StageSimulation", "*.cs"));
sourcePaths.Add("tools/p10/proxy-transition-staging/FullGameplayProgram.cs");
sourcePaths.Add("tools/p10/proxy-transition-staging/FullGameplayTests.csproj");''')
(HERE/'FullGameplayProgram.cs').write_text(s,encoding='utf8')
print('Staged unchanged full gameplay tests; output/source binding paths isolated.')
