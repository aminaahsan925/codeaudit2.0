"""A tiny configurable HTTP server for live-check tests.

Serves on 127.0.0.1 with an ephemeral port, so tests need no network
access. Routes are set per test: map a path to a RouteResponse, or to a
callable taking the request handler (for responses that depend on the
request, e.g. CORS answers that vary by Origin header). Unmapped paths
return 404.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


@dataclass
class RouteResponse:
    status: int = 200
    headers: list[tuple[str, str]] = field(default_factory=list)
    body: str | bytes = ""


Route = RouteResponse | Callable[[BaseHTTPRequestHandler], RouteResponse]


class _LiveTestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_args: object) -> None:
        pass

    def _serve(self) -> None:
        routes: dict[str, Route] = self.server.routes  # type: ignore[attr-defined]
        route = routes.get(self.path)
        if route is None:
            route = RouteResponse(status=404, body="Not found")
        elif callable(route):
            route = route(self)
        body = route.body.encode() if isinstance(route.body, str) else route.body
        self.send_response(route.status)
        for name, value in route.headers:
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    do_GET = _serve  # noqa: N815 - name required by BaseHTTPRequestHandler
    do_POST = _serve  # noqa: N815 - name required by BaseHTTPRequestHandler
    do_HEAD = _serve  # noqa: N815 - name required by BaseHTTPRequestHandler


class LiveTestServer:
    """Context manager around a ThreadingHTTPServer on 127.0.0.1."""

    def __init__(self) -> None:
        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), _LiveTestHandler)
        self._httpd.daemon_threads = True
        self._httpd.routes = {}  # type: ignore[attr-defined]
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self._httpd.server_address[1]}"

    @property
    def routes(self) -> dict[str, Route]:
        return self._httpd.routes  # type: ignore[attr-defined]

    def __enter__(self) -> LiveTestServer:
        self._thread.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        self._thread.join(timeout=5)
