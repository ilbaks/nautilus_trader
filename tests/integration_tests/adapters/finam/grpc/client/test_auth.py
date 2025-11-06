# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2015-2025 Nautech Systems Pty Ltd. All rights reserved.
#  https://nautechsystems.io
#
#  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
#  You may not use this file except in compliance with the License.
#  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# -------------------------------------------------------------------------------------------------

"""
Unit tests for Finam gRPC authentication manager.

Tests the FinamAuthManager class that handles JWT token lifecycle.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch, MagicMock

from nautilus_trader.adapters.finam.grpc.client.auth import FinamAuthManager


# Helper to create mock auth response
def _create_mock_auth_response(token: str = "mock-jwt-token"):
    """Create mock AuthResponse."""
    response = Mock()
    response.token = token
    return response


class TestFinamAuthManagerInit:
    """Test FinamAuthManager initialization."""

    def test_init_creates_manager(self):
        """Test initialization creates manager with correct state."""
        # Arrange
        mock_channel = Mock()

        # Act
        auth_manager = FinamAuthManager(
            channel=mock_channel,
            client_id="test-client",
            access_token="test-token",
        )

        # Assert
        assert auth_manager._client_id == "test-client"
        assert auth_manager._access_token == "test-token"
        assert auth_manager._jwt_token is None
        assert auth_manager._jwt_expires_at is None
        assert auth_manager._auto_refresh_task is None


class TestFinamAuthManagerGetJwtToken:
    """Test JWT token retrieval."""

    @pytest.mark.asyncio
    async def test_get_jwt_token_fetches_new_token(self):
        """Test getting JWT token when no token exists."""
        # Arrange
        mock_channel = Mock()
        mock_stub = AsyncMock()
        mock_response = _create_mock_auth_response("new-jwt-token")
        mock_stub.Auth.return_value = mock_response

        with patch("nautilus_trader.adapters.finam.grpc.client.auth.auth_service_pb2_grpc.AuthServiceStub", return_value=mock_stub):
            auth_manager = FinamAuthManager(
                channel=mock_channel,
                client_id="test-client",
                access_token="test-access-token",
            )

            # Act
            token = await auth_manager.get_jwt_token()

            # Assert
            assert token == "new-jwt-token"
            assert auth_manager._jwt_token == "new-jwt-token"
            assert auth_manager._jwt_expires_at is not None
            mock_stub.Auth.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_jwt_token_returns_cached_token(self):
        """Test that valid cached token is returned without refresh."""
        # Arrange
        mock_channel = Mock()
        mock_stub = AsyncMock()
        mock_response = _create_mock_auth_response("cached-token")
        mock_stub.Auth.return_value = mock_response

        with patch("nautilus_trader.adapters.finam.grpc.client.auth.auth_service_pb2_grpc.AuthServiceStub", return_value=mock_stub):
            auth_manager = FinamAuthManager(
                channel=mock_channel,
                client_id="test-client",
                access_token="test-token",
            )

            # Get token first time (fetch)
            await auth_manager.get_jwt_token()
            assert mock_stub.Auth.call_count == 1

            # Act - Get token second time (should use cache)
            token = await auth_manager.get_jwt_token()

            # Assert
            assert token == "cached-token"
            # Should not fetch again (still 1 call)
            assert mock_stub.Auth.call_count == 1

    @pytest.mark.asyncio
    async def test_get_jwt_token_refreshes_expired_token(self):
        """Test that expired token is refreshed."""
        # Arrange
        mock_channel = Mock()
        mock_stub = AsyncMock()
        mock_stub.Auth.side_effect = [
            _create_mock_auth_response("first-token"),
            _create_mock_auth_response("second-token"),
        ]

        with patch("nautilus_trader.adapters.finam.grpc.client.auth.auth_service_pb2_grpc.AuthServiceStub", return_value=mock_stub):
            auth_manager = FinamAuthManager(
                channel=mock_channel,
                client_id="test-client",
                access_token="test-token",
            )

            # Get first token
            token1 = await auth_manager.get_jwt_token()
            assert token1 == "first-token"

            # Manually expire the token (set expiry in the past)
            auth_manager._jwt_expires_at = datetime.utcnow() - timedelta(minutes=1)

            # Act - Get token again (should refresh)
            token2 = await auth_manager.get_jwt_token()

            # Assert
            assert token2 == "second-token"
            assert mock_stub.Auth.call_count == 2

    @pytest.mark.asyncio
    async def test_get_jwt_token_refreshes_near_expiry(self):
        """Test that token close to expiry is refreshed proactively."""
        # Arrange
        mock_channel = Mock()
        mock_stub = AsyncMock()
        mock_stub.Auth.side_effect = [
            _create_mock_auth_response("first-token"),
            _create_mock_auth_response("refreshed-token"),
        ]

        with patch("nautilus_trader.adapters.finam.grpc.client.auth.auth_service_pb2_grpc.AuthServiceStub", return_value=mock_stub):
            auth_manager = FinamAuthManager(
                channel=mock_channel,
                client_id="test-client",
                access_token="test-token",
            )

            # Get first token
            await auth_manager.get_jwt_token()

            # Set expiry to 4 minutes from now (< 5 min buffer)
            auth_manager._jwt_expires_at = datetime.utcnow() + timedelta(minutes=4)

            # Act - Get token again (should refresh due to proximity to expiry)
            token = await auth_manager.get_jwt_token()

            # Assert
            assert token == "refreshed-token"
            assert mock_stub.Auth.call_count == 2


class TestFinamAuthManagerRefreshJwtToken:
    """Test JWT token refresh."""

    @pytest.mark.asyncio
    async def test_refresh_jwt_token_calls_auth_service(self):
        """Test that refresh calls AuthService correctly."""
        # Arrange
        mock_channel = Mock()
        mock_stub = AsyncMock()
        mock_response = _create_mock_auth_response("refreshed-jwt-token")
        mock_stub.Auth.return_value = mock_response

        with patch("nautilus_trader.adapters.finam.grpc.client.auth.auth_service_pb2_grpc.AuthServiceStub", return_value=mock_stub):
            with patch("nautilus_trader.adapters.finam.grpc.client.auth.auth_service_pb2.AuthRequest") as mock_request:
                auth_manager = FinamAuthManager(
                    channel=mock_channel,
                    client_id="test-client",
                    access_token="secret-access-token",
                )

                # Act
                token = await auth_manager._refresh_jwt_token()

                # Assert
                assert token == "refreshed-jwt-token"
                mock_request.assert_called_once_with(secret="secret-access-token")
                mock_stub.Auth.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_jwt_token_thread_safe(self):
        """Test that concurrent refresh requests don't duplicate calls."""
        # Arrange
        mock_channel = Mock()
        mock_stub = AsyncMock()

        # Simulate slow auth response
        async def slow_auth(*args, **kwargs):
            await asyncio.sleep(0.1)
            return _create_mock_auth_response("thread-safe-token")

        mock_stub.Auth.side_effect = slow_auth

        with patch("nautilus_trader.adapters.finam.grpc.client.auth.auth_service_pb2_grpc.AuthServiceStub", return_value=mock_stub):
            auth_manager = FinamAuthManager(
                channel=mock_channel,
                client_id="test-client",
                access_token="test-token",
            )

            # Act - Make 5 concurrent refresh requests
            tasks = [auth_manager._refresh_jwt_token() for _ in range(5)]
            results = await asyncio.gather(*tasks)

            # Assert
            # All should get the same token
            assert all(r == "thread-safe-token" for r in results)
            # But auth should only be called once due to lock
            assert mock_stub.Auth.call_count == 1


