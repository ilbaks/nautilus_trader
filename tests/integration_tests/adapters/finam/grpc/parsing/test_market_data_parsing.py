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
Unit tests for Finam gRPC market data parsing functions.
"""

import pytest
from unittest.mock import MagicMock

from nautilus_trader.adapters.finam.grpc.parsing.market_data import (
    _decimal_to_str,
    _timestamp_to_nanos,
    _parse_side,
    _parse_aggressor_side,
    _parse_book_action,
    parse_orderbook_response,
    parse_trade_response,
    parse_bar_response,
    parse_quote_response,
)
from nautilus_trader.model.data import BarType, BarSpecification
from nautilus_trader.model.enums import AggregationSource, OrderSide, AggressorSide, BookAction
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue


def _create_proto_decimal(value_str: str):
    """Create a mock protobuf Decimal with .value attribute."""
    decimal = MagicMock()
    decimal.value = value_str
    return decimal


def _create_proto_timestamp(seconds: int, nanos: int = 0):
    """Create a mock protobuf Timestamp."""
    timestamp = MagicMock()
    timestamp.seconds = seconds
    timestamp.nanos = nanos
    return timestamp


# ================================================================================================
# Utility Functions Tests
# ================================================================================================

class TestDecimalToStr:
    """Unit tests for _decimal_to_str function."""

    def test_decimal_to_str_normal_value(self):
        """Test converting normal decimal value."""
        # Arrange
        decimal = _create_proto_decimal("100.50")

        # Act
        result = _decimal_to_str(decimal)

        # Assert
        assert result == "100.50"

    def test_decimal_to_str_zero(self):
        """Test converting zero."""
        # Arrange
        decimal = _create_proto_decimal("0")

        # Act
        result = _decimal_to_str(decimal)

        # Assert
        assert result == "0"

    def test_decimal_to_str_none(self):
        """Test converting None returns '0'."""
        # Act
        result = _decimal_to_str(None)

        # Assert
        assert result == "0"

    def test_decimal_to_str_empty_value(self):
        """Test converting decimal with empty value."""
        # Arrange
        decimal = _create_proto_decimal("")

        # Act
        result = _decimal_to_str(decimal)

        # Assert
        assert result == "0"

    def test_decimal_to_str_large_number(self):
        """Test converting large number."""
        # Arrange
        decimal = _create_proto_decimal("1000000.123456")

        # Act
        result = _decimal_to_str(decimal)

        # Assert
        assert result == "1000000.123456"


class TestTimestampToNanos:
    """Unit tests for _timestamp_to_nanos function."""

    def test_timestamp_to_nanos_normal(self):
        """Test converting normal timestamp."""
        # Arrange
        timestamp = _create_proto_timestamp(seconds=1704067200, nanos=500000000)

        # Act
        result = _timestamp_to_nanos(timestamp)

        # Assert
        expected = (1704067200 * 1_000_000_000) + 500000000
        assert result == expected

    def test_timestamp_to_nanos_zero_nanos(self):
        """Test timestamp with zero nanoseconds."""
        # Arrange
        timestamp = _create_proto_timestamp(seconds=1704067200, nanos=0)

        # Act
        result = _timestamp_to_nanos(timestamp)

        # Assert
        expected = 1704067200 * 1_000_000_000
        assert result == expected

    def test_timestamp_to_nanos_none(self):
        """Test None timestamp returns 0."""
        # Act
        result = _timestamp_to_nanos(None)

        # Assert
        assert result == 0


class TestParseSide:
    """Unit tests for _parse_side function."""

    def test_parse_side_buy(self):
        """Test parsing BUY side."""
        # Act
        result = _parse_side(1)

        # Assert
        assert result == OrderSide.BUY

    def test_parse_side_sell(self):
        """Test parsing SELL side."""
        # Act
        result = _parse_side(2)

        # Assert
        assert result == OrderSide.SELL

    def test_parse_side_unknown(self):
        """Test parsing unknown side."""
        # Act
        result = _parse_side(0)

        # Assert
        assert result == OrderSide.NO_ORDER_SIDE

    def test_parse_side_invalid(self):
        """Test parsing invalid side number."""
        # Act
        result = _parse_side(999)

        # Assert
        assert result == OrderSide.NO_ORDER_SIDE


class TestParseAggressorSide:
    """Unit tests for _parse_aggressor_side function."""

    def test_parse_aggressor_side_buyer(self):
        """Test parsing BUYER aggressor side."""
        # Act
        result = _parse_aggressor_side(1)

        # Assert
        assert result == AggressorSide.BUYER

    def test_parse_aggressor_side_seller(self):
        """Test parsing SELLER aggressor side."""
        # Act
        result = _parse_aggressor_side(2)

        # Assert
        assert result == AggressorSide.SELLER

    def test_parse_aggressor_side_unknown(self):
        """Test parsing unknown aggressor side."""
        # Act
        result = _parse_aggressor_side(0)

        # Assert
        assert result == AggressorSide.NO_AGGRESSOR

    def test_parse_aggressor_side_invalid(self):
        """Test parsing invalid aggressor side number."""
        # Act
        result = _parse_aggressor_side(999)

        # Assert
        assert result == AggressorSide.NO_AGGRESSOR


class TestParseBookAction:
    """Unit tests for _parse_book_action function."""

    def test_parse_book_action_remove(self):
        """Test parsing REMOVE action."""
        # Act
        result = _parse_book_action(1)

        # Assert
        assert result == BookAction.DELETE

    def test_parse_book_action_add(self):
        """Test parsing ADD action."""
        # Act
        result = _parse_book_action(2)

        # Assert
        assert result == BookAction.ADD

    def test_parse_book_action_update(self):
        """Test parsing UPDATE action."""
        # Act
        result = _parse_book_action(3)

        # Assert
        assert result == BookAction.UPDATE

    def test_parse_book_action_unknown(self):
        """Test parsing unknown action."""
        # Act
        result = _parse_book_action(0)

        # Assert
        assert result == BookAction.CLEAR

    def test_parse_book_action_invalid(self):
        """Test parsing invalid action number."""
        # Act
        result = _parse_book_action(999)

        # Assert
        assert result == BookAction.CLEAR


# ================================================================================================
# Parse Response Functions Tests
# ================================================================================================

class TestParseBarResponse:
    """Unit tests for parse_bar_response function."""

    def test_parse_bar_response_single_bar(self):
        """Test parsing response with single bar."""
        # Arrange
        response = MagicMock()
        bar = MagicMock()
        bar.open = _create_proto_decimal("100000.0")
        bar.high = _create_proto_decimal("101000.0")
        bar.low = _create_proto_decimal("99000.0")
        bar.close = _create_proto_decimal("100500.0")
        bar.volume = _create_proto_decimal("5000.0")
        bar.HasField = lambda field: field == "timestamp"
        bar.timestamp = _create_proto_timestamp(1704067200, 0)
        response.bars = [bar]

        instrument_id = InstrumentId(Symbol("SiZ5-RTSX"), Venue("FINAM"))
        bar_spec = BarSpecification.from_str("1-MINUTE-LAST")
        bar_type = BarType(instrument_id, bar_spec, AggregationSource.EXTERNAL)
        ts_init = 1704067200000000000

        # Act
        bars = parse_bar_response(response, instrument_id, bar_type, ts_init)

        # Assert
        assert len(bars) == 1
        assert bars[0].open.as_double() == 100000.0
        assert bars[0].high.as_double() == 101000.0
        assert bars[0].low.as_double() == 99000.0
        assert bars[0].close.as_double() == 100500.0
        assert bars[0].volume.as_double() == 5000.0

    def test_parse_bar_response_multiple_bars(self):
        """Test parsing response with multiple bars."""
        # Arrange
        response = MagicMock()

        bar1 = MagicMock()
        bar1.open = _create_proto_decimal("100000.0")
        bar1.high = _create_proto_decimal("100100.0")
        bar1.low = _create_proto_decimal("99900.0")
        bar1.close = _create_proto_decimal("100050.0")
        bar1.volume = _create_proto_decimal("1000.0")
        bar1.HasField = lambda field: False

        bar2 = MagicMock()
        bar2.open = _create_proto_decimal("100050.0")
        bar2.high = _create_proto_decimal("100200.0")
        bar2.low = _create_proto_decimal("100000.0")
        bar2.close = _create_proto_decimal("100150.0")
        bar2.volume = _create_proto_decimal("1500.0")
        bar2.HasField = lambda field: False

        response.bars = [bar1, bar2]

        instrument_id = InstrumentId(Symbol("SiZ5-RTSX"), Venue("FINAM"))
        bar_spec = BarSpecification.from_str("5-MINUTE-LAST")
        bar_type = BarType(instrument_id, bar_spec, AggregationSource.EXTERNAL)
        ts_init = 1704067200000000000

        # Act
        bars = parse_bar_response(response, instrument_id, bar_type, ts_init)

        # Assert
        assert len(bars) == 2
        assert bars[0].close.as_double() == 100050.0
        assert bars[1].close.as_double() == 100150.0

    def test_parse_bar_response_normalizes_integer_volume(self):
        """Test that volume '1000.0' is normalized to '1000'."""
        # Arrange
        response = MagicMock()
        bar = MagicMock()
        bar.open = _create_proto_decimal("100000.0")
        bar.high = _create_proto_decimal("100000.0")
        bar.low = _create_proto_decimal("100000.0")
        bar.close = _create_proto_decimal("100000.0")
        bar.volume = _create_proto_decimal("1000.0")  # Should be normalized
        bar.HasField = lambda field: False
        response.bars = [bar]

        instrument_id = InstrumentId(Symbol("SiZ5-RTSX"), Venue("FINAM"))
        bar_spec = BarSpecification.from_str("1-MINUTE-LAST")
        bar_type = BarType(instrument_id, bar_spec, AggregationSource.EXTERNAL)
        ts_init = 1704067200000000000

        # Act
        bars = parse_bar_response(response, instrument_id, bar_type, ts_init)

        # Assert
        assert bars[0].volume.as_double() == 1000.0

    def test_parse_bar_response_empty(self):
        """Test parsing empty response."""
        # Arrange
        response = MagicMock()
        response.bars = []

        instrument_id = InstrumentId(Symbol("SiZ5-RTSX"), Venue("FINAM"))
        bar_spec = BarSpecification.from_str("1-MINUTE-LAST")
        bar_type = BarType(instrument_id, bar_spec, AggregationSource.EXTERNAL)
        ts_init = 1704067200000000000

        # Act
        bars = parse_bar_response(response, instrument_id, bar_type, ts_init)

        # Assert
        assert len(bars) == 0


class TestParseTradeResponse:
    """Unit tests for parse_trade_response function."""

    def test_parse_trade_response_single_trade(self):
        """Test parsing response with single trade."""
        # Arrange
        response = MagicMock()
        trade = MagicMock()
        trade.price = _create_proto_decimal("100000.0")
        trade.size = _create_proto_decimal("10.0")
        trade.side = 1  # BUY
        trade.trade_id = "12345"
        trade.HasField = lambda field: field == "timestamp"
        trade.timestamp = _create_proto_timestamp(1704067200, 0)
        response.trades = [trade]

        instrument_id = InstrumentId(Symbol("SiZ5-RTSX"), Venue("FINAM"))
        ts_init = 1704067200000000000

        # Act
        ticks = parse_trade_response(response, instrument_id, ts_init)

        # Assert
        assert len(ticks) == 1
        assert ticks[0].price.as_double() == 100000.0
        assert ticks[0].size.as_double() == 10.0
        assert ticks[0].aggressor_side == AggressorSide.BUYER
        assert ticks[0].trade_id.value == "12345"

    def test_parse_trade_response_multiple_trades(self):
        """Test parsing response with multiple trades."""
        # Arrange
        response = MagicMock()

        trade1 = MagicMock()
        trade1.price = _create_proto_decimal("100000.0")
        trade1.size = _create_proto_decimal("10.0")
        trade1.side = 1  # BUYER
        trade1.trade_id = "12345"
        trade1.HasField = lambda field: False

        trade2 = MagicMock()
        trade2.price = _create_proto_decimal("100050.0")
        trade2.size = _create_proto_decimal("5.0")
        trade2.side = 2  # SELLER
        trade2.trade_id = "12346"
        trade2.HasField = lambda field: False

        response.trades = [trade1, trade2]

        instrument_id = InstrumentId(Symbol("SiZ5-RTSX"), Venue("FINAM"))
        ts_init = 1704067200000000000

        # Act
        ticks = parse_trade_response(response, instrument_id, ts_init)

        # Assert
        assert len(ticks) == 2
        assert ticks[0].aggressor_side == AggressorSide.BUYER
        assert ticks[1].aggressor_side == AggressorSide.SELLER

    def test_parse_trade_response_no_trade_id(self):
        """Test parsing trade with missing trade_id."""
        # Arrange
        response = MagicMock()
        trade = MagicMock()
        trade.price = _create_proto_decimal("100000.0")
        trade.size = _create_proto_decimal("10.0")
        trade.side = 1
        trade.trade_id = ""  # Empty trade ID
        trade.HasField = lambda field: False
        response.trades = [trade]

        instrument_id = InstrumentId(Symbol("SiZ5-RTSX"), Venue("FINAM"))
        ts_init = 1704067200000000000

        # Act
        ticks = parse_trade_response(response, instrument_id, ts_init)

        # Assert
        assert len(ticks) == 1
        assert ticks[0].trade_id.value == "0"

    def test_parse_trade_response_empty(self):
        """Test parsing empty trade response."""
        # Arrange
        response = MagicMock()
        response.trades = []

        instrument_id = InstrumentId(Symbol("SiZ5-RTSX"), Venue("FINAM"))
        ts_init = 1704067200000000000

        # Act
        ticks = parse_trade_response(response, instrument_id, ts_init)

        # Assert
        assert len(ticks) == 0


class TestParseQuoteResponse:
    """Unit tests for parse_quote_response function."""

    def test_parse_quote_response_single_quote(self):
        """Test parsing response with single quote."""
        # Arrange
        response = MagicMock()
        quote = MagicMock()
        quote.symbol = "SiZ5-RTSX"
        quote.bid = _create_proto_decimal("99950.0")
        quote.ask = _create_proto_decimal("100050.0")
        quote.bid_size = _create_proto_decimal("100.0")
        quote.ask_size = _create_proto_decimal("150.0")
        quote.HasField = lambda field: field == "timestamp"
        quote.timestamp = _create_proto_timestamp(1704067200, 0)
        response.quote = [quote]

        instrument_id = InstrumentId(Symbol("SiZ5-RTSX"), Venue("FINAM"))
        ts_init = 1704067200000000000

        # Act
        ticks = parse_quote_response(response, instrument_id, ts_init)

        # Assert
        assert len(ticks) == 1
        assert ticks[0].bid_price.as_double() == 99950.0
        assert ticks[0].ask_price.as_double() == 100050.0
        assert ticks[0].bid_size.as_double() == 100.0
        assert ticks[0].ask_size.as_double() == 150.0

    def test_parse_quote_response_filters_by_symbol(self):
        """Test that quotes are filtered by instrument symbol."""
        # Arrange
        response = MagicMock()

        quote1 = MagicMock()
        quote1.symbol = "SiZ5-RTSX"  # Matches
        quote1.bid = _create_proto_decimal("99950.0")
        quote1.ask = _create_proto_decimal("100050.0")
        quote1.bid_size = _create_proto_decimal("100.0")
        quote1.ask_size = _create_proto_decimal("150.0")
        quote1.HasField = lambda field: False

        quote2 = MagicMock()
        quote2.symbol = "RIZ5-RTSX"  # Different symbol - should be filtered
        quote2.bid = _create_proto_decimal("120000.0")
        quote2.ask = _create_proto_decimal("120100.0")
        quote2.bid_size = _create_proto_decimal("50.0")
        quote2.ask_size = _create_proto_decimal("75.0")
        quote2.HasField = lambda field: False

        response.quote = [quote1, quote2]

        instrument_id = InstrumentId(Symbol("SiZ5-RTSX"), Venue("FINAM"))
        ts_init = 1704067200000000000

        # Act
        ticks = parse_quote_response(response, instrument_id, ts_init)

        # Assert
        assert len(ticks) == 1  # Only SiZ5-RTSX should be included
        assert ticks[0].bid_price.as_double() == 99950.0

    def test_parse_quote_response_empty(self):
        """Test parsing empty quote response."""
        # Arrange
        response = MagicMock()
        response.quote = []

        instrument_id = InstrumentId(Symbol("SiZ5-RTSX"), Venue("FINAM"))
        ts_init = 1704067200000000000

        # Act
        ticks = parse_quote_response(response, instrument_id, ts_init)

        # Assert
        assert len(ticks) == 0


class TestParseOrderBookResponse:
    """Unit tests for parse_orderbook_response function."""

    def test_parse_orderbook_response_buy_order(self):
        """Test parsing orderbook with BUY order."""
        # Arrange
        response = MagicMock()
        order_book = MagicMock()
        row = MagicMock()
        row.price = _create_proto_decimal("100000.0")
        row.HasField = lambda field: field == "buy_size" or field == "timestamp"
        row.buy_size = _create_proto_decimal("100.0")
        row.action = 2  # ADD
        row.timestamp = _create_proto_timestamp(1704067200, 0)
        order_book.rows = [row]
        response.order_book = [order_book]

        instrument_id = InstrumentId(Symbol("SiZ5-RTSX"), Venue("FINAM"))
        ts_init = 1704067200000000000

        # Act
        deltas = parse_orderbook_response(response, instrument_id, ts_init)

        # Assert
        assert len(deltas.deltas) == 1
        assert deltas.deltas[0].order.side == OrderSide.BUY
        assert deltas.deltas[0].order.price.as_double() == 100000.0
        assert deltas.deltas[0].order.size.as_double() == 100.0
        assert deltas.deltas[0].action == BookAction.ADD

    def test_parse_orderbook_response_sell_order(self):
        """Test parsing orderbook with SELL order."""
        # Arrange
        response = MagicMock()
        order_book = MagicMock()
        row = MagicMock()
        row.price = _create_proto_decimal("100100.0")
        row.HasField = lambda field: field == "sell_size" or field == "timestamp"
        row.sell_size = _create_proto_decimal("50.0")
        row.action = 2  # ADD
        row.timestamp = _create_proto_timestamp(1704067200, 0)
        order_book.rows = [row]
        response.order_book = [order_book]

        instrument_id = InstrumentId(Symbol("SiZ5-RTSX"), Venue("FINAM"))
        ts_init = 1704067200000000000

        # Act
        deltas = parse_orderbook_response(response, instrument_id, ts_init)

        # Assert
        assert len(deltas.deltas) == 1
        assert deltas.deltas[0].order.side == OrderSide.SELL
        assert deltas.deltas[0].order.price.as_double() == 100100.0
        assert deltas.deltas[0].order.size.as_double() == 50.0

    def test_parse_orderbook_response_multiple_levels(self):
        """Test parsing orderbook with multiple levels."""
        # Arrange
        response = MagicMock()
        order_book = MagicMock()

        row1 = MagicMock()
        row1.price = _create_proto_decimal("100000.0")
        row1.HasField = lambda field: field == "buy_size"
        row1.buy_size = _create_proto_decimal("100.0")
        row1.action = 2  # ADD

        row2 = MagicMock()
        row2.price = _create_proto_decimal("100100.0")
        row2.HasField = lambda field: field == "sell_size"
        row2.sell_size = _create_proto_decimal("50.0")
        row2.action = 2  # ADD

        order_book.rows = [row1, row2]
        response.order_book = [order_book]

        instrument_id = InstrumentId(Symbol("SiZ5-RTSX"), Venue("FINAM"))
        ts_init = 1704067200000000000

        # Act
        deltas = parse_orderbook_response(response, instrument_id, ts_init)

        # Assert
        assert len(deltas.deltas) == 2
        assert deltas.deltas[0].order.side == OrderSide.BUY
        assert deltas.deltas[1].order.side == OrderSide.SELL

    def test_parse_orderbook_response_delete_action(self):
        """Test parsing orderbook with DELETE action."""
        # Arrange
        response = MagicMock()
        order_book = MagicMock()
        row = MagicMock()
        row.price = _create_proto_decimal("100000.0")
        row.HasField = lambda field: field == "buy_size"
        row.buy_size = _create_proto_decimal("0.0")
        row.action = 1  # REMOVE
        order_book.rows = [row]
        response.order_book = [order_book]

        instrument_id = InstrumentId(Symbol("SiZ5-RTSX"), Venue("FINAM"))
        ts_init = 1704067200000000000

        # Act
        deltas = parse_orderbook_response(response, instrument_id, ts_init)

        # Assert
        assert len(deltas.deltas) == 1
        assert deltas.deltas[0].action == BookAction.DELETE

    def test_parse_orderbook_response_empty(self):
        """Test that empty orderbook response raises ValueError."""
        # Arrange
        response = MagicMock()
        response.order_book = []

        instrument_id = InstrumentId(Symbol("SiZ5-RTSX"), Venue("FINAM"))
        ts_init = 1704067200000000000

        # Act, Assert
        # OrderBookDeltas requires non-empty deltas list
        with pytest.raises(ValueError, match="'deltas' collection was empty"):
            parse_orderbook_response(response, instrument_id, ts_init)
