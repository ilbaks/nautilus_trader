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
Unit tests for main Finam gRPC client.

Tests the FinamGrpcClient class that provides access to all gRPC services.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock

from nautilus_trader.adapters.finam.grpc.client.client import FinamGrpcClient


class TestFinamGrpcClientInit:
    """Test FinamGrpcClient initialization."""

    def test_init_with_minimal_params(self):
        """Test initialization with minimal required parameters."""
        # Arrange, Act
        client = FinamGrpcClient(
            client_id="test-client",
            access_token="test-token",
        )

        # Assert
        assert client._client_id == "test-client"
        assert client._access_token == "test-token"
        assert client._channel is None
        assert client._auth_manager is None
        assert client._rate_limiter is not None

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        # Arrange, Act
        client = FinamGrpcClient(
            client_id="custom-client",
            access_token="custom-token",
            host="custom.host.com",
            port=8080,
            use_ssl=False,
            rate_limit_requests=50,
            rate_limit_window=30.0,
            auto_refresh_token=False,
        )

        # Assert
        assert client._client_id == "custom-client"
        assert client._access_token == "custom-token"
        assert client._auto_refresh_token is False
        assert client._channel_manager.host == "custom.host.com"
        assert client._channel_manager.port == 8080
        assert client._channel_manager.use_ssl is False
        assert client._rate_limiter._max_requests == 50
        assert client._rate_limiter._time_window == 30.0


class TestFinamGrpcClientConnect:
    """Test client connection."""

    @pytest.mark.asyncio
    @patch("nautilus_trader.adapters.finam.grpc.client.client.FinamGrpcChannel")
    @patch("nautilus_trader.adapters.finam.grpc.client.client.FinamAuthManager")
    async def test_connect_initializes_components(self, mock_auth_class, mock_channel_class):
        """Test that connect() initializes all components."""
        # Arrange
        mock_channel_instance = AsyncMock()
        mock_channel = AsyncMock()
        mock_channel_instance.connect.return_value = mock_channel
        mock_channel_class.return_value = mock_channel_instance

        mock_auth_instance = AsyncMock()
        mock_auth_class.return_value = mock_auth_instance

        client = FinamGrpcClient(
            client_id="test-client",
            access_token="test-token",
        )

        # Act
        await client.connect()

        # Assert
        mock_channel_instance.connect.assert_called_once()
        assert client._channel == mock_channel
        assert client._auth_manager == mock_auth_instance

        # Should initialize service stubs
        assert client._auth_stub is not None
        assert client._assets_stub is not None
        assert client._accounts_stub is not None
        assert client._marketdata_stub is not None
        assert client._orders_stub is not None

        # Should start auto-refresh if enabled
        mock_auth_instance.start_auto_refresh.assert_called_once()

    @pytest.mark.asyncio
    @patch("nautilus_trader.adapters.finam.grpc.client.client.FinamGrpcChannel")
    async def test_connect_idempotent(self, mock_channel_class):
        """Test that connect() is idempotent."""
        # Arrange
        mock_channel_instance = AsyncMock()
        mock_channel = AsyncMock()
        mock_channel_instance.connect.return_value = mock_channel
        mock_channel_class.return_value = mock_channel_instance

        client = FinamGrpcClient(
            client_id="test-client",
            access_token="test-token",
        )

        # Act
        await client.connect()
        await client.connect()  # Second connect

        # Assert - Should only connect once
        assert mock_channel_instance.connect.call_count == 1

    @pytest.mark.asyncio
    @patch("nautilus_trader.adapters.finam.grpc.client.client.FinamGrpcChannel")
    @patch("nautilus_trader.adapters.finam.grpc.client.client.FinamAuthManager")
    async def test_connect_without_auto_refresh(self, mock_auth_class, mock_channel_class):
        """Test connect with auto_refresh_token=False doesn't start refresh."""
        # Arrange
        mock_channel_instance = AsyncMock()
        mock_channel = AsyncMock()
        mock_channel_instance.connect.return_value = mock_channel
        mock_channel_class.return_value = mock_channel_instance

        mock_auth_instance = AsyncMock()
        mock_auth_class.return_value = mock_auth_instance

        client = FinamGrpcClient(
            client_id="test-client",
            access_token="test-token",
            auto_refresh_token=False,
        )

        # Act
        await client.connect()

        # Assert - Should NOT start auto-refresh
        mock_auth_instance.start_auto_refresh.assert_not_called()


