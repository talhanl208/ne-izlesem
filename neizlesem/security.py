"""Güvenlik katmanı.

* HTTP güvenlik başlıkları (CSP, clickjacking ve MIME koruması, izin politikası).
* IP başına basit istek sınırlama: biri sayfayı sürekli yenileyerek TMDB/OMDb
  kotanı tüketemesin diye.
* Hata sayfaları: kullanıcıya asla iz (stack trace) gösterilmez.
"""
from __future__ import annotations

import threading
import time
from collections import deque

from flask import Flask, render_template, request

CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data: https://image.tmdb.org https://i.ytimg.com",
    "frame-src https://www.youtube-nocookie.com",
    "connect-src 'self'",
    "media-src 'none'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])

# uç nokta → (istek sayısı, saniye)
LIMITS = {
    "main.results": (30, 60),
    "main.surprise": (30, 60),
    "main.movie": (90, 60),
    "main.search": (40, 60),
    "main.keyword_suggest": (120, 60),
}


class RateLimiter:
    """Bellek içi kayan pencere sınırlayıcı (tek süreçli barındırma için yeterli)."""

    def __init__(self):
        self._hits: dict[tuple[str, str], deque] = {}
        self._lock = threading.Lock()
        self._last_cleanup = time.monotonic()

    def allow(self, key: str, bucket: str, limit: int, window: float) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._hits.setdefault((key, bucket), deque())
            while q and now - q[0] > window:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            if now - self._last_cleanup > 300:
                self._cleanup(now)
            return True

    def _cleanup(self, now: float) -> None:
        self._last_cleanup = now
        for k in [k for k, q in self._hits.items() if not q or now - q[-1] > 600]:
            del self._hits[k]


def client_ip() -> str:
    from flask import current_app
    if current_app.config.get("TRUST_PROXY"):
        real = request.headers.get("X-Real-IP") or request.headers.get("X-Forwarded-For", "").split(",")[0]
        if real.strip():
            return real.strip()
    return request.remote_addr or "?"


def register(app: Flask) -> None:
    limiter = RateLimiter()
    app.extensions["rate_limiter"] = limiter

    @app.before_request
    def _rate_limit():
        if not app.config.get("RATE_LIMIT", True):
            return None
        rule = LIMITS.get(request.endpoint or "")
        if not rule:
            return None
        if not limiter.allow(client_ip(), request.endpoint, *rule):
            if request.endpoint == "main.keyword_suggest":
                return {"error": "Çok fazla istek. Biraz bekle."}, 429
            return render_template(
                "error.html", title="Biraz yavaşlayalım",
                message="Kısa sürede çok fazla arama yapıldı. Bir dakika sonra tekrar dene.",
            ), 429
        return None

    @app.after_request
    def _headers(resp):
        h = resp.headers
        h.setdefault("Content-Security-Policy", CSP)
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        h.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=(), usb=()")
        h.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        if request.is_secure:
            h.setdefault("Strict-Transport-Security", "max-age=31536000")
        if request.endpoint == "static":
            h.setdefault("Cache-Control", "public, max-age=86400")
        return resp

    @app.errorhandler(404)
    def _not_found(_e):
        return render_template("error.html", title="Bu salon boş",
                               message="Aradığın sayfa ya da film bulunamadı."), 404

    @app.errorhandler(405)
    def _method(_e):
        return render_template("error.html", title="Bu kapı kapalı",
                               message="Bu adrese bu şekilde istek gönderilemez."), 405

    @app.errorhandler(500)
    def _server_error(_e):
        return render_template("error.html", title="Projektör arıza yaptı",
                               message="Beklenmeyen bir hata oluştu. Birazdan tekrar dene."), 500
