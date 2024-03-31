import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

address = ("0.0.0.0", 3000)

proc = subprocess.Popen(
    [
        "unzip",
        "-q",
        "/bot.zip",
    ],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    stdin=subprocess.DEVNULL,
)
proc.wait()
proc = subprocess.Popen(
    [
        "/workspace/.pyenv/shims/python",
        "-u",
        "bot.py",
        sys.argv[1],
    ],
    stdout=subprocess.PIPE,
    stderr=sys.stderr,
    stdin=subprocess.PIPE,
)


class MyHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"OK")

    def do_POST(self):
        content_length = int(self.headers["content-length"])
        content = self.rfile.read(content_length).decode("utf-8")

        proc.stdin.write((content + "\n").encode("utf8"))  # type: ignore
        proc.stdin.flush()  # type: ignore
        outs = proc.stdout.readline().decode("utf8").strip()  # type: ignore

        sys.stdout.write(outs + "\n")
        sys.stdout.flush()

        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(outs.encode("utf8"))

    def log_message(self, format, *args):
        return


class MyHTTPServer(HTTPServer):
    def __init__(self, *args, **kwargs):
        self.on_before_serve = kwargs.pop("on_before_serve", None)
        HTTPServer.__init__(self, *args, **kwargs)

    def serve_forever(self):
        if self.on_before_serve:
            self.on_before_serve(self)
        HTTPServer.serve_forever(self)


def main():
    try:
        with MyHTTPServer(address, MyHTTPRequestHandler) as server:
            server.serve_forever()
    except Exception:
        proc.kill()


if __name__ == "__main__":
    main()
