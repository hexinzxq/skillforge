# Probe catalog

Each entry: the hypothesis it tests, the probe, and what the output tells you.
Run probes in the *same* environment as the failure (same shell, same cwd, same
env), otherwise you are testing a different program.

## Environment

| hypothesis | probe |
|---|---|
| wrong interpreter/version | `which -a python3 node; python3 -V; node -v` |
| missing or wrong env var | `python3 -c "import os;print({k:v for k,v in os.environ.items() if 'KEY' in k})"` |
| different cwd | `python3 -c "import os;print(os.getcwd(), os.listdir('.'))"` |
| locale / encoding | `python3 -c "import sys,locale;print(sys.stdout.encoding, locale.getpreferredencoding())"` |
| shell vs app PATH differ | `env | grep -i path` inside the failing process (`os.environ['PATH']`) |
| venv not active | `which python3; python3 -c "import sys;print(sys.prefix)"` |

## Input / data

| hypothesis | probe |
|---|---|
| value isn't what it looks like | `print(repr(value))` — repr, not str; types and invisible chars |
| JSON shape mismatch | `python3 -m json.tool < f.json | head -40` |
| encoding is not UTF-8 | `file -I f.txt; python3 -c "print(open('f.txt','rb').read()[:80])"` |
| timezone / DST | `python3 -c "import datetime;print(datetime.datetime.now().astimezone())"` |
| dict/list ordering assumption | sort keys before comparing; print both orders |
| float equality | print the delta, not `==` |

## State from previous runs

| hypothesis | probe |
|---|---|
| stale build artifact | `find . -name "__pycache__" -o -name "dist" -o -name ".next" | head` then delete and rerun |
| sqlite lock / WAL | `sqlite3 db "PRAGMA journal_mode; PRAGMA busy_timeout;"` and `ls -l db*` |
| port already in use | `lsof -nP -iTCP:PORT -sTCP:LISTEN` |
| leftover process | `ps aux | grep -v grep | grep <name>` |
| cache poisoning | rerun with the cache disabled, not cleared: `--no-cache`, `PYTHONDONTWRITEBYTECODE=1` |
| permissions | `ls -l` on the exact path, plus `id -u` |

## Concurrency

| hypothesis | probe |
|---|---|
| race | run the reproduction 50 times, count failures (`for i in $(seq 50)`) |
| deadlock | `py-spy dump --pid`, or send SIGQUIT and read the traceback |
| shared connection across threads | log `threading.get_ident()` at open and use time |
| ordering assumption | add a monotonic counter print at each step |

## Network / TLS

| hypothesis | probe |
|---|---|
| DNS vs connect vs TLS | `curl -v --max-time 10 URL` — the `*` lines separate the stages |
| proxy env poisoning | `env | grep -i proxy` |
| certificate chain | `openssl s_client -connect host:443 -servername host </dev/null 2>&1 | head -30` |
| IPv6 vs IPv4 | `curl -4` and `curl -6` separately |

## Git / CI only failures

| hypothesis | probe |
|---|---|
| passes locally, fails in CI | run the CI step verbatim locally in a clean dir (`git stash -u`, fresh clone, no venv) |
| file case sensitivity | clone on a case-insensitive fs vs CI's Linux |
| line endings | `git ls-files --eol | head` |
| test order dependence | run the single failing test alone, then the whole file |
| hidden dependency on untracked file | `git status --ignored --short | head -30` |

## Framework-specific quick checks

- Python import errors: `python3 -c "import mod; print(mod.__file__)"` — usually
  a shadowed module name (a local `types.py` or `sqlite3.py`).
- FastAPI 500s: enable `uvicorn --log-level debug` and look for the traceback in
  the server console, not the client response.
- Node ESM/CJS: `node -p "require('./package.json').type"` and check the
  extension of the failing file.
- React hydration mismatch: compare server HTML and client render for the same
  node; usually `Date.now()`, `Math.random()`, or locale formatting.
