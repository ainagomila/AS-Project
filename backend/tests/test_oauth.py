import base64
import hashlib
import secrets
from urllib.parse import parse_qs, urlencode, urlparse

import pytest
from django.test import Client
from oauth2_provider.models import Application

from .conftest import DNI_A, PASSWORD

pytestmark = pytest.mark.django_db

REDIRECT = "https://localhost:8080/noexist/callback"


@pytest.fixture
def oauth_app():
    return Application.objects.create(
        name="Kofre test",
        client_id="kofre-test",
        client_type=Application.CLIENT_PUBLIC,
        authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
        redirect_uris=REDIRECT,
        skip_authorization=True,    # skip the consent screen
        algorithm=Application.RS256_ALGORITHM,
    )


def pkce_pair():
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def authorize(client, challenge=None):
    params = {"response_type": "code", "client_id": "kofre-test", "redirect_uri": REDIRECT}
    if challenge:
        params |= {"code_challenge": challenge, "code_challenge_method": "S256"}
    return client.get("/o/authorize/?" + urlencode(params))


def exchange(client, code, verifier):
    body = urlencode({
        "grant_type": "authorization_code", "code": code, "code_verifier": verifier,
        "redirect_uri": REDIRECT, "client_id": "kofre-test",
    })
    return client.post("/o/token/", body, content_type="application/x-www-form-urlencoded")


def logged_in_client(ana):
    c = Client()
    assert c.login(username=DNI_A, password=PASSWORD)
    return c


def test_login_page_renders():
    response = Client().get("/accounts/login/")
    assert response.status_code == 200
    assert b"csrfmiddlewaretoken" in response.content


def test_authorize_without_session_redirects_to_login(oauth_app):
    _, challenge = pkce_pair()
    response = authorize(Client(), challenge)
    assert response.status_code == 302
    assert response["Location"].startswith("/accounts/login/")


def test_full_flow_gives_five_minute_token(ana, oauth_app):
    client = logged_in_client(ana)
    verifier, challenge = pkce_pair()
    response = authorize(client, challenge)
    assert response.status_code == 302
    query = parse_qs(urlparse(response["Location"]).query)
    token = exchange(client, query["code"][0], verifier)
    assert token.status_code == 200, token.content
    body = token.json()
    assert body["expires_in"] == 300
    assert body["access_token"] and body["refresh_token"]


def test_pkce_is_required(ana, oauth_app):
    response = authorize(logged_in_client(ana))  # no code_challenge
    assert "code=" not in response["Location"]


def test_wrong_verifier_is_rejected(ana, oauth_app):
    client = logged_in_client(ana)
    _, challenge = pkce_pair()
    code = parse_qs(urlparse(authorize(client, challenge)["Location"]).query)["code"][0]
    token = exchange(client, code, "wrong-verifier-" + "x" * 40)
    assert token.status_code == 400


def test_oidc_discovery_is_available():
    response = Client().get("/o/.well-known/openid-configuration")
    assert response.status_code == 200
    body = response.json()
    assert "authorization_endpoint" in body and "jwks_uri" in body
