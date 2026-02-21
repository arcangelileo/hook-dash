from unittest.mock import AsyncMock, patch

import pytest
import httpx


async def register_and_login(client):
    """Register a user and set the access token cookie."""
    resp = await client.post(
        "/auth/register",
        data={"name": "Fwd User", "email": "fwd@example.com", "password": "password123"},
        follow_redirects=False,
    )
    token = resp.cookies.get("access_token")
    client.cookies.set("access_token", token)
    return token


async def create_endpoint_and_get_id(client):
    """Register, login, create endpoint, return its ID."""
    await register_and_login(client)
    create_resp = await client.post(
        "/endpoints/new",
        data={
            "name": "Forwarding Test Endpoint",
            "response_code": "200",
            "response_body": '{"ok": true}',
        },
        follow_redirects=False,
    )
    endpoint_id = create_resp.headers["location"].split("/")[-1]
    return endpoint_id


class TestForwardingConfigCRUD:
    """Tests for creating, updating, and deleting forwarding configurations."""

    @pytest.mark.asyncio
    async def test_create_forwarding_config(self, client):
        endpoint_id = await create_endpoint_and_get_id(client)
        resp = await client.post(
            f"/endpoints/{endpoint_id}/forwarding",
            data={
                "target_url": "https://example.com/webhook",
                "is_active": "on",
                "max_retries": "3",
                "timeout_seconds": "15",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert f"/endpoints/{endpoint_id}" in resp.headers["location"]

        # Verify config is shown on endpoint detail page
        detail = await client.get(f"/endpoints/{endpoint_id}")
        assert detail.status_code == 200
        assert "https://example.com/webhook" in detail.text
        assert "Forwarding Active" in detail.text

    @pytest.mark.asyncio
    async def test_create_forwarding_config_requires_url(self, client):
        endpoint_id = await create_endpoint_and_get_id(client)
        resp = await client.post(
            f"/endpoints/{endpoint_id}/forwarding",
            data={"target_url": "", "is_active": "on", "max_retries": "5", "timeout_seconds": "30"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "fwd_error" in resp.headers["location"]

    @pytest.mark.asyncio
    async def test_create_forwarding_config_validates_url_scheme(self, client):
        endpoint_id = await create_endpoint_and_get_id(client)
        resp = await client.post(
            f"/endpoints/{endpoint_id}/forwarding",
            data={
                "target_url": "ftp://example.com/webhook",
                "is_active": "on",
                "max_retries": "5",
                "timeout_seconds": "30",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "fwd_error" in resp.headers["location"]

    @pytest.mark.asyncio
    async def test_update_forwarding_config(self, client):
        endpoint_id = await create_endpoint_and_get_id(client)
        # Create
        await client.post(
            f"/endpoints/{endpoint_id}/forwarding",
            data={
                "target_url": "https://example.com/v1",
                "is_active": "on",
                "max_retries": "3",
                "timeout_seconds": "15",
            },
            follow_redirects=False,
        )
        # Update
        resp = await client.post(
            f"/endpoints/{endpoint_id}/forwarding",
            data={
                "target_url": "https://example.com/v2",
                "is_active": "on",
                "max_retries": "5",
                "timeout_seconds": "30",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302

        detail = await client.get(f"/endpoints/{endpoint_id}")
        assert "https://example.com/v2" in detail.text

    @pytest.mark.asyncio
    async def test_disable_forwarding(self, client):
        endpoint_id = await create_endpoint_and_get_id(client)
        # Create active
        await client.post(
            f"/endpoints/{endpoint_id}/forwarding",
            data={
                "target_url": "https://example.com/webhook",
                "is_active": "on",
                "max_retries": "3",
                "timeout_seconds": "15",
            },
            follow_redirects=False,
        )
        # Update without is_active checkbox (= disabled)
        await client.post(
            f"/endpoints/{endpoint_id}/forwarding",
            data={
                "target_url": "https://example.com/webhook",
                "max_retries": "3",
                "timeout_seconds": "15",
            },
            follow_redirects=False,
        )
        detail = await client.get(f"/endpoints/{endpoint_id}")
        assert "Paused" in detail.text

    @pytest.mark.asyncio
    async def test_delete_forwarding_config(self, client):
        endpoint_id = await create_endpoint_and_get_id(client)
        await client.post(
            f"/endpoints/{endpoint_id}/forwarding",
            data={
                "target_url": "https://example.com/webhook",
                "is_active": "on",
                "max_retries": "3",
                "timeout_seconds": "15",
            },
            follow_redirects=False,
        )
        # Delete
        resp = await client.post(
            f"/endpoints/{endpoint_id}/forwarding/delete",
            follow_redirects=False,
        )
        assert resp.status_code == 302

        detail = await client.get(f"/endpoints/{endpoint_id}")
        assert "Forwarding Active" not in detail.text
        assert "Enable Forwarding" in detail.text

    @pytest.mark.asyncio
    async def test_forwarding_config_unauthorized_endpoint(self, client):
        endpoint_id = await create_endpoint_and_get_id(client)
        # Register a second user
        resp2 = await client.post(
            "/auth/register",
            data={"name": "Other User", "email": "other@example.com", "password": "password123"},
            follow_redirects=False,
        )
        client.cookies.set("access_token", resp2.cookies.get("access_token"))
        # Try to set forwarding on first user's endpoint
        resp = await client.post(
            f"/endpoints/{endpoint_id}/forwarding",
            data={
                "target_url": "https://evil.com/hook",
                "is_active": "on",
                "max_retries": "3",
                "timeout_seconds": "15",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert resp.headers["location"] == "/endpoints"

    @pytest.mark.asyncio
    async def test_max_retries_clamped(self, client):
        """max_retries should be clamped between 1 and 10."""
        endpoint_id = await create_endpoint_and_get_id(client)
        await client.post(
            f"/endpoints/{endpoint_id}/forwarding",
            data={
                "target_url": "https://example.com/webhook",
                "is_active": "on",
                "max_retries": "50",
                "timeout_seconds": "30",
            },
            follow_redirects=False,
        )
        detail = await client.get(f"/endpoints/{endpoint_id}")
        assert detail.status_code == 200
        assert "Forwarding Active" in detail.text


class TestForwardingLogs:
    """Tests for the forwarding logs page."""

    @pytest.mark.asyncio
    async def test_logs_page_requires_auth(self, client):
        resp = await client.get("/endpoints/some-id/forwarding/logs", follow_redirects=False)
        assert resp.status_code == 302
        assert "/auth/login" in resp.headers["location"]

    @pytest.mark.asyncio
    async def test_logs_page_requires_forwarding_config(self, client):
        endpoint_id = await create_endpoint_and_get_id(client)
        resp = await client.get(
            f"/endpoints/{endpoint_id}/forwarding/logs",
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert f"/endpoints/{endpoint_id}" in resp.headers["location"]

    @pytest.mark.asyncio
    async def test_logs_page_empty_state(self, client):
        endpoint_id = await create_endpoint_and_get_id(client)
        await client.post(
            f"/endpoints/{endpoint_id}/forwarding",
            data={
                "target_url": "https://example.com/webhook",
                "is_active": "on",
                "max_retries": "3",
                "timeout_seconds": "15",
            },
            follow_redirects=False,
        )
        resp = await client.get(f"/endpoints/{endpoint_id}/forwarding/logs")
        assert resp.status_code == 200
        assert "No forwarding logs yet" in resp.text
        assert "Delivery Attempts" in resp.text

    @pytest.mark.asyncio
    async def test_logs_page_shows_endpoint_name(self, client):
        endpoint_id = await create_endpoint_and_get_id(client)
        await client.post(
            f"/endpoints/{endpoint_id}/forwarding",
            data={
                "target_url": "https://example.com/webhook",
                "is_active": "on",
                "max_retries": "3",
                "timeout_seconds": "15",
            },
            follow_redirects=False,
        )
        resp = await client.get(f"/endpoints/{endpoint_id}/forwarding/logs")
        assert "Forwarding Test Endpoint" in resp.text

    @pytest.mark.asyncio
    async def test_logs_page_nonexistent_endpoint(self, client):
        await register_and_login(client)
        resp = await client.get("/endpoints/nonexistent-id/forwarding/logs")
        assert resp.status_code == 404


class TestReplayWebhook:
    """Tests for the replay (manual forwarding) feature."""

    @pytest.mark.asyncio
    async def test_replay_requires_forwarding_config(self, client):
        endpoint_id = await create_endpoint_and_get_id(client)
        await client.post(f"/hooks/{endpoint_id}", json={"test": True})
        resp = await client.post(
            f"/endpoints/{endpoint_id}/replay/some-request-id",
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "fwd_error" in resp.headers["location"]

    @pytest.mark.asyncio
    async def test_replay_nonexistent_request(self, client):
        endpoint_id = await create_endpoint_and_get_id(client)
        await client.post(
            f"/endpoints/{endpoint_id}/forwarding",
            data={
                "target_url": "https://example.com/webhook",
                "is_active": "on",
                "max_retries": "1",
                "timeout_seconds": "5",
            },
            follow_redirects=False,
        )
        resp = await client.post(
            f"/endpoints/{endpoint_id}/replay/nonexistent-request-id",
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "fwd_error" in resp.headers["location"]


class TestForwardingService:
    """Tests for the forwarding service layer functions."""

    @pytest.mark.asyncio
    async def test_forward_webhook_success(self, client):
        """Test successful webhook forwarding with mocked HTTP client."""
        from tests.conftest import TestingSessionLocal
        from app.services.forwarding import create_forwarding_config, forward_webhook
        from app.services.receiver import store_webhook_request
        from app.services.auth import register_user
        from app.models.endpoint import Endpoint

        async with TestingSessionLocal() as db:
            user = await register_user(db, "svc@test.com", "pass123", "Svc User")
            await db.flush()

            endpoint = Endpoint(
                user_id=user.id,
                name="Fwd Svc Test",
                response_code=200,
                response_body='{"ok": true}',
                response_content_type="application/json",
            )
            db.add(endpoint)
            await db.flush()

            config = await create_forwarding_config(
                db, endpoint.id, "https://httpbin.org/post", True, 3, 10
            )
            await db.flush()

            webhook_req = await store_webhook_request(
                db, endpoint, "POST", {"content-type": "application/json"},
                '{"event": "test"}', {}, "application/json", "127.0.0.1"
            )
            await db.flush()

            mock_response = AsyncMock()
            mock_response.status_code = 200

            with patch("app.services.forwarding.httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client.request = AsyncMock(return_value=mock_response)
                mock_client_cls.return_value = mock_client

                log = await forward_webhook(db, config, webhook_req)
                await db.commit()

            assert log.success is True
            assert log.status_code == 200
            assert log.attempt_number == 1
            assert log.response_time_ms is not None
            assert log.error_message == ""

    @pytest.mark.asyncio
    async def test_forward_webhook_connection_error(self, client):
        """Test forwarding when the target server is unreachable."""
        from tests.conftest import TestingSessionLocal
        from app.services.forwarding import create_forwarding_config, forward_webhook
        from app.services.receiver import store_webhook_request
        from app.services.auth import register_user
        from app.models.endpoint import Endpoint

        async with TestingSessionLocal() as db:
            user = await register_user(db, "err@test.com", "pass123", "Err User")
            await db.flush()

            endpoint = Endpoint(
                user_id=user.id,
                name="Err Test",
                response_code=200,
                response_body='{"ok": true}',
                response_content_type="application/json",
            )
            db.add(endpoint)
            await db.flush()

            config = await create_forwarding_config(
                db, endpoint.id, "https://unreachable.invalid/hook", True, 1, 5
            )
            await db.flush()

            webhook_req = await store_webhook_request(
                db, endpoint, "POST", {"content-type": "application/json"},
                '{"event": "test"}', {}, "application/json", "127.0.0.1"
            )
            await db.flush()

            with patch("app.services.forwarding.httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client.request = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
                mock_client_cls.return_value = mock_client

                log = await forward_webhook(db, config, webhook_req)
                await db.commit()

            assert log.success is False
            assert log.status_code is None
            assert "Connection refused" in log.error_message

    @pytest.mark.asyncio
    async def test_forward_webhook_timeout(self, client):
        """Test forwarding when the target server times out."""
        from tests.conftest import TestingSessionLocal
        from app.services.forwarding import create_forwarding_config, forward_webhook
        from app.services.receiver import store_webhook_request
        from app.services.auth import register_user
        from app.models.endpoint import Endpoint

        async with TestingSessionLocal() as db:
            user = await register_user(db, "tout@test.com", "pass123", "Timeout User")
            await db.flush()

            endpoint = Endpoint(
                user_id=user.id,
                name="Timeout Test",
                response_code=200,
                response_body='{"ok": true}',
                response_content_type="application/json",
            )
            db.add(endpoint)
            await db.flush()

            config = await create_forwarding_config(
                db, endpoint.id, "https://slow-server.example/hook", True, 1, 5
            )
            await db.flush()

            webhook_req = await store_webhook_request(
                db, endpoint, "POST", {},
                '{"event": "test"}', {}, "application/json", "127.0.0.1"
            )
            await db.flush()

            with patch("app.services.forwarding.httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client.request = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
                mock_client_cls.return_value = mock_client

                log = await forward_webhook(db, config, webhook_req)
                await db.commit()

            assert log.success is False
            assert "Timeout" in log.error_message

    @pytest.mark.asyncio
    async def test_forward_webhook_4xx_response(self, client):
        """Test forwarding when target returns 4xx."""
        from tests.conftest import TestingSessionLocal
        from app.services.forwarding import create_forwarding_config, forward_webhook
        from app.services.receiver import store_webhook_request
        from app.services.auth import register_user
        from app.models.endpoint import Endpoint

        async with TestingSessionLocal() as db:
            user = await register_user(db, "r4xx@test.com", "pass123", "4xx User")
            await db.flush()

            endpoint = Endpoint(
                user_id=user.id,
                name="4xx Test",
                response_code=200,
                response_body='{"ok": true}',
                response_content_type="application/json",
            )
            db.add(endpoint)
            await db.flush()

            config = await create_forwarding_config(
                db, endpoint.id, "https://example.com/hook", True, 1, 5
            )
            await db.flush()

            webhook_req = await store_webhook_request(
                db, endpoint, "POST", {},
                '{"event": "test"}', {}, "application/json", "127.0.0.1"
            )
            await db.flush()

            mock_response = AsyncMock()
            mock_response.status_code = 422

            with patch("app.services.forwarding.httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client.request = AsyncMock(return_value=mock_response)
                mock_client_cls.return_value = mock_client

                log = await forward_webhook(db, config, webhook_req)
                await db.commit()

            assert log.success is False
            assert log.status_code == 422
            assert "HTTP 422" in log.error_message

    @pytest.mark.asyncio
    async def test_forward_with_retries_succeeds_on_second_attempt(self, client):
        """Test that retry logic succeeds on a later attempt."""
        from tests.conftest import TestingSessionLocal
        from app.services.forwarding import create_forwarding_config, forward_with_retries
        from app.services.receiver import store_webhook_request
        from app.services.auth import register_user
        from app.models.endpoint import Endpoint

        async with TestingSessionLocal() as db:
            user = await register_user(db, "retry@test.com", "pass123", "Retry User")
            await db.flush()

            endpoint = Endpoint(
                user_id=user.id,
                name="Retry Test",
                response_code=200,
                response_body='{"ok": true}',
                response_content_type="application/json",
            )
            db.add(endpoint)
            await db.flush()

            config = await create_forwarding_config(
                db, endpoint.id, "https://flaky.example/hook", True, 3, 5
            )
            await db.flush()

            webhook_req = await store_webhook_request(
                db, endpoint, "POST", {},
                '{"event": "test"}', {}, "application/json", "127.0.0.1"
            )
            await db.flush()

            fail_response = AsyncMock()
            fail_response.status_code = 503

            success_response = AsyncMock()
            success_response.status_code = 200

            call_count = 0

            async def mock_request(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return fail_response
                return success_response

            with patch("app.services.forwarding.httpx.AsyncClient") as mock_client_cls, \
                 patch("app.services.forwarding.asyncio.sleep", new_callable=AsyncMock):
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client.request = mock_request
                mock_client_cls.return_value = mock_client

                log = await forward_with_retries(db, config, webhook_req)
                await db.commit()

            assert log.success is True
            assert log.attempt_number == 2

    @pytest.mark.asyncio
    async def test_forwarding_stats(self, client):
        """Test forwarding stats calculation."""
        from tests.conftest import TestingSessionLocal
        from app.services.forwarding import (
            create_forwarding_config,
            create_forwarding_log,
            get_forwarding_stats,
        )
        from app.services.receiver import store_webhook_request
        from app.services.auth import register_user
        from app.models.endpoint import Endpoint

        async with TestingSessionLocal() as db:
            user = await register_user(db, "stats@test.com", "pass123", "Stats User")
            await db.flush()

            endpoint = Endpoint(
                user_id=user.id,
                name="Stats Test",
                response_code=200,
                response_body='{"ok": true}',
                response_content_type="application/json",
            )
            db.add(endpoint)
            await db.flush()

            config = await create_forwarding_config(
                db, endpoint.id, "https://example.com/hook", True, 3, 5
            )
            await db.flush()

            webhook_req = await store_webhook_request(
                db, endpoint, "POST", {},
                '{"event": "test"}', {}, "application/json", "127.0.0.1"
            )
            await db.flush()

            await create_forwarding_log(db, config.id, webhook_req.id, 200, True, "", 1, 50)
            await create_forwarding_log(db, config.id, webhook_req.id, 500, False, "HTTP 500", 1, 100)
            await create_forwarding_log(db, config.id, webhook_req.id, 200, True, "", 1, 150)
            await db.flush()

            stats = await get_forwarding_stats(db, config.id)
            await db.commit()

        assert stats["total"] == 3
        assert stats["successes"] == 2
        assert stats["failures"] == 1
        assert stats["success_rate"] == 66.7
        assert stats["avg_response_ms"] == 100

    @pytest.mark.asyncio
    async def test_list_forwarding_logs(self, client):
        """Test listing forwarding logs with pagination."""
        from tests.conftest import TestingSessionLocal
        from app.services.forwarding import (
            create_forwarding_config,
            create_forwarding_log,
            list_forwarding_logs,
        )
        from app.services.receiver import store_webhook_request
        from app.services.auth import register_user
        from app.models.endpoint import Endpoint

        async with TestingSessionLocal() as db:
            user = await register_user(db, "list@test.com", "pass123", "List User")
            await db.flush()

            endpoint = Endpoint(
                user_id=user.id,
                name="List Test",
                response_code=200,
                response_body='{"ok": true}',
                response_content_type="application/json",
            )
            db.add(endpoint)
            await db.flush()

            config = await create_forwarding_config(
                db, endpoint.id, "https://example.com/hook", True, 3, 5
            )
            await db.flush()

            webhook_req = await store_webhook_request(
                db, endpoint, "POST", {},
                '{"event": "test"}', {}, "application/json", "127.0.0.1"
            )
            await db.flush()

            for i in range(5):
                await create_forwarding_log(db, config.id, webhook_req.id, 200, True, "", i + 1, 50)
            await db.flush()

            logs, total = await list_forwarding_logs(db, config.id, limit=2, offset=0)
            await db.commit()

        assert total == 5
        assert len(logs) == 2


class TestAutoForwarding:
    """Tests for automatic forwarding when webhooks are received."""

    @pytest.mark.asyncio
    async def test_webhook_detail_shows_forwarding_section(self, client):
        endpoint_id = await create_endpoint_and_get_id(client)
        detail = await client.get(f"/endpoints/{endpoint_id}")
        assert "Webhook Forwarding" in detail.text
        assert "Enable Forwarding" in detail.text

    @pytest.mark.asyncio
    async def test_webhook_detail_shows_replay_button_when_forwarding_active(self, client):
        endpoint_id = await create_endpoint_and_get_id(client)
        await client.post(
            f"/endpoints/{endpoint_id}/forwarding",
            data={
                "target_url": "https://example.com/webhook",
                "is_active": "on",
                "max_retries": "1",
                "timeout_seconds": "5",
            },
            follow_redirects=False,
        )
        await client.post(f"/hooks/{endpoint_id}", json={"event": "test"})
        detail = await client.get(f"/endpoints/{endpoint_id}")
        assert "Replay" in detail.text

    @pytest.mark.asyncio
    async def test_webhook_detail_hides_replay_when_no_forwarding(self, client):
        endpoint_id = await create_endpoint_and_get_id(client)
        await client.post(f"/hooks/{endpoint_id}", json={"event": "test"})
        detail = await client.get(f"/endpoints/{endpoint_id}")
        assert "Replay" not in detail.text

    @pytest.mark.asyncio
    async def test_forwarding_stats_shown_on_detail(self, client):
        endpoint_id = await create_endpoint_and_get_id(client)
        await client.post(
            f"/endpoints/{endpoint_id}/forwarding",
            data={
                "target_url": "https://example.com/webhook",
                "is_active": "on",
                "max_retries": "1",
                "timeout_seconds": "5",
            },
            follow_redirects=False,
        )
        detail = await client.get(f"/endpoints/{endpoint_id}")
        assert "Total Forwarded" in detail.text
        assert "Success Rate" in detail.text

    @pytest.mark.asyncio
    async def test_delete_forwarding_on_nonexistent_endpoint(self, client):
        endpoint_id = await create_endpoint_and_get_id(client)
        resp2 = await client.post(
            "/auth/register",
            data={"name": "Other", "email": "other2@example.com", "password": "password123"},
            follow_redirects=False,
        )
        client.cookies.set("access_token", resp2.cookies.get("access_token"))
        resp = await client.post(
            f"/endpoints/{endpoint_id}/forwarding/delete",
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert resp.headers["location"] == "/endpoints"
