#!/usr/bin/env python3
"""Read-only logical state digest for an upgrade; never emits the stored JSON or authentication material."""
import datetime,json
from backup import STATE,inspect_database
print(json.dumps({'generatedUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),**inspect_database(STATE/'realm/realm.sqlite3')}))
