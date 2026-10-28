import json
import os
import secrets
import shutil
import tempfile
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from converter import convert

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / 'output'
TOKEN = secrets.token_urlsafe(24)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, data, kind='application/json'):
        body = json.dumps(data).encode() if kind == 'application/json' else data
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def route(self):
        path = urlsplit(self.path).path
        prefix = '/' + TOKEN + '/'
        return path[len(prefix):] if path.startswith(prefix) else None

    def do_GET(self):
        if self.route() == '':
            return self.reply(200, (ROOT / 'index.html').read_bytes(), 'text/html; charset=utf-8')
        self.reply(404, {'error': 'Not found'})

    def do_POST(self):
        route = self.route()
        if route is None:
            return self.reply(403, {'error': 'Access denied'})
        try:
            if route == 'open':
                OUTPUT.mkdir(exist_ok=True)
                os.startfile(OUTPUT)
                return self.reply(200, {'ok': True})
            if route != 'convert':
                return self.reply(404, {'error': 'Not found'})
            name = parse_qs(urlsplit(self.path).query).get('name', [''])[0]
            name = name.replace('\\', '/').split('/')[-1]
            if Path(name).suffix.lower() not in {'.cbz', '.cbr'}:
                raise ValueError('Choose a CBZ or CBR file.')
            length = int(self.headers.get('Content-Length', '0'))
            if length <= 0:
                raise ValueError('The file is empty.')
            with tempfile.TemporaryDirectory(prefix='comic-upload-') as temp:
                source = Path(temp) / name
                with source.open('wb') as stream:
                    remaining = length
                    while remaining:
                        data = self.rfile.read(min(1024 * 1024, remaining))
                        if not data:
                            raise ValueError('File transfer interrupted.')
                        stream.write(data)
                        remaining -= len(data)
                target, count = convert(source, OUTPUT)
                self.reply(200, {'name': target.name, 'pages': count})
        except Exception as error:
            self.reply(400, {'error': str(error)})


if __name__ == '__main__':
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    url = f'http://127.0.0.1:{server.server_port}/{TOKEN}/'
    print('Comic to PDF is running locally. Keep this window open.\n' + url, flush=True)
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
