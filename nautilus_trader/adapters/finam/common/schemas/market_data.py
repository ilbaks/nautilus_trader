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

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class Bar(BaseModel):
    """OHLCV bar (candlestick)."""

    timestamp: datetime = Field(..., description="Bar timestamp (open time)")
    open: Decimal = Field(..., description="Open price")
    high: Decimal = Field(..., description="High price")
    low: Decimal = Field(..., description="Low price")
    close: Decimal = Field(..., description="Close price")
    volume: Decimal = Field(..., description="Volume")


class Quote(BaseModel):
    """Best bid/ask quote (Level 1 market data)."""

    symbol: str = Field(..., description="Instrument symbol")
    timestamp: datetime = Field(..., description="Quote timestamp")
    bid: Decimal = Field(..., description="Best bid price")
    bid_size: Decimal = Field(..., description="Best bid size")
    ask: Decimal = Field(..., description="Best ask price")
    ask_size: Decimal = Field(..., description="Best ask size")
    last: Decimal | None = Field(None, description="Last trade price")
    last_size: Decimal | None = Field(None, description="Last trade size")
    volume: Decimal | None = Field(None, description="Total daily volume")


class Trade(BaseModel):
    """Market trade (tape)."""

    trade_id: str = Field(..., description="Unique trade ID")
    timestamp: datetime = Field(..., description="Trade timestamp")
    price: Decimal = Field(..., description="Trade price")
    size: Decimal = Field(..., description="Trade size/quantity")
    side: str | None = Field(None, description="Aggressor side (BUY/SELL)")


class OrderBookLevel(BaseModel):
    """Single level in order book."""

    price: Decimal = Field(..., description="Price level")
    size: Decimal = Field(..., description="Total size at this level")


class OrderBook(BaseModel):
    """Order book snapshot (Level 2 market data)."""

    symbol: str = Field(..., description="Instrument symbol")
    timestamp: datetime = Field(..., description="Snapshot timestamp")
    bids: list[OrderBookLevel] = Field(default_factory=list, description="Bid levels (sorted descending by price)")
    asks: list[OrderBookLevel] = Field(default_factory=list, description="Ask levels (sorted ascending by price)")


class OrderBookDelta(BaseModel):
    """Order book delta/update (for WebSocket streaming)."""

    symbol: str = Field(..., description="Instrument symbol")
    timestamp: datetime = Field(..., description="Update timestamp")
    price: Decimal = Field(..., description="Price level")
    bid_size: Decimal | None = Field(None, description="Bid size at this level (None = no change)")
    ask_size: Decimal | None = Field(None, description="Ask size at this level (None = no change)")
    action: str = Field(..., description="Action: ADD, UPDATE, REMOVE")


# Response wrappers
class BarsResponse(BaseModel):
    """Response from GET /marketdata/bars."""

    symbol: str = Field(..., description="Instrument symbol")
    bars: list[Bar] = Field(default_factory=list, description="List of bars")


class QuoteResponse(BaseModel):
    """Response from GET /marketdata/quote."""

    symbol: str = Field(..., description="Instrument symbol")
    quote: Quote = Field(..., description="Current quote")


class TradesResponse(BaseModel):
    """Response from GET /marketdata/trades."""

    symbol: str = Field(..., description="Instrument symbol")
    trades: list[Trade] = Field(default_factory=list, description="List of trades")


class OrderBookResponse(BaseModel):
    """Response from GET /marketdata/orderbook."""

    symbol: str = Field(..., description="Instrument symbol")
    orderbook: OrderBook = Field(..., description="Order book snapshot")