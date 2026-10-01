"""Web Push (RFC 8030, 8291, 8292): a message for a browser that subscribed goes to its push service
(Apple's, Google's, Mozilla's), encrypted for that browser and signed with the app's VAPID key."""

import base64
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import http_ece
import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from py_vapid import Vapid02

# Where browsers' push services live; the app posts only there, whatever endpoint a client sends.
PUSH_SERVICES = ("push.apple.com", "fcm.googleapis.com", "android.googleapis.com", "push.services.mozilla.com",
                 "notify.windows.com")


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def unb64url(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def is_push_service(endpoint: str) -> bool:
    url = urlsplit(endpoint)
    host = (url.hostname or "").lower()
    return url.scheme == "https" and any(host == s or host.endswith("." + s) for s in PUSH_SERVICES)


def new_vapid_key() -> tuple[str, str]:
    """(the private key as PEM, the public key as the browser takes it: base64url of the raw point)."""
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    point = key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return pem.decode(), b64url(point)


@dataclass(frozen=True)
class PushTarget:
    endpoint: str
    p256dh: str
    auth: str


class WebPushClient:
    """Created once per app (lifespan) and injected: one connection pool for all pushes."""

    def __init__(self, private_pem: str, contact: str, http: httpx.AsyncClient | None = None):
        self.vapid = Vapid02.from_pem(private_pem.encode())
        self.contact = contact      # VAPID "sub": how a push service reaches whoever sends (https: or mailto:)
        self.http = http or httpx.AsyncClient(timeout=15)

    async def send(self, target: PushTarget, payload: dict[str, Any], ttl: int = 600) -> bool:
        """One message. False when the subscription is gone for good (404/410): it's to be forgotten."""
        body = http_ece.encrypt(
            json.dumps(payload, ensure_ascii=False).encode(), private_key=ec.generate_private_key(ec.SECP256R1()),
            dh=unb64url(target.p256dh), auth_secret=unb64url(target.auth), version="aes128gcm")
        url = urlsplit(target.endpoint)
        headers = self.vapid.sign({"aud": f"{url.scheme}://{url.netloc}", "sub": self.contact,
                                   "exp": int(time.time()) + 3600})
        headers |= {"Content-Encoding": "aes128gcm", "Content-Type": "application/octet-stream",
                    "TTL": str(ttl), "Urgency": "high"}   # high: delivered at once, even to a phone saving power
        resp = await self.http.post(target.endpoint, content=body, headers=headers)
        if resp.status_code in (404, 410):
            return False
        resp.raise_for_status()
        return True

    async def aclose(self) -> None:
        await self.http.aclose()
