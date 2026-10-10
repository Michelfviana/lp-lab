"""Servidor local do laboratório de Programação Linear (Python 3.10+)."""
import argparse
import errno
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from solver import solve

STATIC = Path(__file__).resolve().parent / 'static'


class Handler(BaseHTTPRequestHandler):
    def send(self, status, body, content_type):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        files = {'/': ('index.html', 'text/html; charset=utf-8'),
                 '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                 '/style.css': ('style.css', 'text/css; charset=utf-8')}
        if path not in files:
            self.send(404, b'Nao encontrado', 'text/plain; charset=utf-8')
            return
        name, mime = files[path]
        self.send(200, (STATIC/name).read_bytes(), mime)

    def do_POST(self):
        if self.path != '/api/solve':
            self.send(404, b'{}', 'application/json')
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 65536:
                raise ValueError('O problema deve ter até 64 KB.')
            data = json.loads(self.rfile.read(size))
            response = solve(data)
        except (ValueError, TypeError, RecursionError) as error:
            self.send(400, json.dumps({'error': str(error)}, ensure_ascii=False).encode(), 'application/json; charset=utf-8')
            return
        self.send(200, json.dumps(response, ensure_ascii=False).encode(), 'application/json; charset=utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Laboratório interativo de Programação Linear')
    parser.add_argument('--port', type=int, default=8501)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('A porta deve estar entre 1 e 65535.')
    try:
        server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    except OSError as error:
        if error.errno != errno.EADDRINUSE:
            raise
        print(
            f'A porta {args.port} já está em uso. Se o aplicativo já estiver aberto, '
            f'acesse http://127.0.0.1:{args.port}.\n'
            'Para iniciar outra instância, escolha uma porta livre: python app.py --port 8502',
            file=sys.stderr,
        )
        sys.exit(1)
    print(f'Aplicativo disponível em http://127.0.0.1:{args.port} — Ctrl+C para encerrar.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
