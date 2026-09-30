"""Client for the Markhöjd Direkt service (REST/JSON).

The service is called with HTTP Basic (username/password of the system account), the same way
as in HAJK. The credentials are read from the QGIS authentication database and sent as an
Authorization header. QGIS's own network and authentication handling is avoided: it crashed
QGIS and opens login dialogs on 401.
"""

import base64
import json
import time

from qgis.core import QgsApplication, QgsAuthMethodConfig, QgsNetworkAccessManager
from qgis.PyQt.QtCore import QEventLoop, QTimer, QUrl
from qgis.PyQt.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from . import core

BASE_URLS = {
    "production": "https://api.lantmateriet.se/distribution/produkter/markhojd/v1",
    "verification": "https://api-ver.lantmateriet.se/distribution/produkter/markhojd/v1",
}
MAX_RETRIES = 5


class MarkhojdError(Exception):
    pass


def _pause(seconds):
    """Wait without freezing the user interface."""
    loop = QEventLoop()
    QTimer.singleShot(int(seconds * 1000), loop.quit)
    loop.exec()


def load_credentials(authcfg):
    """(username, password) from an authentication configuration (Basic, or key/secret from OAuth2)."""
    cfg = QgsAuthMethodConfig()
    QgsApplication.authManager().loadAuthenticationConfig(authcfg, cfg, True)
    if not cfg.isValid():
        raise MarkhojdError("Autentiseringskonfigurationen hittades inte.")
    if cfg.method() == "OAuth2":
        try:
            data = json.loads(cfg.config("oauth2config") or "{}")
        except ValueError:
            data = {}
        cid, secret = data.get("clientId"), data.get("clientSecret")
    else:
        cid, secret = cfg.config("username"), cfg.config("password")
    if not cid or not secret:
        raise MarkhojdError("Konfigurationen saknar användarnamn/lösenord. Använd 'Ny nyckel…'.")
    return cid, secret


TIMEOUT_MS = 60_000


class MarkhojdClient:
    def __init__(self, authcfg, environment="production", min_interval=0.2):
        self.authcfg = authcfg
        self.base_url = BASE_URLS[environment]
        self.min_interval = min_interval
        self._last = 0.0
        self._basic = None
        self._nam = QNetworkAccessManager()
        self._nam.setProxy(QgsNetworkAccessManager.instance().fallbackProxy())

    def _auth_header(self):
        if not self.authcfg:
            return None
        if self._basic is None:
            user, password = load_credentials(self.authcfg)
            self._basic = base64.b64encode(f"{user}:{password}".encode()).decode()
        return f"Basic {self._basic}".encode()

    def _request(self, path, body=None):
        url = self.base_url + path
        for attempt in range(1, MAX_RETRIES + 1):
            wait = self.min_interval - (time.monotonic() - self._last)
            if wait > 0:
                _pause(wait)
            req = QNetworkRequest(QUrl(url))
            req.setRawHeader(b"Accept", b"application/json")
            auth = self._auth_header()
            if auth:
                req.setRawHeader(b"Authorization", auth)
            if body is None:
                reply = self._nam.get(req)
            else:
                req.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
                reply = self._nam.post(req, body)
            loop = QEventLoop()
            reply.finished.connect(loop.quit)
            QTimer.singleShot(TIMEOUT_MS, loop.quit)
            loop.exec()
            if not reply.isFinished():
                reply.abort()
            self._last = time.monotonic()

            status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
            text = bytes(reply.readAll()).decode("utf-8", errors="replace")
            retry_after = bytes(reply.rawHeader(b"Retry-After")).decode()
            net_error = reply.errorString() if reply.error() != QNetworkReply.NetworkError.NoError else ""
            reply.deleteLater()
            if status == 200:
                try:
                    return json.loads(text)
                except ValueError as e:
                    raise MarkhojdError(f"Ogiltigt svar från tjänsten: {e}")
            # Service throttled or temporarily unavailable: wait and retry
            if status in (429, 503) and attempt < MAX_RETRIES:
                delay = float(retry_after) if retry_after.replace(".", "").isdigit() else 2.0 * attempt
                _pause(min(delay, 60))
                continue
            if status in (401, 403):
                raise MarkhojdError(
                    f"Åtkomst nekad ({status}). Kontrollera användarnamn/lösenord och att systemkontot har beställt "
                    "Markhöjd Direkt och att rätt miljö (produktion/verifiering) är vald."
                )
            detail = core.parse_fault(text) or net_error
            raise MarkhojdError(f"HTTP {status}: {detail}" if status else f"Nätverksfel: {detail}")
        raise MarkhojdError("Tjänsten svarade inte efter flera försök.")

    def health(self):
        return bool(self._request("/health").get("up"))

    def get_height(self, e, n):
        """Height (m) for a point in SWEREF 99 TM, or None if there is no data."""
        payload = self._request(f"/hojd?srid={core.SRID}&e={e:.3f}&n={n:.3f}")
        res = core.parse_heights(payload)
        return res[0][2] if res else None

    def get_heights(self, points):
        """Heights for at most 1000 points (e, n) in one request. Returns (e, n, z|None)."""
        if len(points) > core.MAX_POINTS_PER_REQUEST:
            raise ValueError("För många punkter i ett anrop")
        return core.parse_heights(self._request("/hojd", core.build_multipoint_body(points)))
