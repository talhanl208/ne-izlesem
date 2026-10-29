"""Şablonlarda kullanılan yardımcı filtreler."""
from __future__ import annotations

from urllib.parse import urlencode

from flask import Flask

from .textutil import lower_tr


def tr1(value) -> str:
    """7.25 → '7,3'"""
    if value is None:
        return "—"
    try:
        return f"{float(value):.1f}".replace(".", ",")
    except (TypeError, ValueError):
        return "—"


def score_class(value) -> str:
    if value is None:
        return "s-none"
    v = float(value)
    if v >= 7.5:
        return "s-high"
    if v >= 6.3:
        return "s-mid"
    return "s-low"


def register(app: Flask) -> None:
    app.jinja_env.filters["tr1"] = tr1
    app.jinja_env.filters["score_class"] = score_class
    app.jinja_env.filters["qs"] = lambda pairs: urlencode(pairs)
    app.jinja_env.filters["lower_tr"] = lower_tr
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True
