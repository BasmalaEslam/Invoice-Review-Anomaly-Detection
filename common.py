"""Small local JSON service. Bind to loopback by default; not a public hosting stack."""
import argparse, csv, hashlib, io, json, os, sqlite3, threading, urllib.request
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOCK = threading.RLock()

def now():
    return datetime.now(timezone.utc).isoformat()

def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')

@contextmanager
def db():
    (ROOT / 'runtime').mkdir(exist_ok=True)
    con = sqlite3.connect(ROOT / 'runtime' / 'app.db', timeout=15)
    con.row_factory = sqlite3.Row
    try:
        with con:
            yield con
    finally:
        con.close()

def llm_json(system, user):
    """Optional OpenAI-compatible chat endpoint, e.g. local LM Studio.
    Explicit opt-in. Never call without ENABLE_LLM=1. No secrets in logs.
    """
    if os.getenv('ENABLE_LLM') != '1':
        return None
    base = os.getenv('LLM_BASE_URL', 'http://127.0.0.1:1234/v1').rstrip('/')
    model = os.getenv('LLM_MODEL', '')
    if not model:
        raise ValueError('Set LLM_MODEL to the exact loaded model identifier.')
    body = {'model': model, 'temperature': 0, 'messages': [
        {'role': 'system', 'content': system + '\nReturn one JSON object only.'},
        {'role': 'user', 'content': user}]}
    headers = {'Content-Type': 'application/json'}
    key = os.getenv('LLM_API_KEY')
    if key:
        headers['Authorization'] = 'Bearer ' + key
    req = urllib.request.Request(base + '/chat/completions', json.dumps(body).encode(), headers)
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            data = json.load(response)
        value = json.loads(data['choices'][0]['message']['content'])
        if not isinstance(value, dict):
            raise ValueError('Expected an object')
        return value
    except Exception as exc:
        raise ValueError('LLM response failed or was not valid JSON; use local mode or check endpoint.') from exc

def csv_text(rows):
    if not rows:
        return ''
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=list(rows[0]))
    writer.writeheader()
    # Escape spreadsheet formula prefixes in exported untrusted text cells.
    safe_rows = [{key: ("'" + value if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else value)
                  for key, value in row.items()} for row in rows]
    writer.writerows(safe_rows)
    return out.getvalue()

def serve(dispatch, port):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Do not log customer payloads.

        def send(self, status, content, kind='application/json; charset=utf-8'):
            raw = content.encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            if self.path == '/':
                self.send(200, (ROOT / 'ui.html').read_text(encoding='utf-8'), 'text/html; charset=utf-8')
            elif self.path == '/health':
                self.send(200, json.dumps({'status': 'ok', 'project': ROOT.name}))
            else:
                self.send(404, '{"error":"Not found"}')

        def do_POST(self):
            try:
                n = int(self.headers.get('Content-Length', '0'))
                if not 0 < n <= 262144:
                    raise ValueError('JSON body must be between 1 and 262144 bytes.')
                value = json.loads(self.rfile.read(n))
                if not isinstance(value, dict):
                    raise ValueError('JSON object required.')
                with LOCK:
                    result = dispatch(self.path, value)
                self.send(200, json.dumps(result, ensure_ascii=False, allow_nan=False))
            except (ValueError, KeyError, TypeError) as exc:
                self.send(400, json.dumps({'error': str(exc)}, ensure_ascii=False))
            except FileNotFoundError:
                self.send(409, '{"error":"Run python app.py train first."}')
            except Exception:
                self.send(500, '{"error":"Unexpected local error. Inspect inputs and run tests."}')
    host = os.getenv('APP_HOST', '127.0.0.1')
    print(f'Open http://{host}:{port} — Ctrl+C to stop', flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
