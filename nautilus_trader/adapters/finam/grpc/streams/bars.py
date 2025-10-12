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
Bars stream manager for Finam gRPC API.
"""

from typing import Callable

from nautilus_trader.adapters.finam.grpc.client.client import FinamGrpcClient
from nautilus_trader.adapters.finam.grpc.common.enums import TimeFrame
from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.marketdata.marketdata_service_pb2 import (
    SubscribeBarsRequest,
    SubscribeBarsResponse,
)
from nautilus_trader.adapters.finam.grpc.streams.base import BaseStreamManager
from nautilus_trader.common.component import Logger


class BarsStreamManager(BaseStreamManager):
    """
    Manages Bars streaming subscriptions for Finam gRPC API.

    Server Stream: SubscribeBars(symbol, timeframe) -> stream of Bar updates

    Features:
    - Per-instrument + per-timeframe subscriptions
    - Auto-reconnect on disconnection
    - Real-time OHLCV bars

    Supported Timeframes:
    - M1 (1 minute) - depth 7 days
    - M5 (5 minutes) - depth 30 days
    - M15 (15 minutes) - depth 30 days
    - M30 (30 minutes) - depth 30 days
    - H1 (1 hour) - depth 30 days
    - H2 (2 hours) - depth 30 days
    - H4 (4 hours) - depth 30 days
    - H8 (8 hours) - depth 30 days
    - D (1 day) - depth 365 days
    - W (1 week) - depth 1825 days
    - MN (1 month) - depth 1825 days
    - QR (1 quarter) - depth 1825 days

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

    async def subscribe_bars(
        self,
        symbol: str,
        timeframe: TimeFrame,
        callback: Callable[[SubscribeBarsResponse], None],
    ) -> None:
        """
        Subscribe to Bars updates for a symbol and timeframe.

        Creates a server-side stream that sends real-time OHLCV bar updates.
        Each update contains bars with timestamp, open, high, low, close, volume.

        Parameters
        ----------
        symbol : str
            The instrument symbol (e.g., "SBER@MISX")
        timeframe : TimeFrame
            The bar timeframe (e.g., TimeFrame.M1, TimeFrame.H1)
        callback : Callable[[SubscribeBarsResponse], None]
            Handler for Bars updates
        """
        # Get timeframe name for logging
        timeframe_name = timeframe.name
        stream_id = f"bars_{symbol}_{timeframe_name}"

        if stream_id in self._streams:
            self._logger.warning(
                f"Already subscribed to Bars for {symbol} {timeframe_name}"
            )
            return

        async def stream_factory():
            """Create Bars stream."""
            request = SubscribeBarsRequest(
                symbol=symbol,
                timeframe=timeframe.value,  # Use .value to get Protobuf enum
            )
            metadata = await self._client.get_metadata()

            return self._client.marketdata.SubscribeBars(
                request,
                metadata=metadata,
            )

        def message_handler(response: SubscribeBarsResponse):
            """Handle incoming Bars messages."""
            try:
                callback(response)
            except Exception as e:
                self._logger.error(
                    f"Error in Bars callback for {symbol} {timeframe_name}: {e}",
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
        self._logger.info(f"Subscribed to Bars: {symbol} {timeframe_name}")

    async def unsubscribe_bars(self, symbol: str, timeframe: TimeFrame) -> None:
        """
        Unsubscribe from Bars updates for a symbol and timeframe.

        Parameters
        ----------
        symbol : str
            The instrument symbol
        timeframe : TimeFrame
            The bar timeframe
        """
        timeframe_name = timeframe.name
        stream_id = f"bars_{symbol}_{timeframe_name}"
        await self._stop_stream(stream_id)
        self._logger.info(f"Unsubscribed from Bars: {symbol} {timeframe_name}")
