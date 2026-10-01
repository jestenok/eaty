"""The Web Push client: what reaches a push service is what a browser can decrypt, signed with the app's key."""

import json
import os

import http_ece
import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.clients.web_push import PushTarget, WebPushClient, b64url, is_push_service, new_vapid_key, unb64url


def browser():
    """A browser's subscription keys, as PushSubscription.toJSON() gives them, and its private key."""
    key = ec.generate_private_key(ec.SECP256R1())
    point = key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    auth = os.urandom(16)
    return key, auth, PushTarget("https://web.push.apple.com/QGuF2w", b64url(point), b64url(auth))


async def test_a_push_is_encrypted_for_the_browser_and_signed_with_the_app_key():
    private_pem, public_key = new_vapid_key()
    browser_key, auth, target = browser()
    seen = []

    def push_service(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(201)

    client = WebPushClient(private_pem, "https://eaty.lol", httpx.AsyncClient(transport=httpx.MockTransport(push_service)))
    payload = {"title": "Готово!", "body": "Паста · шаг 3", "tag": "timer:12:2", "url": "/#/recipe/12"}
    assert await client.send(target, payload)

    request = seen[0]
    assert str(request.url) == target.endpoint
    assert (request.headers["content-encoding"], request.headers["ttl"], request.headers["urgency"]) == \
        ("aes128gcm", "600", "high")
    plain = http_ece.decrypt(request.content, private_key=browser_key, auth_secret=auth, version="aes128gcm")
    assert json.loads(plain) == payload

    scheme, _, params = request.headers["authorization"].partition(" ")
    fields = dict(part.split("=", 1) for part in params.split(","))
    assert scheme == "vapid" and fields["k"] == public_key
    vapid = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), unb64url(public_key))
    claims = jwt.decode(fields["t"], vapid, algorithms=["ES256"], audience="https://web.push.apple.com")
    assert claims["sub"] == "https://eaty.lol"


async def test_a_gone_subscription_says_so():
    private_pem, _ = new_vapid_key()
    *_, target = browser()
    for status, alive in [(410, False), (404, False), (201, True)]:
        transport = httpx.MockTransport(lambda request, status=status: httpx.Response(status))
        client = WebPushClient(private_pem, "mailto:eaty@localhost", httpx.AsyncClient(transport=transport))
        assert await client.send(target, {"title": "x"}) is alive


def test_pushes_go_only_to_browsers_push_services():
    assert is_push_service("https://web.push.apple.com/QGuF2w")
    assert is_push_service("https://fcm.googleapis.com/fcm/send/abc")
    assert is_push_service("https://updates.push.services.mozilla.com/wpush/v2/abc")
    for endpoint in ["http://web.push.apple.com/x", "https://push.apple.com.evil.example/x", "https://evil.example/push.apple.com",
                     "https://localhost:5432/", "https://xpush.apple.com/"]:
        assert not is_push_service(endpoint), endpoint