class TestFinamGrpcClientDisconnect:
    """Test client disconnection."""

    @pytest.mark.asyncio
    @patch("nautilus_trader.adapters.finam.grpc.client.client.FinamGrpcChannel")
    @patch("nautilus_trader.adapters.finam.grpc.client.client.FinamAuthManager")
    async def test_disconnect_cleanup(self, mock_auth_class, mock_channel_class):
        """Test that disconnect() cleans up all resources."""
        # Arrange
        mock_channel_instance = AsyncMock()
        mock_channel = AsyncMock()
        mock_channel_instance.connect.return_value = mock_channel
        mock_channel_class.return_value = mock_channel_instance

        mock_auth_instance = AsyncMock()
        mock_auth_class.return_value = mock_auth_instance

        client = FinamGrpcClient(
            client_id="test-client",
            access_token="test-token",
        )

        await client.connect()

        # Act
        await client.disconnect()

        # Assert
        mock_auth_instance.stop_auto_refresh.assert_called_once()
        mock_channel_instance.close.assert_called_once()

        # All state should be cleared
        assert client._channel is None
        assert client._auth_manager is None
        assert client._auth_stub is None
        assert client._assets_stub is None
        assert client._accounts_stub is None
        assert client._marketdata_stub is None
        assert client._orders_stub is None


class TestFinamGrpcClientGetMetadata:
    """Test metadata retrieval."""

    @pytest.mark.asyncio
    @patch("nautilus_trader.adapters.finam.grpc.client.client.FinamGrpcChannel")
    @patch("nautilus_trader.adapters.finam.grpc.client.client.FinamAuthManager")
    async def test_get_metadata_returns_auth_metadata(self, mock_auth_class, mock_channel_class):
        """Test that get_metadata returns metadata from auth manager."""
        # Arrange
        mock_channel_instance = AsyncMock()
        mock_channel = AsyncMock()
        mock_channel_instance.connect.return_value = mock_channel
        mock_channel_class.return_value = mock_channel_instance

        mock_auth_instance = AsyncMock()
        mock_auth_instance.create_metadata.return_value = [
            ("authorization", "test-jwt"),
            ("x-app-name", "NautilusTrader"),
        ]
        mock_auth_class.return_value = mock_auth_instance

        client = FinamGrpcClient(
            client_id="test-client",
            access_token="test-token",
        )

        await client.connect()

        # Act
        metadata = await client.get_metadata()

        # Assert
        assert metadata == [
            ("authorization", "test-jwt"),
            ("x-app-name", "NautilusTrader"),
        ]
        mock_auth_instance.create_metadata.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_metadata_raises_if_not_connected(self):
        """Test that get_metadata raises if not connected."""
        # Arrange
        client = FinamGrpcClient(
            client_id="test-client",
            access_token="test-token",
        )

        # Act, Assert
        with pytest.raises(RuntimeError, match="Client not connected"):
            await client.get_metadata()


