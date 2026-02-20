import pytest
from app.services.auth import hash_password, verify_password, create_access_token, decode_access_token


# --- Unit tests for auth service ---


class TestPasswordHashing:
    def test_hash_password_returns_hash(self):
        hashed = hash_password("testpassword123")
        assert hashed != "testpassword123"
        assert hashed.startswith("$2")

    def test_verify_password_correct(self):
        hashed = hash_password("mypassword")
        assert verify_password("mypassword", hashed) is True

    def test_verify_password_incorrect(self):
        hashed = hash_password("mypassword")
        assert verify_password("wrongpassword", hashed) is False


class TestJWT:
    def test_create_and_decode_token(self):
        token = create_access_token("user-123")
        assert isinstance(token, str)
        user_id = decode_access_token(token)
        assert user_id == "user-123"

    def test_decode_invalid_token(self):
        result = decode_access_token("invalid.token.here")
        assert result is None

    def test_decode_empty_token(self):
        result = decode_access_token("")
        assert result is None


# --- Integration tests for auth routes ---


class TestRegisterPage:
    @pytest.mark.asyncio
    async def test_get_register_page(self, client):
        response = await client.get("/auth/register")
        assert response.status_code == 200
        assert "Create your account" in response.text
        assert "name" in response.text
        assert "email" in response.text
        assert "password" in response.text

    @pytest.mark.asyncio
    async def test_register_success(self, client):
        response = await client.post(
            "/auth/register",
            data={"name": "Test User", "email": "test@example.com", "password": "password123"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/dashboard"
        assert "access_token" in response.cookies

    @pytest.mark.asyncio
    async def test_register_short_password(self, client):
        response = await client.post(
            "/auth/register",
            data={"name": "Test User", "email": "test@example.com", "password": "short"},
        )
        assert response.status_code == 422
        assert "at least 8 characters" in response.text

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client):
        response = await client.post(
            "/auth/register",
            data={"name": "Test User", "email": "notanemail", "password": "password123"},
        )
        assert response.status_code == 422
        assert "valid email" in response.text

    @pytest.mark.asyncio
    async def test_register_missing_name(self, client):
        response = await client.post(
            "/auth/register",
            data={"name": "", "email": "test@example.com", "password": "password123"},
        )
        assert response.status_code == 422
        assert "Name is required" in response.text

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client):
        # Register first user
        await client.post(
            "/auth/register",
            data={"name": "First User", "email": "dupe@example.com", "password": "password123"},
            follow_redirects=False,
        )
        # Try to register second user with same email
        response = await client.post(
            "/auth/register",
            data={"name": "Second User", "email": "dupe@example.com", "password": "password456"},
        )
        assert response.status_code == 409
        assert "already exists" in response.text


class TestLoginPage:
    @pytest.mark.asyncio
    async def test_get_login_page(self, client):
        response = await client.get("/auth/login")
        assert response.status_code == 200
        assert "Welcome back" in response.text
        assert "email" in response.text
        assert "password" in response.text

    @pytest.mark.asyncio
    async def test_login_success(self, client):
        # Register first
        await client.post(
            "/auth/register",
            data={"name": "Login User", "email": "login@example.com", "password": "password123"},
            follow_redirects=False,
        )
        # Clear cookies
        client.cookies.clear()
        # Login
        response = await client.post(
            "/auth/login",
            data={"email": "login@example.com", "password": "password123"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/dashboard"
        assert "access_token" in response.cookies

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client):
        # Register first
        await client.post(
            "/auth/register",
            data={"name": "Wrong PW User", "email": "wrong@example.com", "password": "password123"},
            follow_redirects=False,
        )
        client.cookies.clear()
        # Login with wrong password
        response = await client.post(
            "/auth/login",
            data={"email": "wrong@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert "Invalid email or password" in response.text

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client):
        response = await client.post(
            "/auth/login",
            data={"email": "noone@example.com", "password": "password123"},
        )
        assert response.status_code == 401
        assert "Invalid email or password" in response.text

    @pytest.mark.asyncio
    async def test_login_empty_fields(self, client):
        response = await client.post(
            "/auth/login",
            data={"email": "", "password": ""},
        )
        assert response.status_code == 422
        assert "required" in response.text


class TestLogout:
    @pytest.mark.asyncio
    async def test_logout(self, client):
        # Register and get cookie
        await client.post(
            "/auth/register",
            data={"name": "Logout User", "email": "logout@example.com", "password": "password123"},
            follow_redirects=False,
        )
        # Logout
        response = await client.post("/auth/logout", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/"

    @pytest.mark.asyncio
    async def test_logout_get(self, client):
        response = await client.get("/auth/logout", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/"


class TestAuthProtection:
    @pytest.mark.asyncio
    async def test_dashboard_requires_auth(self, client):
        response = await client.get("/dashboard", follow_redirects=False)
        # Should redirect to login
        assert response.status_code == 302
        assert "/auth/login" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_dashboard_accessible_with_auth(self, client):
        # Register to get a cookie
        reg_response = await client.post(
            "/auth/register",
            data={"name": "Dashboard User", "email": "dash@example.com", "password": "password123"},
            follow_redirects=False,
        )
        # Use the cookie to access dashboard
        token = reg_response.cookies.get("access_token")
        client.cookies.set("access_token", token)
        response = await client.get("/dashboard")
        assert response.status_code == 200
        assert "Dashboard User" in response.text
        assert "Welcome back" in response.text

    @pytest.mark.asyncio
    async def test_register_redirects_when_logged_in(self, client):
        # Register to get a cookie
        reg_response = await client.post(
            "/auth/register",
            data={"name": "Redirect User", "email": "redirect@example.com", "password": "password123"},
            follow_redirects=False,
        )
        token = reg_response.cookies.get("access_token")
        client.cookies.set("access_token", token)
        # Visit register page while logged in
        response = await client.get("/auth/register", follow_redirects=False)
        assert response.status_code == 302
        assert "/dashboard" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_login_redirects_when_logged_in(self, client):
        # Register to get a cookie
        reg_response = await client.post(
            "/auth/register",
            data={"name": "Redirect User2", "email": "redirect2@example.com", "password": "password123"},
            follow_redirects=False,
        )
        token = reg_response.cookies.get("access_token")
        client.cookies.set("access_token", token)
        # Visit login page while logged in
        response = await client.get("/auth/login", follow_redirects=False)
        assert response.status_code == 302
        assert "/dashboard" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_invalid_token_rejected(self, client):
        client.cookies.set("access_token", "totally.invalid.token")
        response = await client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers["location"]
