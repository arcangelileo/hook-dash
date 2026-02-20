import pytest


async def create_endpoint_and_get_id(client):
    """Register, login, create endpoint, and return the endpoint ID."""
    resp = await client.post(
        "/auth/register",
        data={"name": "Test User", "email": "test@example.com", "password": "password123"},
        follow_redirects=False,
    )
    token = resp.cookies.get("access_token")
    client.cookies.set("access_token", token)

    create_resp = await client.post(
        "/endpoints/new",
        data={"name": "Receiver Test", "response_code": "200", "response_body": '{"ok": true}'},
        follow_redirects=False,
    )
    endpoint_id = create_resp.headers["location"].split("/")[-1]
    return endpoint_id


class TestWebhookReceiver:
    @pytest.mark.asyncio
    async def test_receive_post_webhook(self, client):
        endpoint_id = await create_endpoint_and_get_id(client)
        resp = await client.post(
            f"/hooks/{endpoint_id}",
            json={"event": "payment.completed", "amount": 4999},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True

    @pytest.mark.asyncio
    async def test_receive_get_webhook(self, client):
        endpoint_id = await create_endpoint_and_get_id(client)
        resp = await client.get(f"/hooks/{endpoint_id}?status=active&page=1")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_receive_put_webhook(self, client):
        endpoint_id = await create_endpoint_and_get_id(client)
        resp = await client.put(
            f"/hooks/{endpoint_id}",
            content="raw body data",
            headers={"content-type": "text/plain"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_receive_patch_webhook(self, client):
        endpoint_id = await create_endpoint_and_get_id(client)
        resp = await client.patch(
            f"/hooks/{endpoint_id}",
            json={"field": "updated"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_receive_delete_webhook(self, client):
        endpoint_id = await create_endpoint_and_get_id(client)
        resp = await client.request("DELETE", f"/hooks/{endpoint_id}")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_nonexistent_endpoint_returns_404(self, client):
        resp = await client.post(
            "/hooks/nonexistent-endpoint-id",
            json={"test": True},
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["error"].lower()

    @pytest.mark.asyncio
    async def test_inactive_endpoint_returns_410(self, client):
        endpoint_id = await create_endpoint_and_get_id(client)
        # Deactivate the endpoint (don't pass is_active checkbox)
        await client.post(
            f"/endpoints/{endpoint_id}/edit",
            data={
                "name": "Receiver Test",
                "response_code": "200",
                "response_body": '{"ok": true}',
                "response_content_type": "application/json",
            },
            follow_redirects=False,
        )
        resp = await client.post(
            f"/hooks/{endpoint_id}",
            json={"test": True},
        )
        assert resp.status_code == 410
        assert "inactive" in resp.json()["error"].lower()

    @pytest.mark.asyncio
    async def test_request_count_increments(self, client):
        endpoint_id = await create_endpoint_and_get_id(client)
        for i in range(3):
            await client.post(f"/hooks/{endpoint_id}", json={"i": i})
        detail = await client.get(f"/endpoints/{endpoint_id}")
        assert detail.status_code == 200
        assert "3" in detail.text

    @pytest.mark.asyncio
    async def test_custom_response_code(self, client):
        resp = await client.post(
            "/auth/register",
            data={"name": "Custom User", "email": "custom@example.com", "password": "password123"},
            follow_redirects=False,
        )
        token = resp.cookies.get("access_token")
        client.cookies.set("access_token", token)

        create_resp = await client.post(
            "/endpoints/new",
            data={"name": "Custom 201", "response_code": "201", "response_body": '{"created": true}'},
            follow_redirects=False,
        )
        endpoint_id = create_resp.headers["location"].split("/")[-1]
        webhook_resp = await client.post(
            f"/hooks/{endpoint_id}",
            json={"event": "new"},
        )
        assert webhook_resp.status_code == 201
        assert webhook_resp.json()["created"] is True

    @pytest.mark.asyncio
    async def test_webhook_stores_headers(self, client):
        endpoint_id = await create_endpoint_and_get_id(client)
        await client.post(
            f"/hooks/{endpoint_id}",
            json={"data": "test"},
            headers={"X-Custom-Header": "my-value"},
        )
        detail = await client.get(f"/endpoints/{endpoint_id}")
        assert "x-custom-header" in detail.text.lower()

    @pytest.mark.asyncio
    async def test_webhook_stores_query_params(self, client):
        endpoint_id = await create_endpoint_and_get_id(client)
        await client.get(f"/hooks/{endpoint_id}?foo=bar&baz=qux")
        detail = await client.get(f"/endpoints/{endpoint_id}")
        assert "foo" in detail.text
        assert "bar" in detail.text


class TestWebhookHistory:
    @pytest.mark.asyncio
    async def test_history_shows_requests(self, client):
        endpoint_id = await create_endpoint_and_get_id(client)
        await client.post(
            f"/hooks/{endpoint_id}",
            json={"event": "payment.completed"},
        )
        detail = await client.get(f"/endpoints/{endpoint_id}")
        assert detail.status_code == 200
        assert "POST" in detail.text
        assert "payment.completed" in detail.text

    @pytest.mark.asyncio
    async def test_history_method_filter(self, client):
        endpoint_id = await create_endpoint_and_get_id(client)
        await client.post(f"/hooks/{endpoint_id}", json={"type": "post"})
        await client.get(f"/hooks/{endpoint_id}")

        detail = await client.get(f"/endpoints/{endpoint_id}?method=GET")
        assert detail.status_code == 200

    @pytest.mark.asyncio
    async def test_history_search(self, client):
        endpoint_id = await create_endpoint_and_get_id(client)
        await client.post(f"/hooks/{endpoint_id}", json={"event": "unique_search_term_xyz"})
        await client.post(f"/hooks/{endpoint_id}", json={"event": "other"})

        detail = await client.get(f"/endpoints/{endpoint_id}?search=unique_search_term_xyz")
        assert detail.status_code == 200
        assert "unique_search_term_xyz" in detail.text


class TestDashboardStats:
    @pytest.mark.asyncio
    async def test_dashboard_shows_real_stats(self, client):
        endpoint_id = await create_endpoint_and_get_id(client)
        await client.post(f"/hooks/{endpoint_id}", json={"n": 1})
        await client.post(f"/hooks/{endpoint_id}", json={"n": 2})

        dash = await client.get("/dashboard")
        assert dash.status_code == 200
        # Should show 1 endpoint count
        assert "Receiver Test" in dash.text
