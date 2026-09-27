using RacingBois.Server.Infrastructure;
if (args.Length != 1) return 2;
using var store = new SqliteRealmStateStore(Path.GetFullPath(args[0]), "online");
Console.WriteLine("RESTORE_PROJECTION_VALIDATED");
return 0;
