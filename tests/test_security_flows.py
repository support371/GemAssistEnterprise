import app as app_module


def test_health_endpoint_exposes_only_liveness_metadata():
    client = app_module.app.test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "version": "2.1.0"}


def test_portal_routes_redirect_to_canonical_client_login():
    client = app_module.app.test_client()

    for path in ("/dashboard", "/client", "/client-portal"):
        response = client.get(path)
        assert response.status_code == 302
        assert response.headers["Location"] == app_module.CANONICAL_CLIENT_LOGIN_URL


def test_get_started_redirects_to_canonical_application():
    client = app_module.app.test_client()

    response = client.get("/get-started")

    assert response.status_code == 302
    assert response.headers["Location"] == app_module.CANONICAL_GET_STARTED_URL


def test_github_callback_does_not_store_provider_token(monkeypatch):
    monkeypatch.setattr(app_module, "GITHUB_AUTH_AVAILABLE", True)
    monkeypatch.setattr(app_module.github_auth, "is_configured", lambda: True)
    monkeypatch.setattr(
        app_module.github_auth,
        "exchange_code_for_token",
        lambda code: "provider-secret-token",
    )
    monkeypatch.setattr(
        app_module.github_auth,
        "get_user_info",
        lambda token: {"login": "enterprise-user", "name": "Enterprise User"},
    )
    client = app_module.app.test_client()

    with client.session_transaction() as session:
        session["github_oauth_state"] = "expected-state"

    response = client.get(
        "/auth/github/callback?code=valid-code&state=expected-state"
    )

    assert response.status_code == 302
    with client.session_transaction() as session:
        assert "github_token" not in session
        assert "github_oauth_state" not in session
        assert session["github_user"]["login"] == "enterprise-user"


def test_contact_api_fails_closed_when_delivery_cannot_be_confirmed(monkeypatch):
    def fail_delivery(_message):
        raise RuntimeError("mail unavailable")

    monkeypatch.setattr(app_module.mail, "send", fail_delivery)
    client = app_module.app.test_client()

    response = client.post(
        "/api/contact",
        json={
            "name": "Enterprise Buyer",
            "email": "buyer@example.org",
            "company": "Example Org",
            "message": "Please contact me about a security assessment.",
        },
    )

    assert response.status_code == 503
    assert response.get_json()["status"] == "error"


def test_security_headers_are_applied_to_html_routes():
    client = app_module.app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert "Content-Security-Policy" in response.headers
