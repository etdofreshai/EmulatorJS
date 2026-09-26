#!/usr/bin/env python3
from http.server import HTTPServer, SimpleHTTPRequestHandler, test
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import sys

RA_UA = 'EmulatorJS/dev rcheevos'

class CORSRequestHandler (SimpleHTTPRequestHandler):
    # RetroAchievements proxy: the RA API sends no CORS headers and rejects browser user agents.
    def ra_proxy(self):
        path = self.path[len('/ra'):]
        host = 'https://retroachievements.org' if path.startswith('/dorequest.php') else 'https://media.retroachievements.org'
        body = self.rfile.read(int(self.headers.get('Content-Length', 0))) if self.command == 'POST' else None
        req = Request(host + path, data=body, method=self.command, headers={'User-Agent': RA_UA})
        if body is not None:
            req.add_header('Content-Type', self.headers.get('Content-Type', 'application/x-www-form-urlencoded'))
        try:
            r = urlopen(req, timeout=30)
        except HTTPError as e:
            r = e
        data = r.read()
        # emscripten's wget drops bodies of non-2xx responses; RA errors are JSON with Success:false, so send them as 200
        json_err = r.status >= 400 and 'json' in r.headers.get('Content-Type', '')
        self.send_response(200 if json_err else r.status)
        self.send_header('Content-Type', r.headers.get('Content-Type', 'application/octet-stream'))
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.startswith('/ra/'): return self.ra_proxy()
        super().do_GET()

    def do_POST(self):
        if self.path.startswith('/ra/'): return self.ra_proxy()
        self.send_error(405)

    def end_headers (self):
        self.send_header('Cross-Origin-Embedder-Policy', 'require-corp')
        self.send_header('Cross-Origin-Opener-Policy', 'same-origin')
        # Force EJS's IndexedDB cache to revalidate against Last-Modified on
        # every request instead of trusting the 5-day default expiry. Without
        # this the user keeps getting served the first-downloaded core after
        # we rebuild it.
        self.send_header('Cache-Control', 'max-age=0, must-revalidate')
        SimpleHTTPRequestHandler.end_headers(self)

def main():
    test(CORSRequestHandler, HTTPServer, port=int(sys.argv[1]) if len(sys.argv) > 1 else 8000)

if __name__ == '__main__':
    main()
