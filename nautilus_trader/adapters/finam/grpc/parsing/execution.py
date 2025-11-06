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
Parsing functions for Finam gRPC execution-related Protobuf messages.

Converts Finam gRPC Protobuf messages → Nautilus domain objects for execution (orders, trades, account).
"""

from decimal import Decimal

from google.protobuf.timestamp_pb2 import Timestamp
from nautilus_trader.core.uuid import UUID4
from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.accounts.accounts_service_pb2 import (
    GetAccountResponse,
    Position as FinamPosition,
)
from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.orders.orders_service_pb2 import (
    OrderState as FinamOrderState,
    OrderStatus as FinamOrderStatus,
)
from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.side_pb2 import (
    Side as FinamSide,
)
from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.trade_pb2 import (
    AccountTrade as FinamAccountTrade,
)
from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.model.enums import AccountType
from nautilus_trader.model.enums import LiquiditySide
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.enums import OrderStatus
from nautilus_trader.model.enums import PositionSide
from nautilus_trader.model.identifiers import AccountId
from nautilus_trader.model.identifiers import ClientOrderId
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import Symbol
from nautilus_trader.model.identifiers import TradeId
from nautilus_trader.model.identifiers import VenueOrderId
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.objects import AccountBalance
from nautilus_trader.model.objects import Currency
from nautilus_trader.model.objects import MarginBalance
from nautilus_trader.model.objects import Money
from nautilus_trader.model.objects import Price
from nautilus_trader.model.objects import Quantity
from nautilus_trader.model.events import AccountState
from nautilus_trader.model.events import OrderFilled
from nautilus_trader.model.events import OrderAccepted
from nautilus_trader.model.events import OrderCanceled
from nautilus_trader.model.events import OrderRejected


# =================================================================================================
# Constants and Enums Mapping
# =================================================================================================

FINAM_TO_NAUTILUS_ORDER_STATUS = {
    FinamOrderStatus.ORDER_STATUS_NEW: OrderStatus.ACCEPTED,
    FinamOrderStatus.ORDER_STATUS_PARTIALLY_FILLED: OrderStatus.PARTIALLY_FILLED,
    FinamOrderStatus.ORDER_STATUS_FILLED: OrderStatus.FILLED,
    FinamOrderStatus.ORDER_STATUS_CANCELED: OrderStatus.CANCELED,
    FinamOrderStatus.ORDER_STATUS_REJECTED: OrderStatus.REJECTED,
    FinamOrderStatus.ORDER_STATUS_EXPIRED: OrderStatus.EXPIRED,
    FinamOrderStatus.ORDER_STATUS_PENDING_NEW: OrderStatus.SUBMITTED,
    FinamOrderStatus.ORDER_STATUS_PENDING_CANCEL: OrderStatus.PENDING_CANCEL,
    # Extended statuses - map to closest Nautilus equivalent
    FinamOrderStatus.ORDER_STATUS_DONE_FOR_DAY: OrderStatus.CANCELED,
    FinamOrderStatus.ORDER_STATUS_REPLACED: OrderStatus.ACCEPTED,  # Modified order
    FinamOrderStatus.ORDER_STATUS_SUSPENDED: OrderStatus.PENDING_CANCEL,
    FinamOrderStatus.ORDER_STATUS_FAILED: OrderStatus.REJECTED,
    FinamOrderStatus.ORDER_STATUS_DENIED_BY_BROKER: OrderStatus.REJECTED,
    FinamOrderStatus.ORDER_STATUS_REJECTED_BY_EXCHANGE: OrderStatus.REJECTED,
}

FINAM_SIDE_TO_NAUTILUS = {
    FinamSide.SIDE_BUY: OrderSide.BUY,
    FinamSide.SIDE_SELL: OrderSide.SELL,
}


# =================================================================================================
# Helper Functions
# =================================================================================================

def _timestamp_to_nanos(ts: Timestamp) -> int:
    """Convert Protobuf Timestamp to UNIX nanoseconds."""
    return ts.seconds * 1_000_000_000 + ts.nanos


def _decimal_to_str(decimal: Decimal) -> str:
    """Convert Protobuf Decimal to string representation."""
    if not decimal or not hasattr(decimal, 'value'):
        return "0"
    return decimal.value


def _decimal_to_quantity(decimal: Decimal, precision: int = 8) -> Quantity:
    """Convert Protobuf Decimal to Nautilus Quantity."""
    value_str = _decimal_to_str(decimal)
    return Quantity.from_str(value_str) if value_str != "0" else Quantity.zero()


def _decimal_to_price(decimal: Decimal, precision: int = 8) -> Price:
    """Convert Protobuf Decimal to Nautilus Price."""
    value_str = _decimal_to_str(decimal)
    return Price.from_str(value_str) if value_str != "0" else Price.from_str("0")


def _parse_side(side: FinamSide) -> OrderSide:
    """Parse Finam Side → Nautilus OrderSide."""
    return FINAM_SIDE_TO_NAUTILUS.get(side, OrderSide.BUY)


def _parse_order_status(status: FinamOrderStatus) -> OrderStatus:
    """Parse Finam OrderStatus → Nautilus OrderStatus."""
    return FINAM_TO_NAUTILUS_ORDER_STATUS.get(status, OrderStatus.PENDING_UPDATE)


# =================================================================================================
# Order Parsing
# =================================================================================================

def parse_order_state(
    order_state: FinamOrderState,
    account_id: AccountId,
    instrument_id: InstrumentId,
    ts_init: int,
) -> dict:
    """
    Parse Finam OrderState → dict with order information.

    Parameters
    ----------
    order_state : FinamOrderState
        The Finam gRPC OrderState message
    account_id : AccountId
        The account ID for this order
    instrument_id : InstrumentId
        The instrument ID for this order
    ts_init : int
        Timestamp (UNIX nanoseconds) when the message was initialized

    Returns
    -------
    dict
        Dictionary containing:
        - venue_order_id: VenueOrderId
        - client_order_id: ClientOrderId
        - order_status: OrderStatus
        - quantity: Quantity
        - side: OrderSide
        - limit_price: Price | None
        - stop_price: Price | None
        - ts_event: int (UNIX nanoseconds)
        - ts_accepted: int | None
        - ts_init: int

    """
    order = order_state.order

    venue_order_id = VenueOrderId(order_state.order_id)
    client_order_id = ClientOrderId(order.client_order_id) if order.client_order_id else None
    order_status = _parse_order_status(order_state.status)

    # Parse timestamps
    ts_event = _timestamp_to_nanos(order_state.transact_at) if order_state.HasField('transact_at') else ts_init
    ts_accepted = _timestamp_to_nanos(order_state.accept_at) if order_state.HasField('accept_at') else None

    # Parse order details
    quantity = _decimal_to_quantity(order.quantity)
    side = _parse_side(order.side)
    limit_price = _decimal_to_price(order.limit_price) if order.HasField('limit_price') else None
    stop_price = _decimal_to_price(order.stop_price) if order.HasField('stop_price') else None

    return {
        "venue_order_id": venue_order_id,
        "client_order_id": client_order_id,
        "order_status": order_status,
        "quantity": quantity,
        "side": side,
        "limit_price": limit_price,
        "stop_price": stop_price,
        "ts_event": ts_event,
        "ts_accepted": ts_accepted,
        "ts_init": ts_init,
    }


# =================================================================================================
# Trade Parsing
# =================================================================================================

def parse_account_trade(
    trade: FinamAccountTrade,
    account_id: AccountId,
    instrument_id: InstrumentId,
    ts_init: int,
) -> dict:
    """
    Parse Finam AccountTrade → dict with trade (fill) information.

    Parameters
    ----------
    trade : FinamAccountTrade
        The Finam gRPC AccountTrade message
    account_id : AccountId
        The account ID for this trade
    instrument_id : InstrumentId
        The instrument ID for this trade
    ts_init : int
        Timestamp (UNIX nanoseconds) when the message was initialized

    Returns
    -------
    dict
        Dictionary containing:
        - trade_id: TradeId
        - venue_order_id: VenueOrderId
        - side: OrderSide
        - quantity: Quantity (filled size)
        - price: Price (execution price)
        - ts_event: int (UNIX nanoseconds)
        - liquidity_side: LiquiditySide

    """
    trade_id = TradeId(trade.trade_id)
    venue_order_id = VenueOrderId(trade.order_id)
    side = _parse_side(trade.side)
    quantity = _decimal_to_quantity(trade.quantity)
    price = _decimal_to_price(trade.price)

    ts_event = _timestamp_to_nanos(trade.timestamp) if trade.HasField('timestamp') else ts_init

    # Finam doesn't provide liquidity side info - default to TAKER
    liquidity_side = LiquiditySide.TAKER

    return {
        "trade_id": trade_id,
        "venue_order_id": venue_order_id,
        "side": side,
        "quantity": quantity,
        "price": price,
        "ts_event": ts_event,
        "liquidity_side": liquidity_side,
    }


# =================================================================================================
# Account Parsing
# =================================================================================================

def parse_account_balances_and_margins(
    response: GetAccountResponse,
) -> tuple[list[AccountBalance], list[MarginBalance], dict]:
    """
    Parse Finam GetAccountResponse → balances, margins, and info.

    Parameters
    ----------
    response : GetAccountResponse
        The Finam gRPC GetAccountResponse message

    Returns
    -------
    tuple[list[AccountBalance], list[MarginBalance], dict]
        Tuple containing (balances, margins, info)
    """
    # Parse cash balances (multi-currency)
    balances = []
    for money in response.cash:
        currency = Currency.from_str(money.currency_code)
        total = Decimal(money.units) + (Decimal(money.nanos) / 1_000_000_000)
        free = total
        locked = Decimal(0)

        balance = AccountBalance(
            total=Money(total, currency),
            locked=Money(locked, currency),
            free=Money(free, currency),
        )
        balances.append(balance)

    # Parse margin balance (if available)
    margins = []
    if response.HasField('portfolio_mc'):
        currency = Currency.from_str("RUB")
        available_cash = Decimal(_decimal_to_str(response.portfolio_mc.available_cash))
        initial_margin = Decimal(_decimal_to_str(response.portfolio_mc.initial_margin))
        maintenance_margin = Decimal(_decimal_to_str(response.portfolio_mc.maintenance_margin))

        # Only add margin if values are non-zero
        if initial_margin > 0 or maintenance_margin > 0:
            margin = MarginBalance(
                initial=Money(initial_margin, currency),
                maintenance=Money(maintenance_margin, currency),
                instrument_id=None,
            )
            margins.append(margin)

    if response.HasField('portfolio_forts'):
        currency = Currency.from_str("RUB")
        available_cash = Decimal(_decimal_to_str(response.portfolio_forts.available_cash))
        money_reserved = Decimal(_decimal_to_str(response.portfolio_forts.money_reserved))

        # Only add margin if value is non-zero
        if money_reserved > 0:
            margin = MarginBalance(
                initial=Money(money_reserved, currency),
                maintenance=Money(money_reserved, currency),
                instrument_id=None,
            )
            margins.append(margin)

    # Create info dict
    info = {
        "type": response.type,
        "status": response.status,
        "equity": _decimal_to_str(response.equity),
        "unrealized_profit": _decimal_to_str(response.unrealized_profit),
    }

    return balances, margins, info


def parse_account_response(
    response: GetAccountResponse,
    account_id: AccountId,
    ts_event: int,
    ts_init: int,
) -> AccountState:
    """
    Parse Finam GetAccountResponse → Nautilus AccountState.

    Parameters
    ----------
    response : GetAccountResponse
        The Finam gRPC GetAccountResponse message
    account_id : AccountId
        The account ID
    ts_event : int
        Timestamp (UNIX nanoseconds) when account was updated
    ts_init : int
        Timestamp (UNIX nanoseconds) when the message was initialized

    Returns
    -------
    AccountState
        Nautilus AccountState event with balance and margin information

    """
    # Parse cash balances (multi-currency)
    balances = []
    for money in response.cash:
        currency = Currency.from_str(money.currency_code)
        # Finam provides cash as Money (amount in units)
        # We need total, locked (reserved), free
        # Assuming response.cash shows available cash
        # TODO: Check if Finam provides locked/reserved separately
        total = Decimal(money.units) + (Decimal(money.nanos) / 1_000_000_000)
        free = total  # Assuming cash is free (not reserved)
        locked = Decimal(0)  # TODO: Get from margin_reserved if available

        balance = AccountBalance(
            total=Money(total, currency),
            locked=Money(locked, currency),
            free=Money(free, currency),
        )
        balances.append(balance)

    # Ensure at least one balance exists (required by AccountState)
    if not balances:
        # Create zero RUB balance for accounts with only margin data
        currency = Currency.from_str("RUB")
        balances.append(
            AccountBalance(
                total=Money(0, currency),
                locked=Money(0, currency),
                free=Money(0, currency),
            )
        )

    # Parse margin balance (if available)
    margins = []
    if response.HasField('portfolio_mc'):
        # Moscow Exchange margin model
        currency = Currency.from_str("RUB")  # Default for MC
        available_cash = Decimal(_decimal_to_str(response.portfolio_mc.available_cash))
        initial_margin = Decimal(_decimal_to_str(response.portfolio_mc.initial_margin))
        maintenance_margin = Decimal(_decimal_to_str(response.portfolio_mc.maintenance_margin))

        margin = MarginBalance(
            initial=Money(initial_margin, currency),
            maintenance=Money(maintenance_margin, currency),
            instrument_id=None,  # Portfolio-level margin
        )
        margins.append(margin)

    if response.HasField('portfolio_forts'):
        # Futures margin model
        currency = Currency.from_str("RUB")
        available_cash = Decimal(_decimal_to_str(response.portfolio_forts.available_cash))
        money_reserved = Decimal(_decimal_to_str(response.portfolio_forts.money_reserved))

        # Create margin balance from FORTS data
        margin = MarginBalance(
            initial=Money(money_reserved, currency),
            maintenance=Money(money_reserved, currency),  # Approximation
            instrument_id=None,
        )
        margins.append(margin)

    # Create AccountState
    return AccountState(
        account_id=account_id,
        account_type=AccountType.MARGIN,  # Finam accounts are typically margin
        base_currency=None,  # Multi-currency account
        reported=True,
        balances=balances,
        margins=margins,
        info={
            "type": response.type,
            "status": response.status,
            "equity": _decimal_to_str(response.equity),
            "unrealized_profit": _decimal_to_str(response.unrealized_profit),
        },
        event_id=UUID4(),
        ts_event=ts_event,
        ts_init=ts_init,
    )


def parse_position(
    position: FinamPosition,
    account_id: AccountId,
    venue: Venue,
    ts_init: int,
) -> dict:
    """
    Parse Finam Position → dict with position information.

    Parameters
    ----------
    position : FinamPosition
        The Finam gRPC Position message
    account_id : AccountId
        The account ID
    venue : Venue
        The venue for this position
    ts_init : int
        Timestamp (UNIX nanoseconds) when the message was initialized

    Returns
    -------
    dict
        Dictionary containing position information

    """
    symbol = Symbol(position.symbol)
    instrument_id = InstrumentId(symbol, venue)

    quantity_decimal = Decimal(_decimal_to_str(position.quantity))
    quantity = Quantity.from_str(str(abs(quantity_decimal)))

    # Determine position side from quantity sign
    if quantity_decimal > 0:
        side = PositionSide.LONG
    elif quantity_decimal < 0:
        side = PositionSide.SHORT
    else:
        side = PositionSide.FLAT

    avg_price = _decimal_to_price(position.average_price)
    current_price = _decimal_to_price(position.current_price)
    unrealized_pnl = Decimal(_decimal_to_str(position.unrealized_pnl))

    return {
        "instrument_id": instrument_id,
        "side": side,
        "quantity": quantity,
        "avg_price": avg_price,
        "current_price": current_price,
        "unrealized_pnl": unrealized_pnl,
        "ts_init": ts_init,
    }
