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
Shared fixtures for Finam historical client tests.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from decimal import Decimal


@pytest.fixture(autouse=True)
def mock_logging():
    """
    Automatically mock init_logging for all tests in this module.

    Nautilus logging can only be initialized once, so we need to mock it
    for unit tests that create multiple HistoricFinamClient instances.
    """
    with patch("nautilus_trader.adapters.finam.historical.client.init_logging") as mock:
        mock.return_value = MagicMock()
        yield mock


def _create_proto_decimal(value_str: str):
    """
    Create a mock protobuf Decimal with .value attribute.

    Protobuf Decimal has a .value string attribute, not a Python Decimal object.
    """
    decimal = MagicMock()
    decimal.value = value_str
    return decimal


@pytest.fixture
def mock_proto_bar():
    """
    Create a mock protobuf bar for testing.

    Returns
    -------
    MagicMock
        A mock bar object with typical OHLCV data.

    """
    bar = MagicMock()
    bar.open = _create_proto_decimal("100000.0")
    bar.high = _create_proto_decimal("101000.0")
    bar.low = _create_proto_decimal("99000.0")
    bar.close = _create_proto_decimal("100500.0")
    bar.volume = _create_proto_decimal("5000.0")

    # Mock timestamp
    bar.HasField = lambda field: field == "timestamp"
    timestamp = MagicMock()
    timestamp.seconds = 1704067200  # 2024-01-01 00:00:00 UTC
    timestamp.nanos = 0
    bar.timestamp = timestamp

    return bar


@pytest.fixture
def sample_contracts():
    """
    Sample contract list for testing.

    Returns
    -------
    list[dict]
        List of sample contract dictionaries with symbol, name, start, and expiry.

    """
    return [
        {
            "symbol": "SiZ5@RTSX",
            "name": "Si декабрь 2025",
            "start": "2024-06-18",
            "expiry": "2025-12-18",
        },
        {
            "symbol": "RIZ5@RTSX",
            "name": "RTS декабрь 2025",
            "start": "2024-06-18",
            "expiry": "2025-12-18",
        },
        {
            "symbol": "GAZR@MOEX",
            "name": "Газпром",
            "start": "2000-01-01",
            "expiry": None,  # No expiry for stocks
        },
    ]


@pytest.fixture
def sample_bar_specifications():
    """
    Sample bar specification strings for testing.

    Returns
    -------
    list[str]
        List of valid bar specification strings.

    """
    return [
        "1-MINUTE-LAST",
        "5-MINUTE-LAST",
        "15-MINUTE-LAST",
        "30-MINUTE-LAST",
        "1-HOUR-LAST",
        "1-DAY-LAST",
    ]


@pytest.fixture
def sample_date_range():
    """
    Sample date range for testing.

    Returns
    -------
    tuple[datetime, datetime]
        Start and end datetime objects (UTC).

    """
    return (
        datetime(2024, 1, 1, tzinfo=timezone.utc),
        datetime(2024, 1, 7, tzinfo=timezone.utc),
    )
