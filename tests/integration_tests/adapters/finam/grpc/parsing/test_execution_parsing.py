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
Unit tests for Finam gRPC execution parsing functions.
"""

import pytest
from unittest.mock import MagicMock
from decimal import Decimal

from nautilus_trader.adapters.finam.grpc.parsing.execution import (
    _timestamp_to_nanos,
    _decimal_to_str,
    _decimal_to_quantity,
    _decimal_to_price,
    _parse_side,
    _parse_order_status,
    parse_order_state,
    parse_account_trade,
    parse_account_balances_and_margins,
    parse_account_response,
    parse_position,
)
from nautilus_trader.model.identifiers import AccountId, InstrumentId, Symbol, Venue
from nautilus_trader.model.enums import OrderSide, OrderStatus, PositionSide, LiquiditySide


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


def _create_proto_money(units: int, nanos: int, currency_code: str = "RUB"):
    """Create a mock protobuf Money."""
    money = MagicMock()
    money.units = units
    money.nanos = nanos
    money.currency_code = currency_code
    return money


# ================================================================================================
# Helper Functions Tests
# ================================================================================================

class TestTimestampToNanos:
    """Unit tests for _timestamp_to_nanos function."""

    def test_timestamp_to_nanos_normal(self):
        """Test converting normal timestamp."""
        # Arrange
        ts = _create_proto_timestamp(1704067200, 500000000)

        # Act
        result = _timestamp_to_nanos(ts)

        # Assert
        expected = (1704067200 * 1_000_000_000) + 500000000
        assert result == expected

    def test_timestamp_to_nanos_zero_nanos(self):
        """Test timestamp with zero nanoseconds."""
        # Arrange
        ts = _create_proto_timestamp(1704067200, 0)

        # Act
        result = _timestamp_to_nanos(ts)

        # Assert
        assert result == 1704067200 * 1_000_000_000


class TestDecimalToStr:
    """Unit tests for _decimal_to_str function."""

    def test_decimal_to_str_normal(self):
        """Test converting normal decimal."""
        # Arrange
        decimal = _create_proto_decimal("100.50")

        # Act
        result = _decimal_to_str(decimal)

        # Assert
        assert result == "100.50"

    def test_decimal_to_str_none(self):
        """Test converting None returns '0'."""
        # Act
        result = _decimal_to_str(None)

        # Assert
        assert result == "0"

    def test_decimal_to_str_no_value_attr(self):
        """Test decimal without .value attribute."""
        # Arrange
        decimal = MagicMock(spec=[])  # No attributes

        # Act
        result = _decimal_to_str(decimal)

        # Assert
        assert result == "0"


class TestDecimalToQuantity:
    """Unit tests for _decimal_to_quantity function."""

    def test_decimal_to_quantity_normal(self):
        """Test converting normal decimal to quantity."""
        # Arrange
        decimal = _create_proto_decimal("100.5")

        # Act
        quantity = _decimal_to_quantity(decimal)

        # Assert
        assert quantity.as_double() == 100.5

    def test_decimal_to_quantity_zero(self):
        """Test converting zero decimal."""
        # Arrange
        decimal = _create_proto_decimal("0")

        # Act
        quantity = _decimal_to_quantity(decimal)

        # Assert
        assert quantity.as_double() == 0.0


class TestDecimalToPrice:
    """Unit tests for _decimal_to_price function."""

    def test_decimal_to_price_normal(self):
        """Test converting normal decimal to price."""
        # Arrange
        decimal = _create_proto_decimal("100000.50")

        # Act
        price = _decimal_to_price(decimal)

        # Assert
        assert price.as_double() == 100000.50

    def test_decimal_to_price_zero(self):
        """Test converting zero decimal."""
        # Arrange
        decimal = _create_proto_decimal("0")

        # Act
        # Note: _decimal_to_price creates Price.zero(precision) for "0"
        # But Price.zero() doesn't exist, so it returns Price.from_str("0")
        price = _decimal_to_price(decimal, precision=2)

        # Assert
        # Should create a zero price
        assert price.as_double() == 0.0


class TestParseSide:
    """Unit tests for _parse_side function."""

    def test_parse_side_buy(self):
        """Test parsing BUY side."""
        # Arrange
        from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.side_pb2 import Side

        # Act
        result = _parse_side(Side.SIDE_BUY)

        # Assert
        assert result == OrderSide.BUY

    def test_parse_side_sell(self):
        """Test parsing SELL side."""
        # Arrange
        from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.side_pb2 import Side

        # Act
        result = _parse_side(Side.SIDE_SELL)

        # Assert
        assert result == OrderSide.SELL


class TestParseOrderStatus:
    """Unit tests for _parse_order_status function."""

    def test_parse_order_status_new(self):
        """Test parsing NEW status."""
        # Arrange
        from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.orders.orders_service_pb2 import OrderStatus as FinamOrderStatus

        # Act
        result = _parse_order_status(FinamOrderStatus.ORDER_STATUS_NEW)

        # Assert
        assert result == OrderStatus.ACCEPTED

    def test_parse_order_status_filled(self):
        """Test parsing FILLED status."""
        # Arrange
        from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.orders.orders_service_pb2 import OrderStatus as FinamOrderStatus

        # Act
        result = _parse_order_status(FinamOrderStatus.ORDER_STATUS_FILLED)

        # Assert
        assert result == OrderStatus.FILLED

    def test_parse_order_status_canceled(self):
        """Test parsing CANCELED status."""
        # Arrange
        from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.orders.orders_service_pb2 import OrderStatus as FinamOrderStatus

        # Act
        result = _parse_order_status(FinamOrderStatus.ORDER_STATUS_CANCELED)

        # Assert
        assert result == OrderStatus.CANCELED

    def test_parse_order_status_rejected(self):
        """Test parsing REJECTED status."""
        # Arrange
        from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.orders.orders_service_pb2 import OrderStatus as FinamOrderStatus

        # Act
        result = _parse_order_status(FinamOrderStatus.ORDER_STATUS_REJECTED)

        # Assert
        assert result == OrderStatus.REJECTED


# ================================================================================================
# Parsing Functions Tests
# ================================================================================================

class TestParseOrderState:
    """Unit tests for parse_order_state function."""

    def test_parse_order_state_basic(self):
        """Test parsing basic order state."""
        # Arrange
        from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.side_pb2 import Side
        from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.orders.orders_service_pb2 import OrderStatus as FinamOrderStatus

        order_state = MagicMock()
        order_state.order_id = "12345"
        order_state.status = FinamOrderStatus.ORDER_STATUS_NEW
        order_state.HasField = lambda field: field == "transact_at"
        order_state.transact_at = _create_proto_timestamp(1704067200, 0)

        order = MagicMock()
        order.client_order_id = "CLIENT-001"
        order.quantity = _create_proto_decimal("10.0")
        order.side = Side.SIDE_BUY
        order.HasField = lambda field: False
        order_state.order = order

        account_id = AccountId("FINAM-001")
        instrument_id = InstrumentId(Symbol("SiZ5-RTSX"), Venue("FINAM"))
        ts_init = 1704067200000000000

        # Act
        result = parse_order_state(order_state, account_id, instrument_id, ts_init)

        # Assert
        assert result["venue_order_id"].value == "12345"
        assert result["client_order_id"].value == "CLIENT-001"
        assert result["order_status"] == OrderStatus.ACCEPTED
        assert result["quantity"].as_double() == 10.0
        assert result["side"] == OrderSide.BUY
        assert result["limit_price"] is None
        assert result["stop_price"] is None

    def test_parse_order_state_with_limit_price(self):
        """Test parsing order state with limit price."""
        # Arrange
        from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.side_pb2 import Side
        from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.orders.orders_service_pb2 import OrderStatus as FinamOrderStatus

        order_state = MagicMock()
        order_state.order_id = "12345"
        order_state.status = FinamOrderStatus.ORDER_STATUS_NEW
        order_state.HasField = lambda field: False

        order = MagicMock()
        order.client_order_id = "CLIENT-001"
        order.quantity = _create_proto_decimal("10.0")
        order.side = Side.SIDE_BUY
        order.HasField = lambda field: field == "limit_price"
        order.limit_price = _create_proto_decimal("100000.0")
        order_state.order = order

        account_id = AccountId("FINAM-001")
        instrument_id = InstrumentId(Symbol("SiZ5-RTSX"), Venue("FINAM"))
        ts_init = 1704067200000000000

        # Act
        result = parse_order_state(order_state, account_id, instrument_id, ts_init)

        # Assert
        assert result["limit_price"].as_double() == 100000.0
        assert result["stop_price"] is None

    def test_parse_order_state_no_client_order_id(self):
        """Test parsing order state without client order ID."""
        # Arrange
        from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.side_pb2 import Side
        from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.orders.orders_service_pb2 import OrderStatus as FinamOrderStatus

        order_state = MagicMock()
        order_state.order_id = "12345"
        order_state.status = FinamOrderStatus.ORDER_STATUS_NEW
        order_state.HasField = lambda field: False

        order = MagicMock()
        order.client_order_id = ""  # Empty client order ID
        order.quantity = _create_proto_decimal("10.0")
        order.side = Side.SIDE_BUY
        order.HasField = lambda field: False
        order_state.order = order

        account_id = AccountId("FINAM-001")
        instrument_id = InstrumentId(Symbol("SiZ5-RTSX"), Venue("FINAM"))
        ts_init = 1704067200000000000

        # Act
        result = parse_order_state(order_state, account_id, instrument_id, ts_init)

        # Assert
        assert result["client_order_id"] is None


class TestParseAccountTrade:
    """Unit tests for parse_account_trade function."""

    def test_parse_account_trade_basic(self):
        """Test parsing basic account trade."""
        # Arrange
        from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.side_pb2 import Side

        trade = MagicMock()
        trade.trade_id = "TRADE-001"
        trade.order_id = "ORDER-001"
        trade.side = Side.SIDE_BUY
        trade.quantity = _create_proto_decimal("10.0")
        trade.price = _create_proto_decimal("100000.0")
        trade.HasField = lambda field: field == "timestamp"
        trade.timestamp = _create_proto_timestamp(1704067200, 0)

        account_id = AccountId("FINAM-001")
        instrument_id = InstrumentId(Symbol("SiZ5-RTSX"), Venue("FINAM"))
        ts_init = 1704067200000000000

        # Act
        result = parse_account_trade(trade, account_id, instrument_id, ts_init)

        # Assert
        assert result["trade_id"].value == "TRADE-001"
        assert result["venue_order_id"].value == "ORDER-001"
        assert result["side"] == OrderSide.BUY
        assert result["quantity"].as_double() == 10.0
        assert result["price"].as_double() == 100000.0
        assert result["liquidity_side"] == LiquiditySide.TAKER

    def test_parse_account_trade_sell_side(self):
        """Test parsing account trade with SELL side."""
        # Arrange
        from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.side_pb2 import Side

        trade = MagicMock()
        trade.trade_id = "TRADE-002"
        trade.order_id = "ORDER-002"
        trade.side = Side.SIDE_SELL
        trade.quantity = _create_proto_decimal("5.0")
        trade.price = _create_proto_decimal("100500.0")
        trade.HasField = lambda field: False

        account_id = AccountId("FINAM-001")
        instrument_id = InstrumentId(Symbol("SiZ5-RTSX"), Venue("FINAM"))
        ts_init = 1704067200000000000

        # Act
        result = parse_account_trade(trade, account_id, instrument_id, ts_init)

        # Assert
        assert result["side"] == OrderSide.SELL
        assert result["quantity"].as_double() == 5.0
        assert result["price"].as_double() == 100500.0


class TestParsePosition:
    """Unit tests for parse_position function."""

    def test_parse_position_long(self):
        """Test parsing LONG position."""
        # Arrange
        position = MagicMock()
        position.symbol = "SiZ5-RTSX"
        position.quantity = _create_proto_decimal("10.0")  # Positive = LONG
        position.average_price = _create_proto_decimal("100000.0")
        position.current_price = _create_proto_decimal("100500.0")
        position.unrealized_pnl = _create_proto_decimal("5000.0")

        account_id = AccountId("FINAM-001")
        venue = Venue("FINAM")
        ts_init = 1704067200000000000

        # Act
        result = parse_position(position, account_id, venue, ts_init)

        # Assert
        assert result["instrument_id"].symbol.value == "SiZ5-RTSX"
        assert result["side"] == PositionSide.LONG
        assert result["quantity"].as_double() == 10.0
        assert result["avg_price"].as_double() == 100000.0
        assert result["current_price"].as_double() == 100500.0
        assert result["unrealized_pnl"] == Decimal("5000.0")

    def test_parse_position_short(self):
        """Test parsing SHORT position."""
        # Arrange
        position = MagicMock()
        position.symbol = "SiZ5-RTSX"
        position.quantity = _create_proto_decimal("-10.0")  # Negative = SHORT
        position.average_price = _create_proto_decimal("100000.0")
        position.current_price = _create_proto_decimal("99500.0")
        position.unrealized_pnl = _create_proto_decimal("5000.0")

        account_id = AccountId("FINAM-001")
        venue = Venue("FINAM")
        ts_init = 1704067200000000000

        # Act
        result = parse_position(position, account_id, venue, ts_init)

        # Assert
        assert result["side"] == PositionSide.SHORT
        assert result["quantity"].as_double() == 10.0  # Abs value

    def test_parse_position_flat(self):
        """Test parsing FLAT position (zero quantity)."""
        # Arrange
        position = MagicMock()
        position.symbol = "SiZ5-RTSX"
        position.quantity = _create_proto_decimal("0.0")  # Zero = FLAT
        position.average_price = _create_proto_decimal("0.0")
        position.current_price = _create_proto_decimal("100000.0")
        position.unrealized_pnl = _create_proto_decimal("0.0")

        account_id = AccountId("FINAM-001")
        venue = Venue("FINAM")
        ts_init = 1704067200000000000

        # Act
        result = parse_position(position, account_id, venue, ts_init)

        # Assert
        assert result["side"] == PositionSide.FLAT
        assert result["quantity"].as_double() == 0.0


class TestParseAccountBalancesAndMargins:
    """Unit tests for parse_account_balances_and_margins function."""

    def test_parse_account_balances_single_currency(self):
        """Test parsing account with single currency balance."""
        # Arrange
        response = MagicMock()
        money = _create_proto_money(100000, 500000000, "RUB")  # 100000.5 RUB
        response.cash = [money]
        response.HasField = lambda field: False

        # Act
        balances, margins, info = parse_account_balances_and_margins(response)

        # Assert
        assert len(balances) == 1
        assert balances[0].total.as_double() == 100000.5
        assert balances[0].free.as_double() == 100000.5
        assert balances[0].locked.as_double() == 0.0
        assert len(margins) == 0

    def test_parse_account_balances_multiple_currencies(self):
        """Test parsing account with multiple currency balances."""
        # Arrange
        response = MagicMock()
        money_rub = _create_proto_money(100000, 0, "RUB")
        money_usd = _create_proto_money(1000, 0, "USD")
        response.cash = [money_rub, money_usd]
        response.HasField = lambda field: False

        # Act
        balances, margins, info = parse_account_balances_and_margins(response)

        # Assert
        assert len(balances) == 2

    def test_parse_account_with_mc_margin(self):
        """Test parsing account with MC portfolio margin."""
        # Arrange
        response = MagicMock()
        response.cash = []
        response.HasField = lambda field: field == "portfolio_mc"

        portfolio_mc = MagicMock()
        portfolio_mc.available_cash = _create_proto_decimal("50000.0")
        portfolio_mc.initial_margin = _create_proto_decimal("10000.0")
        portfolio_mc.maintenance_margin = _create_proto_decimal("5000.0")
        response.portfolio_mc = portfolio_mc

        # Act
        balances, margins, info = parse_account_balances_and_margins(response)

        # Assert
        assert len(margins) == 1
        assert margins[0].initial.as_double() == 10000.0
        assert margins[0].maintenance.as_double() == 5000.0

    def test_parse_account_with_forts_margin(self):
        """Test parsing account with FORTS portfolio margin."""
        # Arrange
        response = MagicMock()
        response.cash = []

        def has_field(field):
            return field == "portfolio_forts"
        response.HasField = has_field

        portfolio_forts = MagicMock()
        portfolio_forts.available_cash = _create_proto_decimal("50000.0")
        portfolio_forts.money_reserved = _create_proto_decimal("15000.0")
        response.portfolio_forts = portfolio_forts

        # Act
        balances, margins, info = parse_account_balances_and_margins(response)

        # Assert
        assert len(margins) == 1
        assert margins[0].initial.as_double() == 15000.0
        assert margins[0].maintenance.as_double() == 15000.0

    def test_parse_account_info(self):
        """Test parsing account info dict."""
        # Arrange
        response = MagicMock()
        response.cash = []
        response.HasField = lambda field: False
        response.type = 1
        response.status = 2
        response.equity = _create_proto_decimal("200000.0")
        response.unrealized_profit = _create_proto_decimal("5000.0")

        # Act
        balances, margins, info = parse_account_balances_and_margins(response)

        # Assert
        assert info["type"] == 1
        assert info["status"] == 2
        assert info["equity"] == "200000.0"
        assert info["unrealized_profit"] == "5000.0"


class TestParseAccountResponse:
    """Unit tests for parse_account_response function."""

    def test_parse_account_response_basic(self):
        """Test parsing basic account response."""
        # Arrange
        response = MagicMock()
        money = _create_proto_money(100000, 0, "RUB")
        response.cash = [money]
        response.HasField = lambda field: False
        response.type = 1
        response.status = 2
        response.equity = _create_proto_decimal("100000.0")
        response.unrealized_profit = _create_proto_decimal("0.0")

        account_id = AccountId("FINAM-001")
        ts_event = 1704067200000000000
        ts_init = 1704067200000000000

        # Act
        account_state = parse_account_response(response, account_id, ts_event, ts_init)

        # Assert
        assert account_state.account_id == account_id
        assert len(account_state.balances) == 1
        assert account_state.balances[0].total.as_double() == 100000.0
        assert account_state.ts_event == ts_event
        assert account_state.ts_init == ts_init

    def test_parse_account_response_with_margin(self):
        """Test parsing account response with margin data."""
        # Arrange
        response = MagicMock()
        response.cash = []

        def has_field(field):
            return field == "portfolio_mc"
        response.HasField = has_field

        portfolio_mc = MagicMock()
        portfolio_mc.available_cash = _create_proto_decimal("50000.0")
        portfolio_mc.initial_margin = _create_proto_decimal("10000.0")
        portfolio_mc.maintenance_margin = _create_proto_decimal("5000.0")
        response.portfolio_mc = portfolio_mc
        response.type = 1
        response.status = 2
        response.equity = _create_proto_decimal("60000.0")
        response.unrealized_profit = _create_proto_decimal("0.0")

        account_id = AccountId("FINAM-001")
        ts_event = 1704067200000000000
        ts_init = 1704067200000000000

        # Act
        account_state = parse_account_response(response, account_id, ts_event, ts_init)

        # Assert
        assert len(account_state.margins) == 1
        assert account_state.margins[0].initial.as_double() == 10000.0
