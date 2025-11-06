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
Unit tests for Finam gRPC channel management.

Tests the FinamGrpcChannel class that manages gRPC channel lifecycle.
"""

import pytest
import grpc.aio
from unittest.mock import AsyncMock, Mock, patch

from nautilus_trader.adapters.finam.grpc.client.channel import FinamGrpcChannel


class TestFinamGrpcChannelInit:
    """Test FinamGrpcChannel initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        # Arrange, Act
        channel_manager = FinamGrpcChannel()

        # Assert
        assert channel_manager.host == "api.finam.ru"
        assert channel_manager.port == 443
        assert channel_manager.use_ssl is True
        assert channel_manager._channel is None

    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        # Arrange, Act
        channel_manager = FinamGrpcChannel(
            host="custom.host.com",
            port=8080,
            use_ssl=False,
        )

        # Assert
        assert channel_manager.host == "custom.host.com"
        assert channel_manager.port == 8080
        assert channel_manager.use_ssl is False


class TestFinamGrpcChannelConnect:
    """Test channel connection."""

    @pytest.mark.asyncio
    @patch("grpc.aio.secure_channel")
    async def test_connect_with_ssl(self, mock_secure_channel):
        """Test connecting with SSL creates secure channel."""
        # Arrange
        mock_channel = AsyncMock(spec=grpc.aio.Channel)
        mock_secure_channel.return_value = mock_channel

        channel_manager = FinamGrpcChannel(
            host="api.finam.ru",
            port=443,
            use_ssl=True,
        )

        # Act
        result = await channel_manager.connect()

        # Assert
        assert result == mock_channel
        assert channel_manager._channel == mock_channel
        mock_secure_channel.assert_called_once()

        # Verify target and SSL
        call_args = mock_secure_channel.call_args
        assert call_args[0][0] == "api.finam.ru:443"  # target
        assert call_args[1]["options"] is not None  # options provided

    @pytest.mark.asyncio
    @patch("grpc.aio.insecure_channel")
    async def test_connect_without_ssl(self, mock_insecure_channel):
        """Test connecting without SSL creates insecure channel."""
        # Arrange
        mock_channel = AsyncMock(spec=grpc.aio.Channel)
        mock_insecure_channel.return_value = mock_channel

        channel_manager = FinamGrpcChannel(
            host="localhost",
            port=50051,
            use_ssl=False,
        )

        # Act
        result = await channel_manager.connect()

        # Assert
        assert result == mock_channel
        assert channel_manager._channel == mock_channel
        mock_insecure_channel.assert_called_once()

        # Verify target
        call_args = mock_insecure_channel.call_args
        assert call_args[0][0] == "localhost:50051"  # target

    @pytest.mark.asyncio
    @patch("grpc.aio.secure_channel")
    async def test_connect_idempotent(self, mock_secure_channel):
        """Test that connect() is idempotent (doesn't create new channel if already connected)."""
        # Arrange
        mock_channel = AsyncMock(spec=grpc.aio.Channel)
        mock_secure_channel.return_value = mock_channel

        channel_manager = FinamGrpcChannel()

        # Act
        result1 = await channel_manager.connect()
        result2 = await channel_manager.connect()  # Second connect

        # Assert
        assert result1 == result2
        assert result1 == mock_channel
        # Should only create channel once
        assert mock_secure_channel.call_count == 1

    @pytest.mark.asyncio
    @patch("grpc.aio.secure_channel")
    async def test_connect_creates_channel_with_options(self, mock_secure_channel):
        """Test that channel is created with proper gRPC options."""
        # Arrange
        mock_channel = AsyncMock(spec=grpc.aio.Channel)
        mock_secure_channel.return_value = mock_channel

        channel_manager = FinamGrpcChannel()

        # Act
        await channel_manager.connect()

        # Assert
        call_args = mock_secure_channel.call_args
        options = call_args[1]["options"]

        # Verify critical options are present
        options_dict = dict(options)
        assert options_dict['grpc.max_receive_message_length'] == -1
        assert options_dict['grpc.max_send_message_length'] == -1
        assert options_dict['grpc.keepalive_time_ms'] == 30000
        assert options_dict['grpc.enable_retries'] == 1


class TestFinamGrpcChannelClose:
    """Test channel closing."""

    @pytest.mark.asyncio
    @patch("grpc.aio.secure_channel")
    async def test_close_closes_channel(self, mock_secure_channel):
        """Test that close() closes the gRPC channel."""
        # Arrange
        mock_channel = AsyncMock(spec=grpc.aio.Channel)
        mock_secure_channel.return_value = mock_channel

        channel_manager = FinamGrpcChannel()
        await channel_manager.connect()

        # Act
        await channel_manager.close()

        # Assert
        mock_channel.close.assert_called_once()
        assert channel_manager._channel is None

    @pytest.mark.asyncio
    async def test_close_when_not_connected(self):
        """Test that close() is safe when not connected."""
        # Arrange
        channel_manager = FinamGrpcChannel()

        # Act, Assert - Should not raise
        await channel_manager.close()


class TestFinamGrpcChannelContextManager:
    """Test async context manager functionality."""

    @pytest.mark.asyncio
    @patch("grpc.aio.secure_channel")
    async def test_context_manager_connects_and_closes(self, mock_secure_channel):
        """Test that context manager connects on entry and closes on exit."""
        # Arrange
        mock_channel = AsyncMock(spec=grpc.aio.Channel)
        mock_secure_channel.return_value = mock_channel

        channel_manager = FinamGrpcChannel()

        # Act
        async with channel_manager as channel:
            # Assert - Connected
            assert channel == mock_channel
            assert channel_manager._channel == mock_channel
            mock_channel.close.assert_not_called()

        # Assert - Closed after context
        mock_channel.close.assert_called_once()
        assert channel_manager._channel is None

    @pytest.mark.asyncio
    @patch("grpc.aio.secure_channel")
    async def test_context_manager_closes_on_exception(self, mock_secure_channel):
        """Test that context manager closes channel even on exception."""
        # Arrange
        mock_channel = AsyncMock(spec=grpc.aio.Channel)
        mock_secure_channel.return_value = mock_channel

        channel_manager = FinamGrpcChannel()

        # Act, Assert
        with pytest.raises(ValueError):
            async with channel_manager:
                raise ValueError("Test error")

        # Channel should still be closed
        mock_channel.close.assert_called_once()
        assert channel_manager._channel is None
