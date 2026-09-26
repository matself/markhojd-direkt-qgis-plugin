"""Klient mot Markhöjd Direkt (REST/JSON).

Nyckeln (consumer key/secret) läses ur QGIS autentiseringsdatabas, men token hämtas här
(OAuth2 client credentials) och skickas som Bearer-header. QGIS egen OAuth2-metod undviks
eftersom den kraschade QGIS vid anrop från kartverktyg.
"""

import base64
import json
import time

from qgis.core import QgsApplication, QgsAuthMethodConfig, QgsBlockingNetworkRequest
from qgis.PyQt.QtCore import QEventLoop, QTimer, QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest

from . import core

BASE_URLS = {
    "production": "https://api.lantmateriet.se/distribution/produkter/markhojd/v1",
    "verification": "https://api-ver.lantmateriet.se/distribution/produkter/markhojd/v1",
}
AUTH_URLS = {
    "production": "https://apimanager.lantmateriet.se/oauth2/",
    "verification": "https://apimanager-ver.lantmateriet.se/oauth2/",
}

MAX_RETRIES = 5


class MarkhojdError(Exception):
    pass


def _pause(seconds):
    """Vänta utan att frysa gränssnittet."""
    loop = QEventLoop()
    QTimer.singleShot(int(seconds * 1000), loop.quit)
    loop.exec()


def load_credentials(authcfg):
    """(client id, secret) ur en autentiseringskonfiguration (OAuth2 eller Basic)."""
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
        raise MarkhojdError("Konfigurationen saknar consumer key/secret. Använd 'Ny nyckel…'.")
    return cid, secret


class MarkhojdClient:
    def __init__(self, authcfg, environment="production", min_interval=0.2):
        self.authcfg = authcfg
        self.base_url = BASE_URLS[environment]
        self.token_url = AUTH_URLS[environment] + "token"
        self.min_interval = min_interval
        self._last = 0.0
        self._token = None
        self._token_expires = 0.0

    def _get_token(self, force=False):
        if not self.authcfg:
            return None
        if self._token and not force and time.monotonic() < self._token_expires:
            return self._token
        cid, secret = load_credentials(self.authcfg)
        req = QNetworkRequest(QUrl(self.token_url))
        req.setHeader(QNetworkRequest.ContentTypeHeader, "application/x-www-form-urlencoded")
        basic = base64.b64encode(f"{cid}:{secret}".encode()).decode()
        req.setRawHeader(b"Authorization", f"Basic {basic}".encode())
        br = QgsBlockingNetworkRequest()
        err = br.post(req, b"grant_type=client_credentials")
        reply = br.reply()
        text = bytes(reply.content()).decode("utf-8", errors="replace")
        status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        if err != QgsBlockingNetworkRequest.NoError or status != 200:
            raise MarkhojdError(
                f"Kunde inte hämta åtkomsttoken (HTTP {status}). Kontrollera consumer key/secret och miljö. "
                + (text[:200] if text else br.errorMessage())
            )
        try:
            data = json.loads(text)
            self._token = data["access_token"]
        except (ValueError, KeyError):
            raise MarkhojdError("Oväntat svar från token-tjänsten.")
        # marginal på 60 s
        self._token_expires = time.monotonic() + max(30, float(data.get("expires_in", 300)) - 60)
        return self._token

    def _request(self, path, body=None):
        url = self.base_url + path
        refreshed = False
        for attempt in range(1, MAX_RETRIES + 1):
            wait = self.min_interval - (time.monotonic() - self._last)
            if wait > 0:
                _pause(wait)
            req = QNetworkRequest(QUrl(url))
            req.setRawHeader(b"Accept", b"application/json")
            token = self._get_token()
            if token:
                req.setRawHeader(b"Authorization", f"Bearer {token}".encode())
            br = QgsBlockingNetworkRequest()
            if body is None:
                err = br.get(req)
            else:
                req.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")
                err = br.post(req, body)
            self._last = time.monotonic()

            reply = br.reply()
            status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
            text = bytes(reply.content()).decode("utf-8", errors="replace")
            if err == QgsBlockingNetworkRequest.NoError and status in (None, 200):
                try:
                    return json.loads(text)
                except ValueError as e:
                    raise MarkhojdError(f"Ogiltigt svar från tjänsten: {e}")
            if status == 401 and token and not refreshed:  # token kan ha gått ut
                refreshed = True
                self._get_token(force=True)
                continue
            # Tjänsten strypt eller tillfälligt otillgänglig: vänta och försök igen
            if status in (429, 503) and attempt < MAX_RETRIES:
                retry_after = bytes(reply.rawHeader(b"Retry-After")).decode() or ""
                delay = float(retry_after) if retry_after.replace(".", "").isdigit() else 2.0 * attempt
                _pause(min(delay, 60))
                continue
            if status in (401, 403):
                raise MarkhojdError(
                    f"Åtkomst nekad ({status}). Kontrollera att systemkontot har beställt "
                    "Markhöjd Direkt och att rätt miljö (produktion/verifiering) är vald."
                )
            detail = core.parse_fault(text) or br.errorMessage()
            raise MarkhojdError(f"HTTP {status}: {detail}")
        raise MarkhojdError("Tjänsten svarade inte efter flera försök.")

    def health(self):
        return bool(self._request("/health").get("up"))

    def get_height(self, e, n):
        """Höjd (m) för en punkt i SWEREF 99 TM, eller None om data saknas."""
        payload = self._request(f"/hojd?srid={core.SRID}&e={e:.3f}&n={n:.3f}")
        res = core.parse_heights(payload)
        return res[0][2] if res else None

    def get_heights(self, points):
        """Höjder för högst 1 000 punkter (e, n) i ett anrop. Returnerar (e, n, z|None)."""
        if len(points) > core.MAX_POINTS_PER_REQUEST:
            raise ValueError("För många punkter i ett anrop")
        return core.parse_heights(self._request("/hojd", core.build_multipoint_body(points)))
