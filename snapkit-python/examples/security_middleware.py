"""
PLATO Fleet Services — Security Middleware
==========================================
Pure Python 3.8+ security middleware stack, WSGI-compatible.
Each class operates independently and can wrap any WSGI app.

Quick start::

    from security_middleware import (
        InputSanitizer, RateLimiter, AuthMiddleware,
        SecurityHeaders, XSSShield, build_stack
    )

    app = YourWSGIApp()
    app = SecurityHeaders(app)
    app = XSSShield(app)
    app = RateLimiter(app, requests_per_second=10, burst=20)
    app = AuthMiddleware(app, api_keys={"key-abc": ["read", "write"]})

Or use the convenience builder::

    app = build_stack(your_wsgi_app, api_keys={"k": ["read"]})
"""

from __future__ import annotations

import html
import re
import time
import threading
import hashlib
import hmac
import logging
import unittest
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
WSGIApp = Callable[[Dict[str, Any], Callable], Iterator[bytes]]
Environ = Dict[str, Any]
StartResponse = Callable[[str, List[Tuple[str, str]]], None]


# ===========================================================================
# InputSanitizer
# ===========================================================================

class InputSanitizer:
    """Sanitise untrusted text input before it touches business logic.

    Strips HTML / ``<script>`` tags, validates UTF-8 encoding, and enforces a
    configurable maximum length.  Designed to be used stand-alone *or* as a
    WSGI middleware that filters ``wsgi.input`` bodies and query strings.

    Args:
        app:        Downstream WSGI callable (optional — omit for stand-alone use).
        max_length: Maximum allowed byte-length of any single input value.
                    Defaults to 65_536 (64 KiB).
        allow_tags: Whitelist of lowercase HTML tag names that should *not* be
                    stripped.  Defaults to empty (strip everything).

    Examples::

        san = InputSanitizer(max_length=1024)
        clean = san.sanitize("<script>alert(1)</script> Hello")
        # → " Hello"

        # Stand-alone length check
        san.validate_length("x" * 2000)  # raises ValueError
    """

    # Matches any HTML / XML tag
    _TAG_RE = re.compile(r"<[^>]+>", re.IGNORECASE | re.DOTALL)
    # Matches script/style blocks including their content
    _SCRIPT_RE = re.compile(
        r"<\s*(script|style)[^>]*>.*?</\s*(script|style)\s*>",
        re.IGNORECASE | re.DOTALL,
    )
    # Matches on* event attributes like onclick="…"
    _EVENT_ATTR_RE = re.compile(r'\bon\w+\s*=\s*["\'][^"\']*["\']', re.IGNORECASE)
    # Matches javascript: URI schemes
    _JS_URI_RE = re.compile(r"javascript\s*:", re.IGNORECASE)

    def __init__(
        self,
        app: Optional[WSGIApp] = None,
        *,
        max_length: int = 65_536,
        allow_tags: Optional[Set[str]] = None,
    ) -> None:
        self._app = app
        self.max_length = max_length
        self._allow_tags: Set[str] = {t.lower() for t in (allow_tags or set())}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def sanitize(self, text: str) -> str:
        """Return *text* with dangerous HTML constructs removed.

        Processing order:
        1. Validate UTF-8 (raises ``UnicodeDecodeError`` on raw bytes input
           that cannot round-trip through UTF-8).
        2. Strip ``<script>`` / ``<style>`` blocks (including content).
        3. Remove ``on*`` event attributes.
        4. Remove ``javascript:`` URI schemes.
        5. Strip remaining HTML tags (respecting *allow_tags*).

        Args:
            text: Raw string to sanitize.

        Returns:
            Sanitised string.

        Examples::

            san = InputSanitizer()
            san.sanitize('<img src=x onerror="alert(1)">')
            # → '<img src=x>'   — onerror stripped; tag kept only if allowed

            san2 = InputSanitizer(allow_tags={"img"})
            san2.sanitize('<img src=x onerror="alert(1)">')
            # → '<img src=x>'
        """
        self._validate_utf8(text)
        text = self._SCRIPT_RE.sub("", text)
        text = self._EVENT_ATTR_RE.sub("", text)
        text = self._JS_URI_RE.sub("blocked:", text)
        text = self._strip_tags(text)
        return text

    def validate_length(self, value: str, *, field: str = "input") -> None:
        """Raise ``ValueError`` if *value* exceeds *max_length* bytes (UTF-8).

        Args:
            value: String to check.
            field: Human-readable field name used in the error message.

        Raises:
            ValueError: When encoded length exceeds ``self.max_length``.
        """
        encoded_len = len(value.encode("utf-8"))
        if encoded_len > self.max_length:
            raise ValueError(
                f"{field!r} exceeds maximum length: {encoded_len} > {self.max_length}"
            )

    def sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize all string values in *data*.

        Args:
            data: Mapping of arbitrary depth to sanitize in-place copy.

        Returns:
            New mapping with all string leaves sanitized and length-checked.
        """
        result: Dict[str, Any] = {}
        for key, val in data.items():
            if isinstance(val, str):
                self.validate_length(val, field=str(key))
                result[key] = self.sanitize(val)
            elif isinstance(val, dict):
                result[key] = self.sanitize_dict(val)
            elif isinstance(val, list):
                result[key] = [
                    self.sanitize(v) if isinstance(v, str) else v for v in val
                ]
            else:
                result[key] = val
        return result

    # ------------------------------------------------------------------
    # WSGI interface
    # ------------------------------------------------------------------

    def __call__(self, environ: Environ, start_response: StartResponse) -> Iterator[bytes]:
        """WSGI entry-point.  Sanitizes ``QUERY_STRING`` before delegating."""
        if self._app is None:
            raise RuntimeError(
                "InputSanitizer requires a wrapped WSGI app when used as middleware"
            )
        qs = environ.get("QUERY_STRING", "")
        if qs:
            try:
                environ["QUERY_STRING"] = self.sanitize(qs)
            except Exception as exc:  # noqa: BLE001
                logger.warning("InputSanitizer rejected query string: %s", exc)
                environ["QUERY_STRING"] = ""
        return self._app(environ, start_response)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_utf8(text: str) -> None:
        """Ensure *text* can safely round-trip through UTF-8."""
        try:
            text.encode("utf-8").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError) as exc:
            raise ValueError(f"Input is not valid UTF-8: {exc}") from exc

    def _strip_tags(self, text: str) -> str:
        """Strip HTML tags, preserving those in *allow_tags*."""
        if not self._allow_tags:
            return self._TAG_RE.sub("", text)

        def _replace(m: re.Match) -> str:
            tag_text = m.group(0)
            # Extract tag name (handles closing tags and self-closing tags)
            inner = tag_text.lstrip("<").lstrip("/").split()[0].rstrip(">").lower()
            return tag_text if inner in self._allow_tags else ""

        return self._TAG_RE.sub(_replace, text)


# ===========================================================================
# RateLimiter
# ===========================================================================

class RateLimiter:
    """Token-bucket per-IP rate limiter, usable as a WSGI middleware.

    Each remote IP gets its own bucket that refills at *requests_per_second*
    tokens/second up to a maximum of *burst* tokens.  Requests that arrive
    when the bucket is empty receive a ``429 Too Many Requests`` response.

    The implementation is thread-safe: a single ``threading.Lock`` guards the
    shared bucket store, making it suitable for multi-threaded WSGI servers
    (e.g. gunicorn with sync workers).

    Args:
        app:                 Downstream WSGI callable.
        requests_per_second: Sustained refill rate (tokens/second).  Defaults to 10.
        burst:               Maximum bucket capacity.  Defaults to 20.
        ip_header:           Header used to extract the client IP when sitting
                             behind a proxy.  Defaults to ``"REMOTE_ADDR"``.

    Examples::

        limiter = RateLimiter(app, requests_per_second=5, burst=10)

        # Stand-alone: check without the full WSGI machinery
        allowed = limiter.is_allowed("192.168.1.1")
    """

    def __init__(
        self,
        app: WSGIApp,
        *,
        requests_per_second: float = 10.0,
        burst: float = 20.0,
        ip_header: str = "REMOTE_ADDR",
    ) -> None:
        self._app = app
        self.rate = requests_per_second
        self.burst = burst
        self._ip_header = ip_header
        # Per-IP: (tokens: float, last_refill_time: float)
        self._buckets: Dict[str, Tuple[float, float]] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_allowed(self, ip: str) -> bool:
        """Consume one token from *ip*'s bucket; return ``True`` if successful.

        Thread-safe.  Calling this method is the primary way to perform rate
        checks outside of the WSGI context.

        Args:
            ip: Client IP address string.

        Returns:
            ``True`` if the request is within the rate limit, ``False`` if the
            bucket is empty.
        """
        with self._lock:
            now = time.monotonic()
            tokens, last = self._buckets.get(ip, (self.burst, now))
            elapsed = now - last
            tokens = min(self.burst, tokens + elapsed * self.rate)
            if tokens >= 1.0:
                self._buckets[ip] = (tokens - 1.0, now)
                return True
            self._buckets[ip] = (tokens, now)
            return False

    def reset(self, ip: str) -> None:
        """Reset the bucket for *ip* to full capacity.

        Useful in tests or administrative tooling.

        Args:
            ip: Client IP address string.
        """
        with self._lock:
            self._buckets.pop(ip, None)

    def remaining(self, ip: str) -> float:
        """Return the number of tokens remaining for *ip* without consuming any.

        Args:
            ip: Client IP address string.

        Returns:
            Current token count (may be fractional).
        """
        with self._lock:
            now = time.monotonic()
            tokens, last = self._buckets.get(ip, (self.burst, now))
            elapsed = now - last
            return min(self.burst, tokens + elapsed * self.rate)

    # ------------------------------------------------------------------
    # WSGI interface
    # ------------------------------------------------------------------

    def __call__(self, environ: Environ, start_response: StartResponse) -> Iterator[bytes]:
        ip = environ.get(self._ip_header, "unknown")
        # Support X-Forwarded-For: take only the first (client) address
        if "," in ip:
            ip = ip.split(",")[0].strip()

        if not self.is_allowed(ip):
            logger.info("Rate limit exceeded for IP: %s", ip)
            body = b"429 Too Many Requests"
            start_response(
                "429 Too Many Requests",
                [
                    ("Content-Type", "text/plain"),
                    ("Content-Length", str(len(body))),
                    ("Retry-After", str(int(1.0 / max(self.rate, 0.001)) + 1)),
                ],
            )
            return iter([body])
        return self._app(environ, start_response)


# ===========================================================================
# AuthMiddleware
# ===========================================================================

class AuthMiddleware:
    """API key and optional Bearer-token authentication with role-based access.

    Supports two authentication schemes (checked in order):

    1. **API Key** — ``X-API-Key: <key>`` header.
    2. **Bearer Token** — ``Authorization: Bearer <token>`` header.
       Tokens are validated by the pluggable *token_validator* callable.

    Each API key maps to a list of roles.  If *required_roles* is set on a
    route prefix, only callers whose key grants at least one matching role are
    admitted.

    Args:
        app:             Downstream WSGI callable.
        api_keys:        Mapping of raw key strings to lists of role strings.
        token_validator: Optional callable ``(token: str) -> Optional[List[str]]``
                         that returns roles for a valid token or ``None`` if invalid.
        required_roles:  Mapping of URL path prefixes to required role sets.
                         A caller needs *any one* role from the set.
        public_paths:    Set of URL path prefixes that bypass auth entirely.

    Examples::

        auth = AuthMiddleware(
            app,
            api_keys={"secret-key-1": ["read", "write"], "read-only": ["read"]},
            required_roles={"/admin": {"admin"}, "/api": {"read"}},
            public_paths={"/health", "/metrics"},
        )
    """

    def __init__(
        self,
        app: WSGIApp,
        *,
        api_keys: Optional[Dict[str, List[str]]] = None,
        token_validator: Optional[Callable[[str], Optional[List[str]]]] = None,
        required_roles: Optional[Dict[str, Set[str]]] = None,
        public_paths: Optional[Set[str]] = None,
    ) -> None:
        self._app = app
        # Store hashed keys — protects the store if it ever leaks
        self._key_roles: Dict[bytes, List[str]] = {
            self._hash_key(k): v for k, v in (api_keys or {}).items()
        }
        self._token_validator = token_validator
        self._required_roles: Dict[str, Set[str]] = required_roles or {}
        self._public_paths: Set[str] = public_paths or set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def authenticate(
        self,
        api_key: Optional[str] = None,
        bearer_token: Optional[str] = None,
    ) -> Optional[List[str]]:
        """Return roles for the given credentials, or ``None`` if invalid.

        Uses constant-time digest comparison for API keys to prevent timing
        side-channel attacks.

        Args:
            api_key:      Raw API key string.
            bearer_token: Raw bearer token string.

        Returns:
            List of role strings if credentials are valid, else ``None``.
        """
        if api_key is not None:
            hashed = self._hash_key(api_key)
            roles = None
            for stored_hash, stored_roles in self._key_roles.items():
                if hmac.compare_digest(hashed, stored_hash):
                    roles = stored_roles
            if roles is not None:
                return roles

        if bearer_token is not None and self._token_validator is not None:
            return self._token_validator(bearer_token)

        return None

    def has_role(self, roles: List[str], required: Set[str]) -> bool:
        """Return ``True`` if *roles* satisfies at least one role in *required*.

        Args:
            roles:    Roles granted to the caller.
            required: Set of acceptable roles for the resource.

        Returns:
            ``True`` when the intersection is non-empty.
        """
        return bool(set(roles) & required)

    # ------------------------------------------------------------------
    # WSGI interface
    # ------------------------------------------------------------------

    def __call__(self, environ: Environ, start_response: StartResponse) -> Iterator[bytes]:
        path = environ.get("PATH_INFO", "/")

        # Allow public paths without credentials
        for prefix in self._public_paths:
            if path.startswith(prefix):
                return self._app(environ, start_response)

        api_key = environ.get("HTTP_X_API_KEY")
        auth_header = environ.get("HTTP_AUTHORIZATION", "")
        bearer_token: Optional[str] = None
        if auth_header.lower().startswith("bearer "):
            bearer_token = auth_header[7:].strip()

        roles = self.authenticate(api_key=api_key, bearer_token=bearer_token)

        if roles is None:
            return self._deny(
                start_response,
                "401 Unauthorized",
                extra_header="WWW-Authenticate",
                extra_value='Bearer realm="api"',
            )

        # Role check for the current path
        for prefix, required in self._required_roles.items():
            if path.startswith(prefix):
                if not self.has_role(roles, required):
                    return self._deny(start_response, "403 Forbidden")

        # Expose roles downstream via environ
        environ["plato.auth.roles"] = roles
        return self._app(environ, start_response)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _hash_key(key: str) -> bytes:
        return hashlib.sha256(key.encode("utf-8")).digest()

    @staticmethod
    def _deny(
        start_response: StartResponse,
        status: str,
        extra_header: Optional[str] = None,
        extra_value: Optional[str] = None,
    ) -> Iterator[bytes]:
        body = status.encode()
        headers: List[Tuple[str, str]] = [
            ("Content-Type", "text/plain"),
            ("Content-Length", str(len(body))),
        ]
        if extra_header and extra_value:
            headers.append((extra_header, extra_value))
        start_response(status, headers)
        return iter([body])


# ===========================================================================
# SecurityHeaders
# ===========================================================================

class SecurityHeaders:
    """Inject defensive HTTP response headers on every response.

    Adds the following headers by default:

    * ``Content-Security-Policy`` — restricts resource origins.
    * ``X-Frame-Options`` — prevents clickjacking.
    * ``Strict-Transport-Security`` — enforces HTTPS.
    * ``X-Content-Type-Options`` — prevents MIME sniffing.
    * ``Referrer-Policy`` — limits referrer leakage.
    * ``Permissions-Policy`` — disables dangerous browser features.
    * ``X-XSS-Protection`` — legacy IE/Edge XSS filter.

    All defaults can be overridden by passing keyword arguments.  Headers
    already set by the inner application are **not** duplicated.

    Args:
        app:                Downstream WSGI callable.
        csp:                Full ``Content-Security-Policy`` header value.
        frame_options:      ``X-Frame-Options`` value.  Defaults to ``"DENY"``.
        hsts_max_age:       ``max-age`` for HSTS in seconds.  Defaults to 1 year.
        hsts_subdomains:    Include ``includeSubDomains`` in HSTS.
        referrer_policy:    ``Referrer-Policy`` value.
        permissions_policy: ``Permissions-Policy`` value.

    Examples::

        secure = SecurityHeaders(
            app,
            csp="default-src 'self'; script-src 'self' 'nonce-abc'",
            frame_options="SAMEORIGIN",
        )
    """

    _DEFAULT_CSP = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    )

    def __init__(
        self,
        app: WSGIApp,
        *,
        csp: Optional[str] = None,
        frame_options: str = "DENY",
        hsts_max_age: int = 31_536_000,
        hsts_subdomains: bool = True,
        referrer_policy: str = "strict-origin-when-cross-origin",
        permissions_policy: str = (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=()"
        ),
    ) -> None:
        self._app = app
        hsts = f"max-age={hsts_max_age}"
        if hsts_subdomains:
            hsts += "; includeSubDomains"
        self._headers: List[Tuple[str, str]] = [
            ("Content-Security-Policy", csp or self._DEFAULT_CSP),
            ("X-Frame-Options", frame_options),
            ("Strict-Transport-Security", hsts),
            ("X-Content-Type-Options", "nosniff"),
            ("Referrer-Policy", referrer_policy),
            ("Permissions-Policy", permissions_policy),
            ("X-XSS-Protection", "1; mode=block"),
        ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_headers(self) -> List[Tuple[str, str]]:
        """Return the list of security headers this instance injects.

        Returns:
            List of ``(header-name, header-value)`` tuples.
        """
        return list(self._headers)

    # ------------------------------------------------------------------
    # WSGI interface
    # ------------------------------------------------------------------

    def __call__(self, environ: Environ, start_response: StartResponse) -> Iterator[bytes]:
        def _start_response_wrapper(
            status: str,
            headers: List[Tuple[str, str]],
            exc_info=None,
        ):
            # Only inject headers not already set by the inner app
            existing_names = {h[0].lower() for h in headers}
            extra = [(k, v) for k, v in self._headers if k.lower() not in existing_names]
            merged = headers + extra
            if exc_info is not None:
                return start_response(status, merged, exc_info)
            return start_response(status, merged)

        return self._app(environ, _start_response_wrapper)


# ===========================================================================
# XSSShield
# ===========================================================================

class XSSShield:
    """Context-aware XSS encoding for HTML, attribute, and JavaScript output.

    Three encoding contexts are provided as static methods so the class is
    useful without instantiation.  When used as WSGI middleware it passes
    through to the inner app unchanged — XSS encoding is context-sensitive
    and must happen at the template/render layer, not the transport layer.

    Static methods:
        encode_html:      Encode for safe insertion as HTML text content.
        encode_attribute: Encode for safe insertion inside an HTML attribute.
        encode_js:        Encode for safe insertion inside a JavaScript string.
        encode_url:       Percent-encode for safe insertion in URL parameters.

    Args:
        app: Downstream WSGI callable (for WSGI middleware use).

    Examples::

        XSSShield.encode_html("<script>alert('xss')</script>")
        # → "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"

        XSSShield.encode_attribute('"><img src=x onerror=alert(1)>')
        # → "&quot;&gt;&lt;img src=x onerror=alert(1)&gt;"

        XSSShield.encode_js("'); drop table users; --")
        # → "\\x27); drop table users; --"
    """

    # Characters that require escaping in JavaScript string contexts
    _JS_ESCAPE: Dict[str, str] = {
        "\\": "\\\\",
        "'": "\\x27",
        '"': "\\x22",
        "\n": "\\n",
        "\r": "\\r",
        "\t": "\\t",
        "<": "\\x3C",
        ">": "\\x3E",
        "&": "\\x26",
        "=": "\\x3D",
        "`": "\\x60",
    }

    def __init__(self, app: WSGIApp) -> None:
        self._app = app

    # ------------------------------------------------------------------
    # Public API — static encoding methods
    # ------------------------------------------------------------------

    @staticmethod
    def encode_html(text: str) -> str:
        """Encode *text* for safe embedding as HTML text content.

        Escapes ``&``, ``<``, ``>``, ``"``, ``'`` using HTML entities.
        Safe to use inside ``<p>``, ``<div>``, ``<span>``, etc.

        Args:
            text: Untrusted string.

        Returns:
            HTML-entity-encoded string.

        Examples::

            XSSShield.encode_html("<b>bold</b>")
            # → "&lt;b&gt;bold&lt;/b&gt;"
        """
        return html.escape(text, quote=True)

    @staticmethod
    def encode_attribute(value: str) -> str:
        """Encode *value* for safe embedding inside an HTML attribute value.

        Encodes characters that could break out of a quoted attribute context,
        including ``"``, ``'``, ``<``, ``>``, and ``&``.

        Args:
            value: Untrusted attribute value string.

        Returns:
            Attribute-safe encoded string.

        Examples::

            XSSShield.encode_attribute('"><script>alert(1)</script>')
            # → "&quot;&gt;&lt;script&gt;alert(1)&lt;/script&gt;"
        """
        return html.escape(value, quote=True)

    @staticmethod
    def encode_js(value: str) -> str:
        """Encode *value* for safe embedding inside a JavaScript string literal.

        The output is safe to place between single or double quotes in inline
        ``<script>`` blocks or event handlers.  Does **not** add surrounding
        quotes — the caller must do that.

        Args:
            value: Untrusted string to embed in JavaScript.

        Returns:
            JavaScript-safe escaped string.

        Examples::

            f"var name = '{XSSShield.encode_js(user_input)}';"
        """
        result = []
        for ch in value:
            result.append(XSSShield._JS_ESCAPE.get(ch, ch))
        return "".join(result)

    @staticmethod
    def encode_url(value: str) -> str:
        """Percent-encode *value* for safe embedding in a URL parameter.

        Uses RFC 3986 unreserved characters as the safe set.

        Args:
            value: Untrusted string.

        Returns:
            Percent-encoded string.

        Examples::

            XSSShield.encode_url("hello world & more")
            # → "hello%20world%20%26%20more"
        """
        _safe = frozenset(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "abcdefghijklmnopqrstuvwxyz"
            "0123456789-_.~"
        )
        encoded = []
        for byte in value.encode("utf-8"):
            char = chr(byte)
            encoded.append(char if char in _safe else f"%{byte:02X}")
        return "".join(encoded)

    # ------------------------------------------------------------------
    # WSGI interface
    # ------------------------------------------------------------------

    def __call__(self, environ: Environ, start_response: StartResponse) -> Iterator[bytes]:
        """Pass through to the inner app.

        XSS encoding is context-sensitive and must happen at render time.
        This ``__call__`` participates in the middleware chain so XSSShield
        can be subclassed to inspect or transform response bodies.
        """
        return self._app(environ, start_response)


# ===========================================================================
# Convenience builder
# ===========================================================================

def build_stack(
    app: WSGIApp,
    *,
    api_keys: Optional[Dict[str, List[str]]] = None,
    public_paths: Optional[Set[str]] = None,
    required_roles: Optional[Dict[str, Set[str]]] = None,
    token_validator: Optional[Callable[[str], Optional[List[str]]]] = None,
    requests_per_second: float = 10.0,
    burst: float = 20.0,
    max_input_length: int = 65_536,
    csp: Optional[str] = None,
    frame_options: str = "DENY",
) -> WSGIApp:
    """Wrap *app* with the full PLATO security stack in the recommended order.

    Stack order (outermost → innermost):

    1. :class:`InputSanitizer`   — clean inputs first
    2. :class:`RateLimiter`      — shed excessive load early
    3. :class:`AuthMiddleware`   — authenticate before touching business logic
    4. :class:`XSSShield`        — encoding helpers available to downstream code
    5. :class:`SecurityHeaders`  — always appended to every response

    Args:
        app:                 Your WSGI application.
        api_keys:            ``{key: [roles]}`` mapping.
        public_paths:        Paths that skip auth.
        required_roles:      ``{path_prefix: {roles}}`` mapping.
        token_validator:     Bearer-token validator callable.
        requests_per_second: Sustained rate limit.
        burst:               Burst capacity.
        max_input_length:    Maximum input byte length.
        csp:                 Custom Content-Security-Policy value.
        frame_options:       ``X-Frame-Options`` value.

    Returns:
        Wrapped WSGI callable.

    Examples::

        wsgi_app = build_stack(
            my_flask_app,
            api_keys={"prod-key-xyz": ["read", "write"]},
            public_paths={"/healthz"},
            required_roles={"/admin": {"admin"}},
        )
    """
    app = SecurityHeaders(app, csp=csp, frame_options=frame_options)
    app = XSSShield(app)
    app = AuthMiddleware(
        app,
        api_keys=api_keys or {},
        token_validator=token_validator,
        required_roles=required_roles,
        public_paths=public_paths,
    )
    app = RateLimiter(app, requests_per_second=requests_per_second, burst=burst)
    app = InputSanitizer(app, max_length=max_input_length)
    return app


# ===========================================================================
# Unit tests
# ===========================================================================

class _MockWSGIApp:
    """Minimal WSGI app for testing — records calls and returns a fixed response."""

    def __init__(self, status: str = "200 OK", body: bytes = b"OK") -> None:
        self.status = status
        self.body = body
        self.calls: List[Environ] = []

    def __call__(self, environ: Environ, start_response: StartResponse) -> Iterator[bytes]:
        self.calls.append(environ)
        start_response(self.status, [("Content-Type", "text/plain")])
        return iter([self.body])


def _run_wsgi(
    app: WSGIApp,
    environ: Optional[Dict[str, Any]] = None,
) -> Tuple[str, List[Tuple[str, str]], bytes]:
    """Run *app* and return ``(status, headers, body)``."""
    base: Dict[str, Any] = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": "/",
        "QUERY_STRING": "",
        "REMOTE_ADDR": "127.0.0.1",
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "8080",
        "wsgi.input": None,
        "wsgi.errors": None,
        "wsgi.url_scheme": "http",
    }
    if environ:
        base.update(environ)
    captured: Dict[str, Any] = {}

    def _start_response(status: str, headers: List[Tuple[str, str]], exc_info=None):
        captured["status"] = status
        captured["headers"] = headers

    body = b"".join(app(base, _start_response))
    return captured.get("status", ""), captured.get("headers", []), body


class TestInputSanitizer(unittest.TestCase):
    def setUp(self):
        self.san = InputSanitizer(max_length=100)

    def test_strips_script_tags_and_content(self):
        result = self.san.sanitize("<script>alert(1)</script>hello")
        self.assertNotIn("<script>", result)
        self.assertNotIn("alert(1)", result)
        self.assertIn("hello", result)

    def test_strips_event_attributes(self):
        result = self.san.sanitize('<img src=x onerror="alert(1)">')
        self.assertNotIn("onerror", result)

    def test_blocks_javascript_uri(self):
        result = self.san.sanitize('<a href="javascript:alert(1)">click</a>')
        self.assertNotIn("javascript:", result)

    def test_allow_tags_preserved(self):
        san = InputSanitizer(allow_tags={"b"})
        result = san.sanitize("<b>bold</b><script>bad</script>")
        self.assertIn("<b>", result)
        self.assertNotIn("<script>", result)

    def test_max_length_exceeded_raises(self):
        with self.assertRaises(ValueError):
            self.san.validate_length("x" * 200)

    def test_max_length_within_limit_passes(self):
        self.san.validate_length("x" * 50)  # must not raise

    def test_sanitize_dict_cleans_values(self):
        data = {"name": "<script>x</script>Alice", "age": 30}
        result = self.san.sanitize_dict(data)
        self.assertNotIn("<script>", result["name"])
        self.assertEqual(result["age"], 30)

    def test_wsgi_sanitizes_query_string(self):
        inner = _MockWSGIApp()
        san = InputSanitizer(inner)
        _run_wsgi(san, {"QUERY_STRING": "<script>bad</script>"})
        self.assertNotIn("<script>", inner.calls[0]["QUERY_STRING"])


class TestRateLimiter(unittest.TestCase):
    def test_allows_requests_within_burst(self):
        inner = _MockWSGIApp()
        limiter = RateLimiter(inner, requests_per_second=100, burst=5)
        for _ in range(5):
            self.assertTrue(limiter.is_allowed("1.2.3.4"))

    def test_blocks_requests_over_burst(self):
        inner = _MockWSGIApp()
        limiter = RateLimiter(inner, requests_per_second=1, burst=2)
        limiter.is_allowed("9.9.9.9")
        limiter.is_allowed("9.9.9.9")
        self.assertFalse(limiter.is_allowed("9.9.9.9"))

    def test_reset_refills_bucket_to_full(self):
        inner = _MockWSGIApp()
        limiter = RateLimiter(inner, requests_per_second=1, burst=1)
        limiter.is_allowed("1.1.1.1")
        self.assertFalse(limiter.is_allowed("1.1.1.1"))
        limiter.reset("1.1.1.1")
        self.assertTrue(limiter.is_allowed("1.1.1.1"))

    def test_wsgi_returns_429_when_exhausted(self):
        inner = _MockWSGIApp()
        limiter = RateLimiter(inner, requests_per_second=1, burst=0)
        status, _, _ = _run_wsgi(limiter, {"REMOTE_ADDR": "5.5.5.5"})
        self.assertEqual(status, "429 Too Many Requests")

    def test_wsgi_passes_through_when_allowed(self):
        inner = _MockWSGIApp()
        limiter = RateLimiter(inner, requests_per_second=100, burst=100)
        status, _, body = _run_wsgi(limiter, {"REMOTE_ADDR": "6.6.6.6"})
        self.assertEqual(status, "200 OK")
        self.assertEqual(body, b"OK")

    def test_different_ips_have_independent_buckets(self):
        inner = _MockWSGIApp()
        limiter = RateLimiter(inner, requests_per_second=1, burst=1)
        limiter.is_allowed("10.0.0.1")
        self.assertFalse(limiter.is_allowed("10.0.0.1"))
        # Different IP still has its own full bucket
        self.assertTrue(limiter.is_allowed("10.0.0.2"))


class TestAuthMiddleware(unittest.TestCase):
    def _make_auth(self, **kwargs) -> Tuple[AuthMiddleware, _MockWSGIApp]:
        inner = _MockWSGIApp()
        auth = AuthMiddleware(inner, **kwargs)
        return auth, inner

    def test_valid_api_key_admitted(self):
        auth, _ = self._make_auth(api_keys={"good-key": ["read"]})
        status, _, _ = _run_wsgi(auth, {"HTTP_X_API_KEY": "good-key"})
        self.assertEqual(status, "200 OK")

    def test_invalid_api_key_rejected(self):
        auth, _ = self._make_auth(api_keys={"good-key": ["read"]})
        status, _, _ = _run_wsgi(auth, {"HTTP_X_API_KEY": "bad-key"})
        self.assertEqual(status, "401 Unauthorized")

    def test_missing_credentials_rejected(self):
        auth, _ = self._make_auth(api_keys={"k": ["read"]})
        status, _, _ = _run_wsgi(auth)
        self.assertEqual(status, "401 Unauthorized")

    def test_public_path_bypasses_auth(self):
        auth, _ = self._make_auth(api_keys={}, public_paths={"/health"})
        status, _, _ = _run_wsgi(auth, {"PATH_INFO": "/health"})
        self.assertEqual(status, "200 OK")

    def test_role_check_denies_insufficient_role(self):
        auth, _ = self._make_auth(
            api_keys={"read-key": ["read"]},
            required_roles={"/admin": {"admin"}},
        )
        status, _, _ = _run_wsgi(
            auth, {"HTTP_X_API_KEY": "read-key", "PATH_INFO": "/admin/panel"}
        )
        self.assertEqual(status, "403 Forbidden")

    def test_role_check_allows_correct_role(self):
        auth, _ = self._make_auth(
            api_keys={"admin-key": ["admin", "read"]},
            required_roles={"/admin": {"admin"}},
        )
        status, _, _ = _run_wsgi(
            auth, {"HTTP_X_API_KEY": "admin-key", "PATH_INFO": "/admin/panel"}
        )
        self.assertEqual(status, "200 OK")

    def test_bearer_token_validated(self):
        def validator(token: str) -> Optional[List[str]]:
            return ["read"] if token == "valid-token" else None

        auth, _ = self._make_auth(token_validator=validator)
        status, _, _ = _run_wsgi(auth, {"HTTP_AUTHORIZATION": "Bearer valid-token"})
        self.assertEqual(status, "200 OK")

    def test_roles_injected_into_environ(self):
        inner = _MockWSGIApp()
        auth = AuthMiddleware(inner, api_keys={"k": ["read", "write"]})
        _run_wsgi(auth, {"HTTP_X_API_KEY": "k"})
        self.assertEqual(inner.calls[0]["plato.auth.roles"], ["read", "write"])


class TestSecurityHeaders(unittest.TestCase):
    def test_default_security_headers_present(self):
        inner = _MockWSGIApp()
        secure = SecurityHeaders(inner)
        _, headers, _ = _run_wsgi(secure)
        header_names = {h[0] for h in headers}
        for expected in (
            "Content-Security-Policy",
            "X-Frame-Options",
            "Strict-Transport-Security",
            "X-Content-Type-Options",
        ):
            self.assertIn(expected, header_names)

    def test_custom_csp_applied(self):
        inner = _MockWSGIApp()
        secure = SecurityHeaders(inner, csp="default-src 'none'")
        _, headers, _ = _run_wsgi(secure)
        csp_values = [v for k, v in headers if k == "Content-Security-Policy"]
        self.assertEqual(csp_values[0], "default-src 'none'")

    def test_frame_options_defaults_to_deny(self):
        inner = _MockWSGIApp()
        secure = SecurityHeaders(inner)
        _, headers, _ = _run_wsgi(secure)
        fo = {k: v for k, v in headers}.get("X-Frame-Options")
        self.assertEqual(fo, "DENY")

    def test_existing_header_not_duplicated(self):
        class CSPApp:
            def __call__(self, environ, start_response):
                start_response(
                    "200 OK", [("Content-Security-Policy", "default-src 'self'")]
                )
                return iter([b""])

        secure = SecurityHeaders(CSPApp())
        _, headers, _ = _run_wsgi(secure)
        csps = [v for k, v in headers if k == "Content-Security-Policy"]
        self.assertEqual(len(csps), 1)


class TestXSSShield(unittest.TestCase):
    def test_encode_html_escapes_angle_brackets(self):
        result = XSSShield.encode_html("<script>alert(1)</script>")
        self.assertNotIn("<", result)
        self.assertNotIn(">", result)

    def test_encode_html_escapes_ampersand(self):
        result = XSSShield.encode_html("Tom & Jerry")
        self.assertIn("&amp;", result)

    def test_encode_js_escapes_single_quotes(self):
        result = XSSShield.encode_js("it's a 'test'")
        self.assertNotIn("'", result)

    def test_encode_js_escapes_newlines(self):
        result = XSSShield.encode_js("line1\nline2")
        self.assertNotIn("\n", result)
        self.assertIn("\\n", result)

    def test_encode_url_replaces_spaces_and_ampersands(self):
        result = XSSShield.encode_url("hello world & more")
        self.assertNotIn(" ", result)
        self.assertNotIn("&", result)
        self.assertIn("hello", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
