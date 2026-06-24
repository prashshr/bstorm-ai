import http.server
import socketserver

PORT = 3000
FILE = 'ai-ensemble-v5.html'

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.path = '/'
        return super().do_GET()

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Serving {FILE} at http://localhost:{PORT}")
    httpd.serve_forever()