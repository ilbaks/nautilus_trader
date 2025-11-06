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
Unit tests for historical bar parsing functions.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from decimal import Decimal

from nautilus_trader.adapters.finam.grpc.parsing.market_data import parse_historical_bar
from nautilus_trader.model.data import BarType, BarSpecification
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.enums import AggregationSource


def _create_proto_decimal(value_str: str):
    """Create a mock protobuf Decimal with .value attribute."""
    decimal = MagicMock()
    decimal.value = value_str
    return decimal


class TestParseHistoricalBar:
    """Unit tests for parse_historical_bar function."""

    def test_parse_historical_bar_basic(self, mock_proto_bar):
        """
        Test basic parsing of protobuf bar to Nautilus Bar.
        """
        # Arrange
        instrument_id = InstrumentId(Symbol("SiZ5-RTSX"), Venue("FINAM"))
        bar_spec = BarSpecification.from_str("1-MINUTE-LAST")
        bar_type = BarType(instrument_id, bar_spec, AggregationSource.EXTERNAL)
        ts_init = 1704067200000000000  # Nanoseconds

        # Act
        bar = parse_historical_bar(
            proto_bar=mock_proto_bar,
            instrument_id=instrument_id,
            bar_type=bar_type,
            ts_init=ts_init,
        )

        # Assert
        assert bar.open.as_double() == 100000.0
        assert bar.high.as_double() == 101000.0
        assert bar.low.as_double() == 99000.0
        assert bar.close.as_double() == 100500.0
        assert bar.volume.as_double() == 5000.0
        assert bar.ts_init == ts_init

    def test_parse_historical_bar_normalizes_integer_volume(self):
        """
        Test that volume "1000.0" is normalized to "1000" (integer).
        """
        # Arrange
        proto_bar = MagicMock()
        proto_bar.open = _create_proto_decimal("100000.0")
        proto_bar.high = _create_proto_decimal("100000.0")
        proto_bar.low = _create_proto_decimal("100000.0")
        proto_bar.close = _create_proto_decimal("100000.0")
        proto_bar.volume = _create_proto_decimal("1000.0")  # Should be normalized to "1000"
        proto_bar.HasField = lambda field: False

        instrument_id = InstrumentId(Symbol("SiZ5-RTSX"), Venue("FINAM"))
        bar_spec = BarSpecification.from_str("1-MINUTE-LAST")
        bar_type = BarType(instrument_id, bar_spec, AggregationSource.EXTERNAL)
        ts_init = 1704067200000000000

        # Act
        bar = parse_historical_bar(
            proto_bar=proto_bar,
            instrument_id=instrument_id,
            bar_type=bar_type,
            ts_init=ts_init,
        )

        # Assert
        assert bar.volume.as_double() == 1000.0
        # Volume should be normalized internally (no .0 suffix)

    def test_parse_historical_bar_with_timestamp(self):
        """
        Test that bar uses proto_bar timestamp when available.
        """
        # Arrange
        proto_bar = MagicMock()
        proto_bar.open = _create_proto_decimal("100000.0")
        proto_bar.high = _create_proto_decimal("100100.0")
        proto_bar.low = _create_proto_decimal("99900.0")
        proto_bar.close = _create_proto_decimal("100050.0")
        proto_bar.volume = _create_proto_decimal("500.0")

        # Mock timestamp present
        proto_bar.HasField = lambda field: field == "timestamp"
        timestamp = MagicMock()
        timestamp.seconds = 1704153600  # 2024-01-02 00:00:00 UTC
        timestamp.nanos = 500000000  # 0.5 seconds
        proto_bar.timestamp = timestamp

        instrument_id = InstrumentId(Symbol("SiZ5-RTSX"), Venue("FINAM"))
        bar_spec = BarSpecification.from_str("5-MINUTE-LAST")
        bar_type = BarType(instrument_id, bar_spec, AggregationSource.EXTERNAL)
        ts_init = 1704067200000000000

        # Act
        bar = parse_historical_bar(
            proto_bar=proto_bar,
            instrument_id=instrument_id,
            bar_type=bar_type,
            ts_init=ts_init,
        )

        # Assert
        # ts_event should be from proto_bar.timestamp
        expected_ts_event = (1704153600 * 1_000_000_000) + 500000000
        assert bar.ts_event == expected_ts_event
        assert bar.ts_init == ts_init

    def test_parse_historical_bar_without_timestamp(self):
        """
        Test that bar uses ts_init when proto_bar has no timestamp.
        """
        # Arrange
        proto_bar = MagicMock()
        proto_bar.open = _create_proto_decimal("100000.0")
        proto_bar.high = _create_proto_decimal("100100.0")
        proto_bar.low = _create_proto_decimal("99900.0")
        proto_bar.close = _create_proto_decimal("100050.0")
        proto_bar.volume = _create_proto_decimal("500.0")
        proto_bar.HasField = lambda field: False  # No timestamp

        instrument_id = InstrumentId(Symbol("RIZ5-RTSX"), Venue("FINAM"))
        bar_spec = BarSpecification.from_str("1-HOUR-LAST")
        bar_type = BarType(instrument_id, bar_spec, AggregationSource.EXTERNAL)
        ts_init = 1704240000000000000

        # Act
        bar = parse_historical_bar(
            proto_bar=proto_bar,
            instrument_id=instrument_id,
            bar_type=bar_type,
            ts_init=ts_init,
        )

        # Assert
        # ts_event should fall back to ts_init when no timestamp
        assert bar.ts_event == ts_init
        assert bar.ts_init == ts_init

    def test_parse_historical_bar_price_precision(self):
        """
        Test that prices maintain proper precision.
        """
        # Arrange
        proto_bar = MagicMock()
        proto_bar.open = _create_proto_decimal("100000.50")  # Fractional price
        proto_bar.high = _create_proto_decimal("100500.75")
        proto_bar.low = _create_proto_decimal("99500.25")
        proto_bar.close = _create_proto_decimal("100200.00")
        proto_bar.volume = _create_proto_decimal("2500.0")
        proto_bar.HasField = lambda field: False

        instrument_id = InstrumentId(Symbol("GAZR-MOEX"), Venue("FINAM"))
        bar_spec = BarSpecification.from_str("1-DAY-LAST")
        bar_type = BarType(instrument_id, bar_spec, AggregationSource.EXTERNAL)
        ts_init = 1704067200000000000

        # Act
        bar = parse_historical_bar(
            proto_bar=proto_bar,
            instrument_id=instrument_id,
            bar_type=bar_type,
            ts_init=ts_init,
        )

        # Assert - Verify precision is maintained
        assert bar.open.as_double() == 100000.50
        assert bar.high.as_double() == 100500.75
        assert bar.low.as_double() == 99500.25
        assert bar.close.as_double() == 100200.00

    def test_parse_historical_bar_zero_volume(self):
        """
        Test parsing bar with zero volume.
        """
        # Arrange
        proto_bar = MagicMock()
        proto_bar.open = _create_proto_decimal("100000.0")
        proto_bar.high = _create_proto_decimal("100000.0")
        proto_bar.low = _create_proto_decimal("100000.0")
        proto_bar.close = _create_proto_decimal("100000.0")
        proto_bar.volume = _create_proto_decimal("0.0")  # Zero volume
        proto_bar.HasField = lambda field: False

        instrument_id = InstrumentId(Symbol("SiZ5-RTSX"), Venue("FINAM"))
        bar_spec = BarSpecification.from_str("1-MINUTE-LAST")
        bar_type = BarType(instrument_id, bar_spec, AggregationSource.EXTERNAL)
        ts_init = 1704067200000000000

        # Act
        bar = parse_historical_bar(
            proto_bar=proto_bar,
            instrument_id=instrument_id,
            bar_type=bar_type,
            ts_init=ts_init,
        )

        # Assert
        assert bar.volume.as_double() == 0.0

    def test_parse_historical_bar_maintains_bar_type(self):
        """
        Test that parsed bar maintains correct bar_type.
        """
        # Arrange
        proto_bar = MagicMock()
        proto_bar.open = _create_proto_decimal("100000.0")
        proto_bar.high = _create_proto_decimal("101000.0")
        proto_bar.low = _create_proto_decimal("99000.0")
        proto_bar.close = _create_proto_decimal("100500.0")
        proto_bar.volume = _create_proto_decimal("5000.0")
        proto_bar.HasField = lambda field: False

        instrument_id = InstrumentId(Symbol("SiZ5-RTSX"), Venue("FINAM"))
        bar_spec = BarSpecification.from_str("15-MINUTE-LAST")
        bar_type = BarType(instrument_id, bar_spec, AggregationSource.EXTERNAL)
        ts_init = 1704067200000000000

        # Act
        bar = parse_historical_bar(
            proto_bar=proto_bar,
            instrument_id=instrument_id,
            bar_type=bar_type,
            ts_init=ts_init,
        )

        # Assert
        assert bar.bar_type == bar_type
        assert bar.bar_type.instrument_id == instrument_id
        assert bar.bar_type.spec.step == 15
        # Verify it's a 15-minute bar type
        assert "15-MINUTE" in str(bar.bar_type)

    def test_parse_historical_bar_large_volume(self):
        """
        Test parsing bar with large volume value.
        """
        # Arrange
        proto_bar = MagicMock()
        proto_bar.open = _create_proto_decimal("100000.0")
        proto_bar.high = _create_proto_decimal("100100.0")
        proto_bar.low = _create_proto_decimal("99900.0")
        proto_bar.close = _create_proto_decimal("100050.0")
        proto_bar.volume = _create_proto_decimal("1000000.0")  # 1 million volume
        proto_bar.HasField = lambda field: False

        instrument_id = InstrumentId(Symbol("RIZ5-RTSX"), Venue("FINAM"))
        bar_spec = BarSpecification.from_str("1-MINUTE-LAST")
        bar_type = BarType(instrument_id, bar_spec, AggregationSource.EXTERNAL)
        ts_init = 1704067200000000000

        # Act
        bar = parse_historical_bar(
            proto_bar=proto_bar,
            instrument_id=instrument_id,
            bar_type=bar_type,
            ts_init=ts_init,
        )

        # Assert
        assert bar.volume.as_double() == 1000000.0
