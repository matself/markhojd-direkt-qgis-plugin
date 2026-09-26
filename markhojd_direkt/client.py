"""Klient mot Markhöjd Direkt (REST/JSON) via QGIS autentiseringsdatabas (OAuth2)."""

import json
import time

from qgis.core import QgsBlockingNetworkRequest
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


class MarkhojdClient:
    def __init__(self, authcfg, environment="production", min_interval=0.2):
        self.authcfg = authcfg
        self.base_url = BASE_URLS[environment]
        self.min_interval = min_interval
        self._last = 0.0

    def _request(self, path, body=None):
        url = self.base_url + path
        for attempt in range(1, MAX_RETRIES + 1):
            wait = self.min_interval - (time.monotonic() - self._last)
            if wait > 0:
                _pause(wait)
            req = QNetworkRequest(QUrl(url))
            req.setRawHeader(b"Accept", b"application/json")
            br = QgsBlockingNetworkRequest()
            if self.authcfg:
                br.setAuthCfg(self.authcfg)
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
            # Tjänsten strypt eller tillfälligt otillgänglig: vänta och försök igen
            if status in (429, 503) and attempt < MAX_RETRIES:
                retry_after = bytes(reply.rawHeader(b"Retry-After")).decode() or ""
                delay = float(retry_after) if retry_after.replace(".", "").isdigit() else 2.0 * attempt
                _pause(min(delay, 60))
                continue
            if status == 401 or status == 403:
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
