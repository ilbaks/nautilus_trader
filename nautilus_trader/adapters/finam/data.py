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
Provides a data client for the Finam exchange using gRPC API.
"""

import asyncio
from typing import Any

from nautilus_trader.adapters.finam.grpc.client.client import FinamGrpcClient
from nautilus_trader.adapters.finam.grpc.common.enums import TimeFrame
from nautilus_trader.adapters.finam.grpc.parsing.market_data import (
    parse_bar_response,
    parse_orderbook_response,
    parse_quote_response,
    parse_trade_response,
)
from nautilus_trader.adapters.finam.grpc.streams.bars import BarsStreamManager
from nautilus_trader.adapters.finam.grpc.streams.orderbook import OrderBookStreamManager
from nautilus_trader.adapters.finam.grpc.streams.quotes import QuoteStreamManager
from nautilus_trader.adapters.finam.grpc.streams.trades import TradesStreamManager
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import LiveClock
from nautilus_trader.common.component import MessageBus
from nautilus_trader.common.enums import LogColor
from nautilus_trader.common.providers import InstrumentProvider
from nautilus_trader.model.data import BarSpecification
from nautilus_trader.model.enums import BarAggregation
from nautilus_trader.data.messages import SubscribeBars
from nautilus_trader.data.messages import SubscribeOrderBook
from nautilus_trader.data.messages import SubscribeQuoteTicks
from nautilus_trader.data.messages import SubscribeTradeTicks
from nautilus_trader.data.messages import UnsubscribeBars
from nautilus_trader.data.messages import UnsubscribeOrderBook
from nautilus_trader.data.messages import UnsubscribeQuoteTicks
from nautilus_trader.data.messages import UnsubscribeTradeTicks
from nautilus_trader.live.data_client import LiveMarketDataClient
from nautilus_trader.model.identifiers import ClientId
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import Venue


class FinamDataClient(LiveMarketDataClient):
    """
    Provides a data client for the Finam exchange using gRPC API.

    This client provides real-time market data through gRPC streams:
    - Order book deltas (incremental updates)
    - Trade ticks
    - Quote ticks (BBO - Best Bid/Offer)
    - Bars (OHLCV candles)

    Parameters
    ----------
    loop : asyncio.AbstractEventLoop
        The event loop for the client.
    client : FinamGrpcClient
        The Finam gRPC client for API communication.
    msgbus : MessageBus
        The message bus for the client.
    cache : Cache
        The cache for the client.
    clock : LiveClock
        The clock for the client.
    instrument_provider : InstrumentProvider
        The instrument provider.
    venue : Venue
        The venue for the client.
    name : str, optional
        The custom client ID.

    """

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        client: FinamGrpcClient,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
        instrument_provider: InstrumentProvider,
        venue: Venue,
        name: str | None = None,
    ) -> None:
        super().__init__(
            loop=loop,
            client_id=ClientId(name or venue.value),
            venue=venue,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            instrument_provider=instrument_provider,
        )

        # Finam gRPC client
        self._client = client

        # Create Stream Managers
        self._orderbook_stream = OrderBookStreamManager(
            client=self._client,
            logger=self._log,
        )
        self._trades_stream = TradesStreamManager(
            client=self._client,
            logger=self._log,
        )
        self._quotes_stream = QuoteStreamManager(
            client=self._client,
            logger=self._log,
        )
        self._bars_stream = BarsStreamManager(
            client=self._client,
            logger=self._log,
        )

        self._log.info("FinamDataClient initialized", LogColor.BLUE)

    # -- CONNECTION LIFECYCLE ---------------------------------------------------------------------

    async def _connect(self) -> None:
        """Connect to Finam gRPC API and start stream managers."""
        # Initialize instrument provider
        await self._instrument_provider.initialize()
        self._send_all_instruments_to_data_engine()

        # Start stream managers
        await self._orderbook_stream.start()
        await self._trades_stream.start()
        await self._quotes_stream.start()
        await self._bars_stream.start()

        self._log.info("FinamDataClient connected", LogColor.GREEN)

    async def _disconnect(self) -> None:
        """Disconnect from Finam gRPC API and stop stream managers."""
        # Stop all stream managers
        await self._orderbook_stream.stop()
        await self._trades_stream.stop()
        await self._quotes_stream.stop()
        await self._bars_stream.stop()

        # Disconnect gRPC client
        await self._client.disconnect()

        self._log.info("FinamDataClient disconnected", LogColor.YELLOW)

    def _send_all_instruments_to_data_engine(self) -> None:
        """Send all instruments from provider to data engine."""
        for instrument in self._instrument_provider.get_all().values():
            self._handle_data(instrument)

        # Cache currencies
        for currency in self._instrument_provider.currencies().values():
            self._cache.add_currency(currency)

        self._log.info(
            f"Sent {len(self._instrument_provider.get_all())} instruments to data engine",
            LogColor.BLUE,
        )

    # -- SUBSCRIPTIONS: ORDER BOOK ----------------------------------------------------------------

    async def _subscribe_order_book_deltas(self, command: SubscribeOrderBook) -> None:
        """
        Subscribe to order book deltas for an instrument.

        Parameters
        ----------
        command : SubscribeOrderBook
            The subscription command.

        """
        instrument_id: InstrumentId = command.instrument_id
        symbol: str = self._get_finam_symbol(instrument_id)

        def callback(response: Any) -> None:
            """Handle order book updates from gRPC stream."""
            try:
                ts_init = self._clock.timestamp_ns()
                deltas = parse_orderbook_response(response, instrument_id, ts_init)
                self._handle_data(deltas)
            except Exception as e:
                self._log.error(
                    f"Error parsing order book for {symbol}: {e}",
                    exc_info=True,
                )

        await self._orderbook_stream.subscribe_order_book(symbol, callback)
        self._log.info(f"Subscribed to order book deltas: {symbol}", LogColor.BLUE)

    async def _subscribe_order_book_snapshots(self, command: SubscribeOrderBook) -> None:
        """
        Subscribe to order book snapshots.

        Note: Finam gRPC API provides incremental deltas only.
        Snapshots can be requested via HTTP REST API if needed.

        Parameters
        ----------
        command : SubscribeOrderBook
            The subscription command.

        """
        self._log.warning(
            f"Order book snapshots not supported for {command.instrument_id}: "
            "Finam gRPC provides deltas only. Use deltas subscription instead.",
        )

    async def _unsubscribe_order_book_deltas(self, command: UnsubscribeOrderBook) -> None:
        """
        Unsubscribe from order book deltas.

        Parameters
        ----------
        command : UnsubscribeOrderBook
            The unsubscription command.

        """
        symbol: str = self._get_finam_symbol(command.instrument_id)
        await self._orderbook_stream.unsubscribe_order_book(symbol)
        self._log.info(f"Unsubscribed from order book deltas: {symbol}")

    async def _unsubscribe_order_book_snapshots(self, command: UnsubscribeOrderBook) -> None:
        """Unsubscribe from order book snapshots (no-op)."""
        pass  # Snapshots not supported

    # -- SUBSCRIPTIONS: TRADES --------------------------------------------------------------------

    async def _subscribe_trade_ticks(self, command: SubscribeTradeTicks) -> None:
        """
        Subscribe to trade ticks for an instrument.

        Parameters
        ----------
        command : SubscribeTradeTicks
            The subscription command.

        """
        instrument_id: InstrumentId = command.instrument_id
        symbol: str = self._get_finam_symbol(instrument_id)

        def callback(response: Any) -> None:
            """Handle trade updates from gRPC stream."""
            try:
                ts_init = self._clock.timestamp_ns()
                ticks = parse_trade_response(response, instrument_id, ts_init)
                for tick in ticks:
                    self._handle_data(tick)
            except Exception as e:
                self._log.error(
                    f"Error parsing trade for {symbol}: {e}",
                    exc_info=True,
                )

        await self._trades_stream.subscribe_trades(symbol, callback)
        self._log.info(f"Subscribed to trade ticks: {symbol}", LogColor.BLUE)

    async def _unsubscribe_trade_ticks(self, command: UnsubscribeTradeTicks) -> None:
        """
        Unsubscribe from trade ticks.

        Parameters
        ----------
        command : UnsubscribeTradeTicks
            The unsubscription command.

        """
        symbol: str = self._get_finam_symbol(command.instrument_id)
        await self._trades_stream.unsubscribe_trades(symbol)
        self._log.info(f"Unsubscribed from trade ticks: {symbol}")

    # -- SUBSCRIPTIONS: QUOTES --------------------------------------------------------------------

    async def _subscribe_quote_ticks(self, command: SubscribeQuoteTicks) -> None:
        """
        Subscribe to quote ticks (BBO) for an instrument.

        Parameters
        ----------
        command : SubscribeQuoteTicks
            The subscription command.

        """
        instrument_id: InstrumentId = command.instrument_id
        symbol: str = self._get_finam_symbol(instrument_id)

        def callback(response: Any) -> None:
            """Handle quote updates from gRPC stream."""
            try:
                ts_init = self._clock.timestamp_ns()
                ticks = parse_quote_response(response, instrument_id, ts_init)
                for tick in ticks:
                    self._handle_data(tick)
            except Exception as e:
                self._log.error(
                    f"Error parsing quote for {symbol}: {e}",
                    exc_info=True,
                )

        # Note: QuoteStreamManager accepts list of symbols
        await self._quotes_stream.subscribe_quotes([symbol], callback)
        self._log.info(f"Subscribed to quote ticks: {symbol}", LogColor.BLUE)

    async def _unsubscribe_quote_ticks(self, command: UnsubscribeQuoteTicks) -> None:
        """
        Unsubscribe from quote ticks.

        Parameters
        ----------
        command : UnsubscribeQuoteTicks
            The unsubscription command.

        """
        symbol: str = self._get_finam_symbol(command.instrument_id)
        await self._quotes_stream.unsubscribe_quotes([symbol])
        self._log.info(f"Unsubscribed from quote ticks: {symbol}")

    # -- SUBSCRIPTIONS: BARS ----------------------------------------------------------------------

    async def _subscribe_bars(self, command: SubscribeBars) -> None:
        """
        Subscribe to bars (OHLCV candles) for an instrument.

        Parameters
        ----------
        command : SubscribeBars
            The subscription command.

        """
        instrument_id: InstrumentId = command.instrument_id
        symbol: str = self._get_finam_symbol(instrument_id)
        bar_type = command.bar_type

        # Convert Nautilus BarSpec to Finam TimeFrame
        try:
            timeframe = self._nautilus_bar_spec_to_finam_timeframe(bar_type.spec)
        except ValueError as e:
            self._log.error(f"Cannot subscribe to bars for {symbol}: {e}")
            return

        def callback(response: Any) -> None:
            """Handle bar updates from gRPC stream."""
            try:
                # Get price_precision from cached instrument
                instrument = self._cache.instrument(instrument_id)
                if instrument is None:
                    self._log.error(
                        f"Instrument {instrument_id} not found in cache. "
                        f"Cannot parse bars without price precision."
                    )
                    return

                price_precision = instrument.price_precision
                ts_init = self._clock.timestamp_ns()
                bars = parse_bar_response(response, instrument_id, bar_type, price_precision, ts_init)
                for bar in bars:
                    self._handle_data(bar)
            except Exception as e:
                self._log.error(
                    f"Error parsing bar for {symbol}: {e}",
                    exc_info=True,
                )

        await self._bars_stream.subscribe_bars(symbol, timeframe.name, callback)
        self._log.info(f"Subscribed to bars: {symbol} {timeframe}", LogColor.BLUE)

    async def _unsubscribe_bars(self, command: UnsubscribeBars) -> None:
        """
        Unsubscribe from bars.

        Parameters
        ----------
        command : UnsubscribeBars
            The unsubscription command.

        """
        symbol: str = self._get_finam_symbol(command.instrument_id)
        bar_type = command.bar_type

        # Convert Nautilus BarSpec to Finam TimeFrame
        try:
            timeframe = self._nautilus_bar_spec_to_finam_timeframe(bar_type.spec)
        except ValueError as e:
            self._log.error(f"Cannot unsubscribe from bars for {symbol}: {e}")
            return

        await self._bars_stream.unsubscribe_bars(symbol, timeframe.name)
        self._log.info(f"Unsubscribed from bars: {symbol} {timeframe}")

    # -- HELPER METHODS ---------------------------------------------------------------------------

    def _get_finam_symbol(self, instrument_id: InstrumentId) -> str:
        """
        Convert Nautilus InstrumentId to Finam symbol format.

        Finam format: "SYMBOL@EXCHANGE" (e.g., "SBER@MISX", "GAZP@MISX")

        Parameters
        ----------
        instrument_id : InstrumentId
            The Nautilus instrument ID.

        Returns
        -------
        str
            The Finam symbol.

        """
        # Extract symbol without venue suffix
        # InstrumentId format: "SBER@MISX.FINAM"
        # Finam API expects: "SBER@MISX"
        symbol_str = instrument_id.symbol.value
        if ".FINAM" in symbol_str:
            return symbol_str.replace(".FINAM", "")
        return symbol_str

    def _nautilus_bar_spec_to_finam_timeframe(self, bar_spec: BarSpecification) -> TimeFrame:
        """
        Convert Nautilus BarSpecification to Finam TimeFrame.

        Parameters
        ----------
        bar_spec : BarSpecification
            The Nautilus bar specification.

        Returns
        -------
        TimeFrame
            The Finam timeframe.

        Raises
        ------
        ValueError
            If the bar specification is not supported by Finam.

        """
        agg = bar_spec.aggregation
        step = bar_spec.step

        # Minute bars
        if agg == BarAggregation.MINUTE:
            if step == 1:
                return TimeFrame.M1
            elif step == 5:
                return TimeFrame.M5
            elif step == 15:
                return TimeFrame.M15
            elif step == 30:
                return TimeFrame.M30
            else:
                raise ValueError(
                    f"Unsupported minute step: {step}. "
                    "Supported minute steps: 1, 5, 15, 30"
                )

        # Hour bars
        elif agg == BarAggregation.HOUR:
            if step == 1:
                return TimeFrame.H1
            elif step == 2:
                return TimeFrame.H2
            elif step == 4:
                return TimeFrame.H4
            elif step == 8:
                return TimeFrame.H8
            else:
                raise ValueError(
                    f"Unsupported hour step: {step}. "
                    "Supported hour steps: 1, 2, 4, 8"
                )

        # Day bars
        elif agg == BarAggregation.DAY:
            if step == 1:
                return TimeFrame.D
            else:
                raise ValueError(
                    f"Unsupported day step: {step}. "
                    "Only 1-day bars are supported"
                )

        # Week bars
        elif agg == BarAggregation.WEEK:
            if step == 1:
                return TimeFrame.W
            else:
                raise ValueError(
                    f"Unsupported week step: {step}. "
                    "Only 1-week bars are supported"
                )

        # Month bars
        elif agg == BarAggregation.MONTH:
            if step == 1:
                return TimeFrame.MN
            else:
                raise ValueError(
                    f"Unsupported month step: {step}. "
                    "Only 1-month bars are supported"
                )

        # Unsupported aggregation types
        else:
            raise ValueError(
                f"Unsupported bar aggregation: {agg}. "
                "Finam supports: MINUTE, HOUR, DAY, WEEK, MONTH"
            )
