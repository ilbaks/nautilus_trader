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
Parsing utilities for Finam gRPC market data.

Converts Protobuf messages to Nautilus domain models.
"""

from decimal import Decimal

from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.marketdata.marketdata_service_pb2 import (
    SubscribeBarsResponse,
)
from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.marketdata.marketdata_service_pb2 import (
    SubscribeLatestTradesResponse,
)
from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.marketdata.marketdata_service_pb2 import (
    SubscribeOrderBookResponse,
)
from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.marketdata.marketdata_service_pb2 import (
    SubscribeQuoteResponse,
)
from nautilus_trader.core.datetime import secs_to_nanos
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.data import BookOrder
from nautilus_trader.model.data import OrderBookDelta
from nautilus_trader.model.data import OrderBookDeltas
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.enums import AggressorSide
from nautilus_trader.model.enums import BookAction
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import TradeId
from nautilus_trader.model.objects import Price
from nautilus_trader.model.objects import Quantity


def _decimal_to_str(decimal_value) -> str:
    """Convert Protobuf Decimal to string."""
    if decimal_value is None or not decimal_value.value:
        return "0"
    return decimal_value.value


def _timestamp_to_nanos(timestamp) -> int:
    """Convert Protobuf Timestamp to nanoseconds."""
    if timestamp is None:
        return 0
    return secs_to_nanos(timestamp.seconds) + timestamp.nanos


def _parse_side(side: int) -> OrderSide:
    """Parse Finam Side to Nautilus OrderSide."""
    # Finam proto: SIDE_BUY=1, SIDE_SELL=2
    if side == 1:
        return OrderSide.BUY
    elif side == 2:
        return OrderSide.SELL
    else:
        return OrderSide.NO_ORDER_SIDE


def _parse_aggressor_side(side: int) -> AggressorSide:
    """Parse Finam Side to Nautilus AggressorSide."""
    # Finam proto: SIDE_BUY=1, SIDE_SELL=2
    if side == 1:
        return AggressorSide.BUYER
    elif side == 2:
        return AggressorSide.SELLER
    else:
        return AggressorSide.NO_AGGRESSOR


def _parse_book_action(action: int) -> BookAction:
    """Parse Finam OrderBook Action to Nautilus BookAction."""
    # Finam proto: ACTION_REMOVE=1, ACTION_ADD=2, ACTION_UPDATE=3
    if action == 1:
        return BookAction.DELETE
    elif action == 2:
        return BookAction.ADD
    elif action == 3:
        return BookAction.UPDATE
    else:
        return BookAction.CLEAR


def parse_orderbook_response(
    response: SubscribeOrderBookResponse,
    instrument_id: InstrumentId,
    ts_init: int,
) -> OrderBookDeltas:
    """
    Parse Finam SubscribeOrderBookResponse to Nautilus OrderBookDeltas.

    Parameters
    ----------
    response : SubscribeOrderBookResponse
        The Finam gRPC response
    instrument_id : InstrumentId
        The instrument ID
    ts_init : int
        The initialization timestamp (nanoseconds)

    Returns
    -------
    OrderBookDeltas
        The parsed order book deltas

    """
    deltas = []

    for order_book in response.order_book:
        for row in order_book.rows:
            # Determine side and size
            if row.HasField("buy_size"):
                side = OrderSide.BUY
                size_str = _decimal_to_str(row.buy_size)
            elif row.HasField("sell_size"):
                side = OrderSide.SELL
                size_str = _decimal_to_str(row.sell_size)
            else:
                continue  # Skip invalid rows

            # Parse price and size
            price = Price.from_str(_decimal_to_str(row.price))
            size = Quantity.from_str(size_str)

            # Parse action
            action = _parse_book_action(row.action)

            # Get timestamp
            ts_event = _timestamp_to_nanos(row.timestamp) if row.HasField("timestamp") else ts_init

            # Create order
            order = BookOrder(
                side=side,
                price=price,
                size=size,
                order_id=0,  # Finam doesn't provide order IDs
            )

            # Create delta
            delta = OrderBookDelta(
                instrument_id=instrument_id,
                action=action,
                order=order,
                flags=0,
                sequence=0,  # Finam doesn't provide sequence numbers
                ts_event=ts_event,
                ts_init=ts_init,
            )

            deltas.append(delta)

    return OrderBookDeltas(
        instrument_id=instrument_id,
        deltas=deltas,
    )


def parse_trade_response(
    response: SubscribeLatestTradesResponse,
    instrument_id: InstrumentId,
    ts_init: int,
) -> list[TradeTick]:
    """
    Parse Finam SubscribeLatestTradesResponse to Nautilus TradeTicks.

    Parameters
    ----------
    response : SubscribeLatestTradesResponse
        The Finam gRPC response
    instrument_id : InstrumentId
        The instrument ID
    ts_init : int
        The initialization timestamp (nanoseconds)

    Returns
    -------
    list[TradeTick]
        The parsed trade ticks

    """
    ticks = []

    for trade in response.trades:
        price = Price.from_str(_decimal_to_str(trade.price))
        size = Quantity.from_str(_decimal_to_str(trade.size))
        aggressor_side = _parse_aggressor_side(trade.side)
        trade_id = TradeId(trade.trade_id) if trade.trade_id else TradeId("0")
        ts_event = _timestamp_to_nanos(trade.timestamp) if trade.HasField("timestamp") else ts_init

        tick = TradeTick(
            instrument_id=instrument_id,
            price=price,
            size=size,
            aggressor_side=aggressor_side,
            trade_id=trade_id,
            ts_event=ts_event,
            ts_init=ts_init,
        )

        ticks.append(tick)

    return ticks


def parse_bar_response(
    response: SubscribeBarsResponse,
    instrument_id: InstrumentId,
    bar_type: BarType,
    ts_init: int,
) -> list[Bar]:
    """
    Parse Finam SubscribeBarsResponse to Nautilus Bars.

    Parameters
    ----------
    response : SubscribeBarsResponse
        The Finam gRPC response
    instrument_id : InstrumentId
        The instrument ID
    bar_type : BarType
        The bar type
    ts_init : int
        The initialization timestamp (nanoseconds)

    Returns
    -------
    list[Bar]
        The parsed bars

    """
    bars = []

    for bar in response.bars:
        open_price = Price.from_str(_decimal_to_str(bar.open))
        high_price = Price.from_str(_decimal_to_str(bar.high))
        low_price = Price.from_str(_decimal_to_str(bar.low))
        close_price = Price.from_str(_decimal_to_str(bar.close))

        # Нормализуем volume: убираем .0 если значение целое
        # Finam API отправляет объемы в формате "1.0", "2.0" вместо "1", "2"
        # Это приводит к precision=1, но FuturesContract требует precision=0
        volume_str = _decimal_to_str(bar.volume)
        if '.' in volume_str:
            volume_float = float(volume_str)
            volume_int = int(volume_float)
            if volume_float == volume_int:
                volume_str = str(volume_int)  # "1.0" → "1", "2.0" → "2"
        volume = Quantity.from_str(volume_str)

        ts_event = _timestamp_to_nanos(bar.timestamp) if bar.HasField("timestamp") else ts_init

        nautilus_bar = Bar(
            bar_type=bar_type,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
            ts_event=ts_event,
            ts_init=ts_init,
        )

        bars.append(nautilus_bar)

    return bars


def parse_quote_response(
    response: SubscribeQuoteResponse,
    instrument_id: InstrumentId,
    ts_init: int,
) -> list[QuoteTick]:
    """
    Parse Finam SubscribeQuoteResponse to Nautilus QuoteTicks.

    Parameters
    ----------
    response : SubscribeQuoteResponse
        The Finam gRPC response
    instrument_id : InstrumentId
        The instrument ID
    ts_init : int
        The initialization timestamp (nanoseconds)

    Returns
    -------
    list[QuoteTick]
        The parsed quote ticks

    """
    ticks = []

    for quote in response.quote:
        # Check if this quote is for the requested instrument
        # (SubscribeQuote can return quotes for multiple symbols)
        if quote.symbol != instrument_id.symbol.value:
            continue

        # Parse prices as strings to normalize precision
        bid_str = _decimal_to_str(quote.bid)
        ask_str = _decimal_to_str(quote.ask)

        # Determine precision from decimal places
        bid_precision = len(bid_str.split('.')[-1]) if '.' in bid_str else 0
        ask_precision = len(ask_str.split('.')[-1]) if '.' in ask_str else 0
        max_precision = max(bid_precision, ask_precision)

        # Normalize to same precision
        if bid_precision < max_precision:
            bid_str = f"{bid_str:0<{len(bid_str) + (max_precision - bid_precision)}}"
            if '.' not in bid_str:
                bid_str += '.' + '0' * max_precision
        if ask_precision < max_precision:
            ask_str = f"{ask_str:0<{len(ask_str) + (max_precision - ask_precision)}}"
            if '.' not in ask_str:
                ask_str += '.' + '0' * max_precision

        bid_price = Price.from_str(bid_str)
        ask_price = Price.from_str(ask_str)
        bid_size = Quantity.from_str(_decimal_to_str(quote.bid_size))
        ask_size = Quantity.from_str(_decimal_to_str(quote.ask_size))
        ts_event = _timestamp_to_nanos(quote.timestamp) if quote.HasField("timestamp") else ts_init

        tick = QuoteTick(
            instrument_id=instrument_id,
            bid_price=bid_price,
            ask_price=ask_price,
            bid_size=bid_size,
            ask_size=ask_size,
            ts_event=ts_event,
            ts_init=ts_init,
        )

        ticks.append(tick)

    return ticks