class TestFinamAuthManagerCreateMetadata:
    """Test gRPC metadata creation."""

    @pytest.mark.asyncio
    async def test_create_metadata_includes_token_and_app_name(self):
        """Test that metadata includes JWT token and app name."""
        # Arrange
        mock_channel = Mock()
        mock_stub = AsyncMock()
        mock_response = _create_mock_auth_response("metadata-token")
        mock_stub.Auth.return_value = mock_response

        with patch("nautilus_trader.adapters.finam.grpc.client.auth.auth_service_pb2_grpc.AuthServiceStub", return_value=mock_stub):
            auth_manager = FinamAuthManager(
                channel=mock_channel,
                client_id="test-client",
                access_token="test-token",
            )

            # Act
            metadata = await auth_manager.create_metadata()

            # Assert
            assert isinstance(metadata, list)
            assert ("authorization", "metadata-token") in metadata
            assert ("x-app-name", "NautilusTrader") in metadata


class TestFinamAuthManagerInvalidate:
    """Test token invalidation."""

    @pytest.mark.asyncio
    async def test_invalidate_clears_token(self):
        """Test that invalidate clears current token."""
        # Arrange
        mock_channel = Mock()
        mock_stub = AsyncMock()
        mock_response = _create_mock_auth_response("to-be-invalidated")
        mock_stub.Auth.return_value = mock_response

        with patch("nautilus_trader.adapters.finam.grpc.client.auth.auth_service_pb2_grpc.AuthServiceStub", return_value=mock_stub):
            auth_manager = FinamAuthManager(
                channel=mock_channel,
                client_id="test-client",
                access_token="test-token",
            )

            # Get a token first
            await auth_manager.get_jwt_token()
            assert auth_manager._jwt_token is not None
            assert auth_manager._jwt_expires_at is not None

            # Act
            auth_manager.invalidate()

            # Assert
            assert auth_manager._jwt_token is None
            assert auth_manager._jwt_expires_at is None

    @pytest.mark.asyncio
    async def test_invalidate_forces_refresh_on_next_get(self):
        """Test that after invalidation, next get_jwt_token fetches new token."""
        # Arrange
        mock_channel = Mock()
        mock_stub = AsyncMock()
        mock_stub.Auth.side_effect = [
            _create_mock_auth_response("first-token"),
            _create_mock_auth_response("second-token"),
        ]

        with patch("nautilus_trader.adapters.finam.grpc.client.auth.auth_service_pb2_grpc.AuthServiceStub", return_value=mock_stub):
            auth_manager = FinamAuthManager(
                channel=mock_channel,
                client_id="test-client",
                access_token="test-token",
            )

            # Get first token
            token1 = await auth_manager.get_jwt_token()
            assert token1 == "first-token"
            assert mock_stub.Auth.call_count == 1

            # Act - Invalidate
            auth_manager.invalidate()

            # Get token again (should fetch new)
            token2 = await auth_manager.get_jwt_token()

            # Assert
            assert token2 == "second-token"
            assert mock_stub.Auth.call_count == 2


