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
Quote stream manager for Finam gRPC API.
"""

from typing import Callable

from nautilus_trader.adapters.finam.grpc.client.client import FinamGrpcClient
from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.marketdata.marketdata_service_pb2 import (
    SubscribeQuoteRequest,
    SubscribeQuoteResponse,
)
from nautilus_trader.adapters.finam.grpc.streams.base import BaseStreamManager
from nautilus_trader.common.component import Logger


class QuoteStreamManager(BaseStreamManager):
    """
    Manages Quote streaming subscriptions for Finam gRPC API.

    Server Stream: SubscribeQuote(symbols[]) -> stream of Quote updates

    IMPORTANT: Unlike OrderBook/Trades streams, SubscribeQuote accepts
    MULTIPLE symbols in a single stream. This is a key difference in the API.

    Features:
    - Multiple symbols in single stream (batch subscription)
    - Auto-reconnect on disconnection
    - Quote data: bid, ask, bid_size, ask_size, last, volume, OHLC

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

    async def subscribe_quotes(
        self,
        symbols: list[str],
        callback: Callable[[SubscribeQuoteResponse], None],
    ) -> None:
        """
        Subscribe to Quote updates for multiple symbols.

        Creates a server-side stream that sends quote updates for all requested symbols.
        Each response contains quotes for potentially multiple symbols.

        IMPORTANT: Finam API design - one stream can handle multiple symbols.
        This is different from OrderBook/Trades which require per-instrument streams.

        Parameters
        ----------
        symbols : list[str]
            List of instrument symbols (e.g., ["SBER@MISX", "GAZP@MISX"])
        callback : Callable[[SubscribeQuoteResponse], None]
            Handler for Quote updates
        """
        if not symbols:
            self._logger.warning("No symbols provided for quote subscription")
            return

        # Create stream ID from all symbols
        stream_id = f"quotes_{'_'.join(sorted(symbols))}"

        if stream_id in self._streams:
            self._logger.warning(f"Already subscribed to Quotes for symbols: {symbols}")
            return

        async def stream_factory():
            """Create Quote stream for multiple symbols."""
            request = SubscribeQuoteRequest(symbols=symbols)
            metadata = await self._client.get_metadata()

            return self._client.marketdata.SubscribeQuote(
                request,
                metadata=metadata,
            )

        def message_handler(response: SubscribeQuoteResponse):
            """Handle incoming Quote messages."""
            try:
                # Check for stream error
                if response.HasField("error"):
                    self._logger.error(
                        f"Quote stream error: code={response.error.code}, "
                        f"description={response.error.description}"
                    )
                    return

                callback(response)
            except Exception as e:
                self._logger.error(
                    f"Error in Quote callback for symbols {symbols}: {e}",
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
        self._logger.info(f"Subscribed to Quotes: {symbols}")

    async def unsubscribe_quotes(self, symbols: list[str]) -> None:
        """
        Unsubscribe from Quote updates for symbols.

        Parameters
        ----------
        symbols : list[str]
            List of instrument symbols
        """
        stream_id = f"quotes_{'_'.join(sorted(symbols))}"
        await self._stop_stream(stream_id)
        self._logger.info(f"Unsubscribed from Quotes: {symbols}")
