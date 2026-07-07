"""Deterministic page reduction utilities."""

from .fetch import FetchResult, fetch_html
from .html_to_markdown import ReducedPage, reduce_html
from .signals import EMAIL_RE, PHONE_RE, URL_RE, collect_signals

__all__ = ["EMAIL_RE", "PHONE_RE", "URL_RE", "FetchResult", "ReducedPage", "collect_signals", "fetch_html", "reduce_html"]
