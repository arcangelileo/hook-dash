"""QA session tests — covers error handling, edge cases, and new code paths."""
import pytest


async def register_and_login(client):
    """Helper: register a user and return with auth cookie set."""
    resp = await client.post(
        "/auth/register",
        data={"name": "QA User", "email": "qa@example.com", "password": "password123"},
        follow_redirects=False,
    )
    token = resp.cookies.get("access_token")
    client.cookies.set("access_token", token)
    return token


async def create_endpoint_get_id(client):
    """Register, login, create endpoint, return ID."""
    await register_and_login(client)
    resp = await client.post(
        "/endpoints/new",
        data={"name": "QA Endpoint"},
        follow_redirects=False,
    )
    return resp.headers["location"].split("/")[-1]


class TestErrorPage:
    @pytest.mark.asyncio
    async def test_404_renders_error_template(self, client):
        resp = await client.get("/nonexistent-page")
        assert resp.status_code == 404
        assert "Page not found" in resp.text or "404" in resp.text

    @pytest.mark.asyncio
    async def test_error_page_has_navigation_links(self, client):
        resp = await client.get("/nonexistent-page")
        assert resp.status_code == 404
        assert "Go Home" in resp.text


class TestIntConversionSafety:
    @pytest.mark.asyncio
    async def test_create_endpoint_non_numeric_response_code(self, client):
        await register_and_login(client)
        resp = await client.post(
            "/endpoints/new",
            data={
                "name": "Bad Code Test",
                "response_code": "abc",
                "response_body": "{}",
                "response_content_type": "application/json",
            },
            follow_redirects=False,
        )
        # Should default to 200 and succeed, not crash with 500
        assert resp.status_code == 302

    @pytest.mark.asyncio
    async def test_edit_endpoint_non_numeric_response_code(self, client):
        endpoint_id = await create_endpoint_get_id(client)
        resp = await client.post(
            f"/endpoints/{endpoint_id}/edit",
            data={
                "name": "QA Endpoint",
                "response_code": "not-a-number",
                "response_body": "{}",
                "response_content_type": "application/json",
                "is_active": "on",
            },
            follow_redirects=False,
        )
        # Should use the existing code and succeed
        assert resp.status_code == 302

    @pytest.mark.asyncio
    async def test_detail_page_invalid_page_param(self, client):
        endpoint_id = await create_endpoint_get_id(client)
        resp = await client.get(f"/endpoints/{endpoint_id}?page=abc")
        # Should default to page 1, not crash
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_detail_page_negative_page_param(self, client):
        endpoint_id = await create_endpoint_get_id(client)
        resp = await client.get(f"/endpoints/{endpoint_id}?page=-5")
        # Should clamp to page 1
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_forwarding_non_numeric_retries(self, client):
        endpoint_id = await create_endpoint_get_id(client)
        resp = await client.post(
            f"/endpoints/{endpoint_id}/forwarding",
            data={
                "target_url": "https://example.com/hook",
                "max_retries": "abc",
                "timeout_seconds": "xyz",
                "is_active": "on",
            },
            follow_redirects=False,
        )
        # Should default and succeed
        assert resp.status_code == 302


class TestContentLengthPrecheck:
    @pytest.mark.asyncio
    async def test_content_length_too_large_rejected_early(self, client):
        await register_and_login(client)
        resp = await client.post(
            "/endpoints/new",
            data={"name": "Size Check"},
            follow_redirects=False,
        )
        endpoint_id = resp.headers["location"].split("/")[-1]

        # Send with an oversized Content-Length header
        webhook_resp = await client.post(
            f"/hooks/{endpoint_id}",
            content=b"small body",
            headers={
                "content-type": "application/octet-stream",
                "content-length": "99999999",
            },
        )
        assert webhook_resp.status_code == 413


class TestLandingPageContent:
    @pytest.mark.asyncio
    async def test_landing_shows_coming_soon_for_team_features(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "coming soon" in resp.text.lower()

    @pytest.mark.asyncio
    async def test_landing_has_favicon(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "icon" in resp.text.lower()


class TestNavPlanBadge:
    @pytest.mark.asyncio
    async def test_dashboard_shows_plan_badge(self, client):
        await register_and_login(client)
        resp = await client.get("/dashboard")
        assert resp.status_code == 200
        # Nav should show plan badge
        assert "free" in resp.text.lower()


class TestEndpointEditConfirmation:
    @pytest.mark.asyncio
    async def test_edit_page_has_delete_confirmation(self, client):
        endpoint_id = await create_endpoint_get_id(client)
        resp = await client.get(f"/endpoints/{endpoint_id}/edit")
        assert resp.status_code == 200
        assert "confirm(" in resp.text
        assert "permanently" in resp.text.lower()
