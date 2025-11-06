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
Integration tests for HistoricFinamClient with real API calls.

These tests require valid Finam API credentials in environment variables:
- FINAM_ACCESS_TOKEN
- FINAM_CLIENT_ID

Tests are skipped if credentials are not available.
"""

import os
import pytest
from datetime import datetime, timezone, timedelta

from nautilus_trader.adapters.finam.historical import HistoricFinamClient
from nautilus_trader.model.data import Bar
from nautilus_trader.model.instruments import Instrument


# Check for credentials (support both naming conventions)
FINAM_ACCESS_TOKEN = os.getenv("FINAM_ACCESS_TOKEN") or os.getenv("FINAM_SECRET_TOKEN")
FINAM_CLIENT_ID = os.getenv("FINAM_CLIENT_ID") or os.getenv("FINAM_ACCOUNT_ID")
HAS_CREDENTIALS = FINAM_ACCESS_TOKEN and FINAM_CLIENT_ID

skip_if_no_credentials = pytest.mark.skipif(
    not HAS_CREDENTIALS,
    reason="Finam API credentials not available. Set either: "
    "(FINAM_ACCESS_TOKEN, FINAM_CLIENT_ID) or (FINAM_SECRET_TOKEN, FINAM_ACCOUNT_ID)",
)


@pytest.mark.asyncio
@skip_if_no_credentials
class TestHistoricFinamClientIntegration:
    """Integration tests for HistoricFinamClient with real API."""

    async def test_connect_to_real_api(self):
        """
        Test successful connection to real Finam API.
        """
        # Arrange
        client = HistoricFinamClient(
            access_token=FINAM_ACCESS_TOKEN,
            client_id=int(FINAM_CLIENT_ID),
        )

        # Act
        await client.connect()

        # Assert
        assert client._bars_stream is not None
        assert client._instrument_provider is not None

        # Cleanup
        await client.disconnect()

    async def test_request_instruments_real_api(self):
        """
        Test requesting instruments from real API.
        """
        # Arrange
        client = HistoricFinamClient(
            access_token=FINAM_ACCESS_TOKEN,
            client_id=int(FINAM_CLIENT_ID),
        )
        await client.connect()

        # Sample contract (Si futures on MOEX)
        contracts = [
            {
                "symbol": "SiZ5@RTSX",
                "name": "Si декабрь 2025",
                "start": "2024-06-18",
                "expiry": "2025-12-18",
            }
        ]

        # Act
        instruments = await client.request_instruments(contracts=contracts)

        # Assert
        assert len(instruments) > 0
        assert all(isinstance(inst, Instrument) for inst in instruments)

        # Verify instrument details
        si_instrument = instruments[0]
        assert "Si" in str(si_instrument.id.symbol)
        assert si_instrument.id.venue.value == "FINAM"

        # Cleanup
        await client.disconnect()

    async def test_request_bars_real_api_short_range(self):
        """
        Test requesting bars from real API with short date range.

        Uses a short date range (1 day) to minimize API load.
        """
        # Arrange
        client = HistoricFinamClient(
            access_token=FINAM_ACCESS_TOKEN,
            client_id=int(FINAM_CLIENT_ID),
        )
        await client.connect()

        # Sample contract and date range (1 day, recent data)
        contracts = [{"symbol": "SiZ5@RTSX", "name": "Si декабрь 2025"}]
        end_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = end_date - timedelta(days=1)

        # Act
        bars = await client.request_bars(
            bar_specifications=["1-HOUR-LAST"],
            start_date_time=start_date,
            end_date_time=end_date,
            contracts=contracts,
        )

        # Assert
        assert isinstance(bars, list)
        # Note: May be empty if no trading on that day
        if len(bars) > 0:
            assert all(isinstance(bar, Bar) for bar in bars)
            assert all(bar.bar_type.instrument_id.venue.value == "FINAM" for bar in bars)

        # Cleanup
        await client.disconnect()

    async def test_request_bars_multiple_instruments(self):
        """
        Test requesting bars for multiple instruments simultaneously.
        """
        # Arrange
        client = HistoricFinamClient(
            access_token=FINAM_ACCESS_TOKEN,
            client_id=int(FINAM_CLIENT_ID),
        )
        await client.connect()

        # Multiple contracts
        contracts = [
            {"symbol": "SiZ5@RTSX", "name": "Si декабрь 2025"},
            {"symbol": "RIZ5@RTSX", "name": "RTS декабрь 2025"},
        ]
        end_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = end_date - timedelta(days=1)

        # Act
        bars = await client.request_bars(
            bar_specifications=["1-DAY-LAST"],
            start_date_time=start_date,
            end_date_time=end_date,
            contracts=contracts,
        )

        # Assert
        assert isinstance(bars, list)
        if len(bars) > 0:
            # Should have bars from different instruments
            unique_instruments = {bar.bar_type.instrument_id.symbol.value for bar in bars}
            # At least one instrument should have data
            assert len(unique_instruments) >= 1

        # Cleanup
        await client.disconnect()

    async def test_request_bars_multiple_timeframes(self):
        """
        Test requesting multiple timeframes for same instrument.
        """
        # Arrange
        client = HistoricFinamClient(
            access_token=FINAM_ACCESS_TOKEN,
            client_id=int(FINAM_CLIENT_ID),
        )
        await client.connect()

        contracts = [{"symbol": "SiZ5@RTSX"}]
        end_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = end_date - timedelta(days=2)

        # Act - Request both 1-hour and 1-day bars
        bars = await client.request_bars(
            bar_specifications=["1-HOUR-LAST", "1-DAY-LAST"],
            start_date_time=start_date,
            end_date_time=end_date,
            contracts=contracts,
        )

        # Assert
        assert isinstance(bars, list)
        if len(bars) > 0:
            # Should have different timeframes
            unique_specs = {str(bar.bar_type.spec) for bar in bars}
            # At least one timeframe should have data
            assert len(unique_specs) >= 1

        # Cleanup
        await client.disconnect()

    async def test_reconnection_after_disconnect(self):
        """
        Test that client can reconnect after disconnect.
        """
        # Arrange
        client = HistoricFinamClient(
            access_token=FINAM_ACCESS_TOKEN,
            client_id=int(FINAM_CLIENT_ID),
        )

        # Act - Connect, disconnect, reconnect
        await client.connect()
        assert client._bars_stream is not None

        await client.disconnect()

        await client.connect()
        assert client._bars_stream is not None

        # Verify it's functional
        contracts = [{"symbol": "SiZ5@RTSX"}]
        instruments = await client.request_instruments(contracts=contracts)
        assert len(instruments) > 0

        # Cleanup
        await client.disconnect()

    async def test_error_handling_invalid_symbol(self):
        """
        Test error handling with invalid symbol.
        """
        # Arrange
        client = HistoricFinamClient(
            access_token=FINAM_ACCESS_TOKEN,
            client_id=int(FINAM_CLIENT_ID),
        )
        await client.connect()

        # Invalid contract
        contracts = [{"symbol": "INVALID_SYMBOL_12345@INVALID"}]
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=1)

        # Act - Should handle gracefully
        bars = await client.request_bars(
            bar_specifications=["1-DAY-LAST"],
            start_date_time=start_date,
            end_date_time=end_date,
            contracts=contracts,
        )

        # Assert - Should return empty list or handle error gracefully
        assert isinstance(bars, list)
        # Invalid symbols should be skipped or return empty

        # Cleanup
        await client.disconnect()

    async def test_concurrent_requests(self):
        """
        Test that client handles multiple concurrent requests.
        """
        # Arrange
        client = HistoricFinamClient(
            access_token=FINAM_ACCESS_TOKEN,
            client_id=int(FINAM_CLIENT_ID),
        )
        await client.connect()

        contracts = [{"symbol": "SiZ5@RTSX"}]
        end_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = end_date - timedelta(days=1)

        # Act - Make concurrent requests
        import asyncio

        task1 = client.request_instruments(contracts=contracts)
        task2 = client.request_bars(
            bar_specifications=["1-DAY-LAST"],
            start_date_time=start_date,
            end_date_time=end_date,
            contracts=contracts,
        )

        results = await asyncio.gather(task1, task2)
        instruments, bars = results

        # Assert
        assert isinstance(instruments, list)
        assert isinstance(bars, list)

        # Cleanup
        await client.disconnect()
