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
Unit tests for HistoricFinamClient.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from nautilus_trader.adapters.finam.historical import HistoricFinamClient
from nautilus_trader.adapters.finam.grpc.common.enums import TimeFrame
from nautilus_trader.model.data import Bar, BarSpecification
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue


class TestHistoricFinamClient:
    """Unit tests for HistoricFinamClient."""

    def test_init_creates_client(self):
        """
        Test that HistoricFinamClient initializes correctly.
        """
        # Arrange, Act
        client = HistoricFinamClient(
            access_token="test_token_123",
            client_id=1,
            log_level="INFO",
        )

        # Assert
        assert client._clock is not None
        assert client.log is not None
        assert client._client is not None
        assert client._bars_stream is None  # Not initialized until connect()
        assert client._instrument_provider is None

    def test_init_with_custom_client_id(self):
        """
        Test initialization with custom client_id.
        """
        # Arrange, Act
        client = HistoricFinamClient(
            access_token="test_token",
            client_id=42,
            log_level="DEBUG",
        )

        # Assert
        assert client._client is not None

    @pytest.mark.asyncio
    async def test_connect_initializes_components(self):
        """
        Test that connect() initializes stream managers and providers.
        """
        # Arrange
        client = HistoricFinamClient(
            access_token="test_token",
            client_id=1,
        )

        # Mock gRPC client connect
        with patch.object(client._client, "connect", new_callable=AsyncMock):
            # Act
            await client.connect()

            # Assert
            assert client._bars_stream is not None
            assert client._instrument_provider is not None

    @pytest.mark.asyncio
    async def test_connect_raises_on_failure(self):
        """
        Test that connect() raises ConnectionError on failure.
        """
        # Arrange
        client = HistoricFinamClient(access_token="test_token", client_id=1)

        # Mock connect to raise exception
        with patch.object(
            client._client,
            "connect",
            new_callable=AsyncMock,
            side_effect=Exception("Connection failed"),
        ):
            # Act, Assert
            with pytest.raises(ConnectionError, match="Failed to connect"):
                await client.connect()

    @pytest.mark.asyncio
    async def test_disconnect_closes_connection(self):
        """
        Test that disconnect() properly closes gRPC connection.
        """
        # Arrange
        client = HistoricFinamClient(access_token="test_token", client_id=1)

        with patch.object(client._client, "connect", new_callable=AsyncMock):
            await client.connect()

        # Mock disconnect
        with patch.object(client._client, "disconnect", new_callable=AsyncMock) as mock_disconnect:
            # Act
            await client.disconnect()

            # Assert
            mock_disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_bars_validates_parameters(self):
        """
        Test that request_bars() validates input parameters after connection.
        """
        # Arrange
        client = HistoricFinamClient(access_token="test_token", client_id=1)

        with patch.object(client._client, "connect", new_callable=AsyncMock):
            await client.connect()

        # Act, Assert - No contracts or instrument_ids
        with pytest.raises(ValueError, match="Either contracts or instrument_ids must be provided"):
            await client.request_bars(
                bar_specifications=["1-MINUTE-LAST"],
                start_date_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
                end_date_time=datetime(2024, 1, 7, tzinfo=timezone.utc),
            )

    @pytest.mark.asyncio
    async def test_request_bars_validates_date_range(self):
        """
        Test that request_bars() validates start < end.
        """
        # Arrange
        client = HistoricFinamClient(access_token="test_token", client_id=1)

        with patch.object(client._client, "connect", new_callable=AsyncMock):
            await client.connect()

        # Act, Assert
        with pytest.raises(ValueError, match="start_date_time must be before end_date_time"):
            await client.request_bars(
                bar_specifications=["1-MINUTE-LAST"],
                start_date_time=datetime(2024, 1, 7, tzinfo=timezone.utc),
                end_date_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
                contracts=[{"symbol": "SiZ5@RTSX", "name": "Si Dec 2025"}],
            )

    @pytest.mark.asyncio
    async def test_request_bars_requires_connection(self):
        """
        Test that request_bars() raises error if not connected.
        """
        # Arrange
        client = HistoricFinamClient(access_token="test_token", client_id=1)

        # Act, Assert
        with pytest.raises(RuntimeError, match="Not connected"):
            await client.request_bars(
                bar_specifications=["1-MINUTE-LAST"],
                start_date_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
                end_date_time=datetime(2024, 1, 7, tzinfo=timezone.utc),
                contracts=[{"symbol": "SiZ5@RTSX"}],
            )

    @pytest.mark.asyncio
    async def test_request_bars_validates_contract_format(self):
        """
        Test that request_bars() validates contract dict format.
        """
        # Arrange
        client = HistoricFinamClient(access_token="test_token", client_id=1)

        with patch.object(client._client, "connect", new_callable=AsyncMock):
            await client.connect()

        # Mock BarsStreamManager
        client._bars_stream.request_historical_bars = AsyncMock(return_value=[])

        # Act - Missing 'symbol' field
        bars = await client.request_bars(
            bar_specifications=["1-MINUTE-LAST"],
            start_date_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date_time=datetime(2024, 1, 7, tzinfo=timezone.utc),
            contracts=[{"name": "Si Dec 2025"}],  # Missing symbol
        )

        # Assert - Should skip invalid contract and return empty list
        assert len(bars) == 0

    @pytest.mark.asyncio
    async def test_request_instruments_requires_connection(self):
        """
        Test that request_instruments() raises error if not connected.
        """
        # Arrange
        client = HistoricFinamClient(access_token="test_token", client_id=1)

        # Act, Assert
        with pytest.raises(RuntimeError, match="Not connected"):
            await client.request_instruments(
                contracts=[{"symbol": "SiZ5@RTSX"}]
            )

    @pytest.mark.asyncio
    async def test_request_instruments_validates_parameters(self):
        """
        Test that request_instruments() validates parameters.
        """
        # Arrange
        client = HistoricFinamClient(access_token="test_token", client_id=1)

        with patch.object(client._client, "connect", new_callable=AsyncMock):
            await client.connect()

        # Act, Assert
        with pytest.raises(ValueError, match="Either contracts or instrument_ids must be provided"):
            await client.request_instruments()

    def test_bar_spec_to_timeframe_minute(self):
        """
        Test mapping of MINUTE bar specs to TimeFrame.
        """
        # Arrange
        client = HistoricFinamClient(access_token="test_token", client_id=1)

        # Act, Assert - M1
        spec = BarSpecification.from_str("1-MINUTE-LAST")
        assert client._bar_spec_to_timeframe(spec) == TimeFrame.M1

        # M5
        spec = BarSpecification.from_str("5-MINUTE-LAST")
        assert client._bar_spec_to_timeframe(spec) == TimeFrame.M5

        # M15
        spec = BarSpecification.from_str("15-MINUTE-LAST")
        assert client._bar_spec_to_timeframe(spec) == TimeFrame.M15

        # M30
        spec = BarSpecification.from_str("30-MINUTE-LAST")
        assert client._bar_spec_to_timeframe(spec) == TimeFrame.M30

    def test_bar_spec_to_timeframe_hour(self):
        """
        Test mapping of HOUR bar specs to TimeFrame.
        """
        # Arrange
        client = HistoricFinamClient(access_token="test_token", client_id=1)

        # Act, Assert - H1
        spec = BarSpecification.from_str("1-HOUR-LAST")
        assert client._bar_spec_to_timeframe(spec) == TimeFrame.H1

        # H2
        spec = BarSpecification.from_str("2-HOUR-LAST")
        assert client._bar_spec_to_timeframe(spec) == TimeFrame.H2

        # H4
        spec = BarSpecification.from_str("4-HOUR-LAST")
        assert client._bar_spec_to_timeframe(spec) == TimeFrame.H4

        # H8
        spec = BarSpecification.from_str("8-HOUR-LAST")
        assert client._bar_spec_to_timeframe(spec) == TimeFrame.H8

    def test_bar_spec_to_timeframe_day_week_month(self):
        """
        Test mapping of DAY/WEEK/MONTH bar specs to TimeFrame.
        """
        # Arrange
        client = HistoricFinamClient(access_token="test_token", client_id=1)

        # Act, Assert - Daily
        spec = BarSpecification.from_str("1-DAY-LAST")
        assert client._bar_spec_to_timeframe(spec) == TimeFrame.D

        # Weekly
        spec = BarSpecification.from_str("1-WEEK-LAST")
        assert client._bar_spec_to_timeframe(spec) == TimeFrame.W

        # Monthly
        spec = BarSpecification.from_str("1-MONTH-LAST")
        assert client._bar_spec_to_timeframe(spec) == TimeFrame.MN

    def test_bar_spec_to_timeframe_unsupported(self):
        """
        Test that unsupported bar specs raise ValueError.
        """
        # Arrange
        client = HistoricFinamClient(access_token="test_token", client_id=1)

        # Act, Assert - 3-MINUTE not supported
        spec = BarSpecification.from_str("3-MINUTE-LAST")
        with pytest.raises(ValueError, match="Unsupported bar specification"):
            client._bar_spec_to_timeframe(spec)

        # 10-MINUTE not supported
        spec = BarSpecification.from_str("10-MINUTE-LAST")
        with pytest.raises(ValueError, match="Unsupported bar specification"):
            client._bar_spec_to_timeframe(spec)

        # 3-HOUR not supported
        spec = BarSpecification.from_str("3-HOUR-LAST")
        with pytest.raises(ValueError, match="Unsupported bar specification"):
            client._bar_spec_to_timeframe(spec)