class TestFinamGrpcClientServiceStubs:
    """Test service stub properties."""

    @pytest.mark.asyncio
    @patch("nautilus_trader.adapters.finam.grpc.client.client.FinamGrpcChannel")
    async def test_auth_stub_raises_if_not_connected(self, mock_channel_class):
        """Test that accessing auth stub raises if not connected."""
        # Arrange
        client = FinamGrpcClient(
            client_id="test-client",
            access_token="test-token",
        )

        # Act, Assert
        with pytest.raises(RuntimeError, match="Client not connected"):
            _ = client.auth

    @pytest.mark.asyncio
    @patch("nautilus_trader.adapters.finam.grpc.client.client.FinamGrpcChannel")
    async def test_assets_stub_raises_if_not_connected(self, mock_channel_class):
        """Test that accessing assets stub raises if not connected."""
        # Arrange
        client = FinamGrpcClient(
            client_id="test-client",
            access_token="test-token",
        )

        # Act, Assert
        with pytest.raises(RuntimeError, match="Client not connected"):
            _ = client.assets

    @pytest.mark.asyncio
    @patch("nautilus_trader.adapters.finam.grpc.client.client.FinamGrpcChannel")
    async def test_accounts_stub_raises_if_not_connected(self, mock_channel_class):
        """Test that accessing accounts stub raises if not connected."""
        # Arrange
        client = FinamGrpcClient(
            client_id="test-client",
            access_token="test-token",
        )

        # Act, Assert
        with pytest.raises(RuntimeError, match="Client not connected"):
            _ = client.accounts

    @pytest.mark.asyncio
    @patch("nautilus_trader.adapters.finam.grpc.client.client.FinamGrpcChannel")
    async def test_marketdata_stub_raises_if_not_connected(self, mock_channel_class):
        """Test that accessing marketdata stub raises if not connected."""
        # Arrange
        client = FinamGrpcClient(
            client_id="test-client",
            access_token="test-token",
        )

        # Act, Assert
        with pytest.raises(RuntimeError, match="Client not connected"):
            _ = client.marketdata

    @pytest.mark.asyncio
    @patch("nautilus_trader.adapters.finam.grpc.client.client.FinamGrpcChannel")
    async def test_orders_stub_raises_if_not_connected(self, mock_channel_class):
        """Test that accessing orders stub raises if not connected."""
        # Arrange
        client = FinamGrpcClient(
            client_id="test-client",
            access_token="test-token",
        )

        # Act, Assert
        with pytest.raises(RuntimeError, match="Client not connected"):
            _ = client.orders

    @pytest.mark.asyncio
    @patch("nautilus_trader.adapters.finam.grpc.client.client.FinamGrpcChannel")
    async def test_rate_limiter_always_accessible(self, mock_channel_class):
        """Test that rate_limiter property is always accessible."""
        # Arrange
        client = FinamGrpcClient(
            client_id="test-client",
            access_token="test-token",
        )

        # Act
        rate_limiter = client.rate_limiter

        # Assert - Should not raise, even without connect
        assert rate_limiter is not None


class TestFinamGrpcClientContextManager:
    """Test async context manager functionality."""

    @pytest.mark.asyncio
    @patch("nautilus_trader.adapters.finam.grpc.client.client.FinamGrpcChannel")
    @patch("nautilus_trader.adapters.finam.grpc.client.client.FinamAuthManager")
    async def test_context_manager_connects_and_disconnects(self, mock_auth_class, mock_channel_class):
        """Test that context manager connects on entry and disconnects on exit."""
        # Arrange
        mock_channel_instance = AsyncMock()
        mock_channel = AsyncMock()
        mock_channel_instance.connect.return_value = mock_channel
        mock_channel_class.return_value = mock_channel_instance

        mock_auth_instance = AsyncMock()
        mock_auth_class.return_value = mock_auth_instance

        client = FinamGrpcClient(
            client_id="test-client",
            access_token="test-token",
        )

        # Act
        async with client as c:
            # Assert - Connected
            assert c is client
            assert client._channel is not None
            mock_channel_instance.close.assert_not_called()

        # Assert - Disconnected after context
        mock_auth_instance.stop_auto_refresh.assert_called_once()
        mock_channel_instance.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("nautilus_trader.adapters.finam.grpc.client.client.FinamGrpcChannel")
    @patch("nautilus_trader.adapters.finam.grpc.client.client.FinamAuthManager")
    async def test_context_manager_disconnects_on_exception(self, mock_auth_class, mock_channel_class):
        """Test that context manager disconnects even on exception."""
        # Arrange
        mock_channel_instance = AsyncMock()
        mock_channel = AsyncMock()
        mock_channel_instance.connect.return_value = mock_channel
        mock_channel_class.return_value = mock_channel_instance

        mock_auth_instance = AsyncMock()
        mock_auth_class.return_value = mock_auth_instance

        client = FinamGrpcClient(
            client_id="test-client",
            access_token="test-token",
        )

        # Act, Assert
        with pytest.raises(ValueError):
            async with client:
                raise ValueError("Test error")

        # Should still disconnect
        mock_auth_instance.stop_auto_refresh.assert_called_once()
        mock_channel_instance.close.assert_called_once()
