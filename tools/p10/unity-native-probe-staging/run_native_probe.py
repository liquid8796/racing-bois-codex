"""CLI for the source-bound native WSS specimen; implementation is importable for lifecycle tests."""
import json
from native_probe_runner import main

if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,ValueError,KeyError,TypeError) as error:
        print(json.dumps({'status':'FAIL','errorCode':type(error).__name__,'scope':'Launcher setup failed; no raw logs emitted.'}));raise SystemExit(1)
