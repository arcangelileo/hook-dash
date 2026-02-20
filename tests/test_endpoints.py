import pytest


async def register_and_login(client):
    """Helper: register a user and return with auth cookie set."""
    resp = await client.post(
        "/auth/register",
        data={"name": "Test User", "email": "test@example.com", "password": "password123"},
        follow_redirects=False,
    )
    token = resp.cookies.get("access_token")
    client.cookies.set("access_token", token)
    return token


class TestEndpointList:
    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client):
        resp = await client.get("/endpoints", follow_redirects=False)
        assert resp.status_code == 302
        assert "/auth/login" in resp.headers["location"]

    @pytest.mark.asyncio
    async def test_list_empty(self, client):
        await register_and_login(client)
        resp = await client.get("/endpoints")
        assert resp.status_code == 200
        assert "No endpoints yet" in resp.text

    @pytest.mark.asyncio
    async def test_list_shows_endpoints(self, client):
        await register_and_login(client)
        await client.post(
            "/endpoints/new",
            data={"name": "My Webhook", "description": "Test endpoint"},
            follow_redirects=False,
        )
        resp = await client.get("/endpoints")
        assert resp.status_code == 200
        assert "My Webhook" in resp.text


class TestEndpointCreate:
    @pytest.mark.asyncio
    async def test_create_page_loads(self, client):
        await register_and_login(client)
        resp = await client.get("/endpoints/new")
        assert resp.status_code == 200
        assert "Create a new endpoint" in resp.text

    @pytest.mark.asyncio
    async def test_create_success(self, client):
        await register_and_login(client)
        resp = await client.post(
            "/endpoints/new",
            data={"name": "Stripe Webhooks", "description": "Payment events"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "/endpoints/" in resp.headers["location"]

    @pytest.mark.asyncio
    async def test_create_missing_name(self, client):
        await register_and_login(client)
        resp = await client.post(
            "/endpoints/new",
            data={"name": "", "description": "No name"},
        )
        assert resp.status_code == 422
        assert "required" in resp.text.lower()

    @pytest.mark.asyncio
    async def test_create_custom_response(self, client):
        await register_and_login(client)
        resp = await client.post(
            "/endpoints/new",
            data={
                "name": "Custom Response",
                "response_code": "201",
                "response_body": '{"status": "created"}',
                "response_content_type": "application/json",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302

    @pytest.mark.asyncio
    async def test_create_invalid_response_code(self, client):
        await register_and_login(client)
        resp = await client.post(
            "/endpoints/new",
            data={"name": "Bad Code", "response_code": "999"},
        )
        assert resp.status_code == 422
        assert "between 100 and 599" in resp.text

    @pytest.mark.asyncio
    async def test_create_at_plan_limit(self, client):
        await register_and_login(client)
        # Free plan = 2 endpoints
        await client.post(
            "/endpoints/new",
            data={"name": "Endpoint 1"},
            follow_redirects=False,
        )
        await client.post(
            "/endpoints/new",
            data={"name": "Endpoint 2"},
            follow_redirects=False,
        )
        # Third should fail
        resp = await client.post(
            "/endpoints/new",
            data={"name": "Endpoint 3"},
        )
        assert resp.status_code == 403
        assert "limit" in resp.text.lower()


class TestEndpointDetail:
    @pytest.mark.asyncio
    async def test_detail_shows_endpoint(self, client):
        await register_and_login(client)
        create_resp = await client.post(
            "/endpoints/new",
            data={"name": "Detail Test"},
            follow_redirects=False,
        )
        endpoint_url = create_resp.headers["location"]
        resp = await client.get(endpoint_url)
        assert resp.status_code == 200
        assert "Detail Test" in resp.text
        assert "hooks/" in resp.text

    @pytest.mark.asyncio
    async def test_detail_not_found(self, client):
        await register_and_login(client)
        resp = await client.get("/endpoints/nonexistent-id")
        assert resp.status_code == 404
        assert "not found" in resp.text.lower()

    @pytest.mark.asyncio
    async def test_detail_shows_empty_history(self, client):
        await register_and_login(client)
        create_resp = await client.post(
            "/endpoints/new",
            data={"name": "Empty History"},
            follow_redirects=False,
        )
        resp = await client.get(create_resp.headers["location"])
        assert "No requests yet" in resp.text


class TestEndpointEdit:
    @pytest.mark.asyncio
    async def test_edit_page_loads(self, client):
        await register_and_login(client)
        create_resp = await client.post(
            "/endpoints/new",
            data={"name": "Edit Me"},
            follow_redirects=False,
        )
        endpoint_id = create_resp.headers["location"].split("/")[-1]
        resp = await client.get(f"/endpoints/{endpoint_id}/edit")
        assert resp.status_code == 200
        assert "Edit Me" in resp.text

    @pytest.mark.asyncio
    async def test_edit_success(self, client):
        await register_and_login(client)
        create_resp = await client.post(
            "/endpoints/new",
            data={"name": "Before Edit"},
            follow_redirects=False,
        )
        endpoint_id = create_resp.headers["location"].split("/")[-1]
        resp = await client.post(
            f"/endpoints/{endpoint_id}/edit",
            data={
                "name": "After Edit",
                "description": "Updated",
                "is_active": "on",
                "response_code": "200",
                "response_body": '{"ok": true}',
                "response_content_type": "application/json",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302
        detail = await client.get(f"/endpoints/{endpoint_id}")
        assert "After Edit" in detail.text

    @pytest.mark.asyncio
    async def test_edit_empty_name_rejected(self, client):
        await register_and_login(client)
        create_resp = await client.post(
            "/endpoints/new",
            data={"name": "No Empty"},
            follow_redirects=False,
        )
        endpoint_id = create_resp.headers["location"].split("/")[-1]
        resp = await client.post(
            f"/endpoints/{endpoint_id}/edit",
            data={
                "name": "",
                "response_code": "200",
                "response_body": "{}",
                "response_content_type": "application/json",
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_edit_not_found(self, client):
        await register_and_login(client)
        resp = await client.get("/endpoints/fake-id/edit")
        assert resp.status_code == 404


class TestEndpointDelete:
    @pytest.mark.asyncio
    async def test_delete_success(self, client):
        await register_and_login(client)
        create_resp = await client.post(
            "/endpoints/new",
            data={"name": "Delete Me"},
            follow_redirects=False,
        )
        endpoint_id = create_resp.headers["location"].split("/")[-1]
        resp = await client.post(
            f"/endpoints/{endpoint_id}/delete",
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert resp.headers["location"] == "/endpoints"
        detail = await client.get(f"/endpoints/{endpoint_id}")
        assert detail.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client):
        await register_and_login(client)
        resp = await client.post(
            "/endpoints/fake-id/delete",
            follow_redirects=False,
        )
        assert resp.status_code == 404


class TestEndpointIsolation:
    @pytest.mark.asyncio
    async def test_cannot_see_other_users_endpoints(self, client):
        # Register user 1
        resp1 = await client.post(
            "/auth/register",
            data={"name": "User One", "email": "user1@example.com", "password": "password123"},
            follow_redirects=False,
        )
        token1 = resp1.cookies.get("access_token")
        client.cookies.set("access_token", token1)

        create_resp = await client.post(
            "/endpoints/new",
            data={"name": "User1 Endpoint"},
            follow_redirects=False,
        )
        endpoint_id = create_resp.headers["location"].split("/")[-1]

        # Register user 2
        client.cookies.clear()
        resp2 = await client.post(
            "/auth/register",
            data={"name": "User Two", "email": "user2@example.com", "password": "password123"},
            follow_redirects=False,
        )
        token2 = resp2.cookies.get("access_token")
        client.cookies.set("access_token", token2)

        detail = await client.get(f"/endpoints/{endpoint_id}")
        assert detail.status_code == 404
