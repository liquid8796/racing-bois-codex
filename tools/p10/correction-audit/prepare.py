"""Copy the unchanged P10 driver; add observation hooks only in this directory."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'ProtocolSoakNext'
program=(BASE/'Program.cs').read_text(encoding='utf8')
program=program.replace('// Credentials only exist', 'if (args.Length > 0 && args[0] == "--replay") return CorrectionReplay.Run(args);\n\n// Credentials only exist',1)
program=program.replace('var stopwatch = Stopwatch.StartNew(); var driver = new RaceDriver(clients, clock);', 'var stopwatch = Stopwatch.StartNew(); var correctionAudit = new CorrectionTrace(clock); var driver = new RaceDriver(clients, clock, correctionAudit);')
if 'correctionAudit.Attach(index, participant)' not in program:
    program=program.replace('journal.Attach(index, participant);', 'journal.Attach(index, participant); correctionAudit.Attach(index, participant);')
if 'correctionTrace = correctionAudit.Report()' not in program:
    program=program.replace('diagnosticEvents = journal.Events.ToArray(),', 'correctionTrace = correctionAudit.Report(), diagnosticEvents = journal.Events.ToArray(),')
program=program.replace('new JsonSerializerOptions { WriteIndented = true }', 'new JsonSerializerOptions { WriteIndented = true, IncludeFields = true }')
program=program.replace('internal sealed class RaceDriver(List<Participant> clients, ProbeClock clock)', 'internal sealed class RaceDriver(List<Participant> clients, ProbeClock clock, CorrectionTrace audit)')
if 'audit.Presented(p.Session)' not in program:
    program=program.replace('p.Session.Step(1, 0, steer, 0); p.Session.SamplePresentation();', 'p.Session.Step(1, 0, steer, 0); p.Session.SamplePresentation(); audit.Presented(p.Session);')
program=program.replace('.Append("tools/p10/ProtocolSoakNext/ProtocolSoakNext.csproj")', '.Concat(Directory.GetFiles("tools/p10/correction-audit", "*.cs", SearchOption.TopDirectoryOnly)).Append("tools/p10/correction-audit/CorrectionAudit.csproj").Append("tools/p10/ProtocolSoakNext/ProtocolSoakNext.csproj")')
# The experiment is restricted to a NEW task-owned loopback realm by the runner.
program=program.replace('endpoint.Scheme == "ws" && !endpoint.IsLoopback', '!endpoint.IsLoopback')
(HERE/'Program.cs').write_text(program,encoding='utf8')
transport=(BASE/'ProbeTransport.cs').read_text(encoding='utf8')
if 'BeforeDispatch' not in transport:
    transport=transport.replace('public Action<string> TraceSent;', 'public Action<string> TraceSent;\n    public Action<string> BeforeDispatch, AfterDispatch;')
transport=transport.replace('if (socket == current) Message?.Invoke(text);', 'if (socket == current) { BeforeDispatch?.Invoke(text); Message?.Invoke(text); AfterDispatch?.Invoke(text); }')
(HERE/'ProbeTransport.cs').write_text(transport,encoding='utf8')
receipt={'baseline':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [BASE/'Program.cs',BASE/'ProbeTransport.cs',BASE/'DiagnosticJournal.cs']},'behavior':'Controller, handshake, retries, timeouts and production source unchanged. Added read-only observers and report serialization. This probe rejects non-loopback endpoints.'}
(HERE/'baseline.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
print('Diagnostic copies prepared; baseline files untouched.')
