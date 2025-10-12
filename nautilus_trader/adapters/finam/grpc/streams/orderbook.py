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
OrderBook stream manager for Finam gRPC API.
"""

from typing import Callable

from nautilus_trader.adapters.finam.grpc.client.client import FinamGrpcClient
from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.marketdata.marketdata_service_pb2 import (
    SubscribeOrderBookRequest,
    SubscribeOrderBookResponse,
)
from nautilus_trader.adapters.finam.grpc.streams.base import BaseStreamManager
from nautilus_trader.common.component import Logger


class OrderBookStreamManager(BaseStreamManager):
    """
    Manages OrderBook streaming subscriptions for Finam gRPC API.

    Server Stream: SubscribeOrderBook(symbol) -> stream of OrderBook updates

    Features:
    - Per-instrument OrderBook streams
    - Auto-reconnect on disconnection
    - Incremental updates (ADD, UPDATE, REMOVE actions)

    Parameters
    ----------
    client : FinamGrpcClient
        The gRPC client for API communication
    logger : Logger
        The logger for stream events
    """

    def __init__(
        self,
        client: FinamGrpcClient,
        logger: Logger,
    ) -> None:
        super().__init__(logger)
        self._client = client

    async def subscribe_order_book(
        self,
        symbol: str,
        callback: Callable[[SubscribeOrderBookResponse], None],
    ) -> None:
        """
        Subscribe to OrderBook updates for a symbol.

        Creates a server-side stream that sends incremental OrderBook updates.
        Each update contains rows with actions: ADD, UPDATE, or REMOVE.

        Parameters
        ----------
        symbol : str
            The instrument symbol (e.g., "SBER@MISX")
        callback : Callable[[SubscribeOrderBookResponse], None]
            Handler for OrderBook updates
        """
        stream_id = f"orderbook_{symbol}"

        if stream_id in self._streams:
            self._logger.warning(f"Already subscribed to OrderBook for {symbol}")
            return

        async def stream_factory():
            """Create OrderBook stream."""
            request = SubscribeOrderBookRequest(symbol=symbol)
            metadata = await self._client.get_metadata()

            return self._client.marketdata.SubscribeOrderBook(
                request,
                metadata=metadata,
            )

        def message_handler(response: SubscribeOrderBookResponse):
            """Handle incoming OrderBook messages."""
            try:
                callback(response)
            except Exception as e:
                self._logger.error(
                    f"Error in OrderBook callback for {symbol}: {e}",
                    exc_info=True,
                )

        # Create stream reader task with auto-reconnect
        async def stream_reader(cancel_token):
            await self._stream_reader_with_reconnect(
                stream_id=stream_id,
                stream_factory=stream_factory,
                message_handler=message_handler,
                cancel_token=cancel_token,
                max_retries=5,
                base_delay=1.0,
            )

        self._create_stream_task(stream_id, stream_reader)
        self._logger.info(f"Subscribed to OrderBook: {symbol}")

    async def unsubscribe_order_book(self, symbol: str) -> None:
        """
        Unsubscribe from OrderBook updates for a symbol.

        Parameters
        ----------
        symbol : str
            The instrument symbol
        """
        stream_id = f"orderbook_{symbol}"
        await self._stop_stream(stream_id)
        self._logger.info(f"Unsubscribed from OrderBook: {symbol}")