class TestFinamAuthManagerAutoRefresh:
    """Test automatic token refresh."""

    @pytest.mark.asyncio
    async def test_start_auto_refresh_starts_task(self):
        """Test that start_auto_refresh starts background task."""
        # Arrange
        mock_channel = Mock()
        mock_stub = AsyncMock()
        mock_stub.Auth.return_value = _create_mock_auth_response("auto-refresh-token")

        with patch("nautilus_trader.adapters.finam.grpc.client.auth.auth_service_pb2_grpc.AuthServiceStub", return_value=mock_stub):
            auth_manager = FinamAuthManager(
                channel=mock_channel,
                client_id="test-client",
                access_token="test-token",
            )

            # Act
            await auth_manager.start_auto_refresh()

            # Assert
            assert auth_manager._auto_refresh_task is not None
            assert not auth_manager._auto_refresh_task.done()

            # Cleanup
            await auth_manager.stop_auto_refresh()

    @pytest.mark.asyncio
    async def test_start_auto_refresh_idempotent(self):
        """Test that start_auto_refresh is idempotent."""
        # Arrange
        mock_channel = Mock()
        mock_stub = AsyncMock()
        mock_stub.Auth.return_value = _create_mock_auth_response("token")

        with patch("nautilus_trader.adapters.finam.grpc.client.auth.auth_service_pb2_grpc.AuthServiceStub", return_value=mock_stub):
            auth_manager = FinamAuthManager(
                channel=mock_channel,
                client_id="test-client",
                access_token="test-token",
            )

            # Act - Start twice
            await auth_manager.start_auto_refresh()
            task1 = auth_manager._auto_refresh_task

            await auth_manager.start_auto_refresh()
            task2 = auth_manager._auto_refresh_task

            # Assert - Should be same task
            assert task1 is task2

            # Cleanup
            await auth_manager.stop_auto_refresh()

    @pytest.mark.asyncio
    async def test_stop_auto_refresh_cancels_task(self):
        """Test that stop_auto_refresh cancels background task."""
        # Arrange
        mock_channel = Mock()
        mock_stub = AsyncMock()
        mock_stub.Auth.return_value = _create_mock_auth_response("token")

        with patch("nautilus_trader.adapters.finam.grpc.client.auth.auth_service_pb2_grpc.AuthServiceStub", return_value=mock_stub):
            auth_manager = FinamAuthManager(
                channel=mock_channel,
                client_id="test-client",
                access_token="test-token",
            )

            await auth_manager.start_auto_refresh()
            assert auth_manager._auto_refresh_task is not None

            # Act
            await auth_manager.stop_auto_refresh()

            # Assert
            assert auth_manager._auto_refresh_task is None

    @pytest.mark.asyncio
    async def test_stop_auto_refresh_safe_when_not_started(self):
        """Test that stop_auto_refresh is safe when auto-refresh not started."""
        # Arrange
        mock_channel = Mock()
        auth_manager = FinamAuthManager(
            channel=mock_channel,
            client_id="test-client",
            access_token="test-token",
        )

        # Act, Assert - Should not raise
        await auth_manager.stop_auto_refresh()
        assert auth_manager._auto_refresh_task is None
