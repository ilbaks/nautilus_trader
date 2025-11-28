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

import asyncio
from datetime import datetime
from typing import Callable

import grpc
from google.protobuf.timestamp_pb2 import Timestamp
from google.type.interval_pb2 import Interval

from nautilus_trader.adapters.finam.grpc.client.client import FinamGrpcClient
from nautilus_trader.adapters.finam.grpc.common.enums import TimeFrame
from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.marketdata.marketdata_service_pb2 import (
    BarsRequest,
    BarsResponse,
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

    async def request_historical_bars(
        self,
        symbol: str,
        timeframe: TimeFrame,
        start_time: datetime,
        end_time: datetime,
        max_retries: int = 3,
        chunk_days: int = 7,
    ) -> list:
        """
        Request historical bars for a specific time range.

        This is a unary RPC call (not streaming) that fetches a batch
        of historical OHLCV bars from the server.

        **IMPORTANT: Finam API Limits**
        - For intraday timeframes (M1, M5, H1, etc.): max 30 days per request
        - This method automatically chunks large requests into smaller periods

        Parameters
        ----------
        symbol : str
            The instrument symbol (e.g., "SiZ5@RTSX")
        timeframe : TimeFrame
            The bar timeframe (M1, M5, H1, D, etc.)
        start_time : datetime
            Start of the time range (timezone-aware recommended)
        end_time : datetime
            End of the time range (timezone-aware recommended)
        max_retries : int
            Maximum number of retry attempts on failure (default: 3)
        chunk_days : int
            Size of chunks in days for splitting large requests (default: 7)
            Set to 0 to disable chunking (not recommended for >30 days)

        Returns
        -------
        list
            List of Bar protobuf messages

        Raises
        ------
        grpc.RpcError
            If the request fails after all retries
        ValueError
            If start_time >= end_time or parameters invalid

        Examples
        --------
        >>> from datetime import datetime, timedelta, timezone
        >>> manager = BarsStreamManager(client, logger)
        >>>
        >>> # Request 1 week of M1 bars
        >>> end = datetime.now(timezone.utc)
        >>> start = end - timedelta(days=7)
        >>> bars = await manager.request_historical_bars(
        ...     symbol="SiZ5@RTSX",
        ...     timeframe=TimeFrame.M1,
        ...     start_time=start,
        ...     end_time=end,
        ... )
        >>> print(f"Loaded {len(bars)} bars")
        >>>
        >>> # Request 90 days (auto-chunked into 7-day periods)
        >>> start = end - timedelta(days=90)
        >>> bars = await manager.request_historical_bars(
        ...     symbol="SiZ5@RTSX",
        ...     timeframe=TimeFrame.M1,
        ...     start_time=start,
        ...     end_time=end,
        ... )
        >>> print(f"Loaded {len(bars)} bars")
        """
        # Validation
        if start_time >= end_time:
            raise ValueError(
                f"start_time ({start_time}) must be before end_time ({end_time})"
            )

        # Calculate total period
        total_period = end_time - start_time
        total_days = total_period.total_seconds() / 86400  # Convert to days

        # Check if chunking is needed
        if chunk_days > 0 and total_days > chunk_days:
            self._logger.info(
                f"Chunking request: {total_days:.1f} days split into {chunk_days}-day chunks"
            )
            return await self._request_historical_bars_chunked(
                symbol=symbol,
                timeframe=timeframe,
                start_time=start_time,
                end_time=end_time,
                chunk_days=chunk_days,
                max_retries=max_retries,
            )

        # Single request (no chunking)
        return await self._request_single_chunk(
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
            max_retries=max_retries,
        )

    async def _request_historical_bars_chunked(
        self,
        symbol: str,
        timeframe: TimeFrame,
        start_time: datetime,
        end_time: datetime,
        chunk_days: int,
        max_retries: int,
    ) -> list:
        """
        Request historical bars in chunks to handle large date ranges.

        Splits the request into smaller time periods and combines results.
        """
        from datetime import timedelta

        all_bars = []
        current_start = start_time
        chunk_delta = timedelta(days=chunk_days)
        chunk_number = 0

        while current_start < end_time:
            chunk_number += 1
            # Calculate chunk end (but not beyond final end_time)
            current_end = min(current_start + chunk_delta, end_time)

            self._logger.info(
                f"📦 Chunk {chunk_number}: {symbol} {timeframe.name} "
                f"from {current_start.strftime('%Y-%m-%d')} "
                f"to {current_end.strftime('%Y-%m-%d')}"
            )

            # Request chunk
            try:
                chunk_bars = await self._request_single_chunk(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_time=current_start,
                    end_time=current_end,
                    max_retries=max_retries,
                )

                all_bars.extend(chunk_bars)
                self._logger.info(
                    f"   ✅ Loaded {len(chunk_bars)} bars (total: {len(all_bars)})"
                )

            except grpc.RpcError as e:
                self._logger.error(
                    f"   ❌ Failed to load chunk {chunk_number}: {e}"
                )
                # Continue with next chunk instead of failing completely
                # This allows partial data recovery

            # Move to next chunk
            current_start = current_end

            # Small delay between chunks to respect rate limits
            if current_start < end_time:
                await asyncio.sleep(0.5)

        self._logger.info(
            f"✅ Chunked request complete: {len(all_bars)} total bars for {symbol}"
        )
        return all_bars

    async def _request_single_chunk(
        self,
        symbol: str,
        timeframe: TimeFrame,
        start_time: datetime,
        end_time: datetime,
        max_retries: int,
    ) -> list:
        """
        Request a single chunk of historical bars (internal method).

        This method handles a single API call for a time range.
        """
        self._logger.debug(
            f"Requesting bars: {symbol} {timeframe.name} "
            f"from {start_time} to {end_time}"
        )

        # Create Interval (google.type.Interval)
        interval = Interval()

        # Convert datetime to Timestamp
        start_ts = Timestamp()
        start_ts.FromDatetime(start_time)
        interval.start_time.CopyFrom(start_ts)

        end_ts = Timestamp()
        end_ts.FromDatetime(end_time)
        interval.end_time.CopyFrom(end_ts)

        # Create request
        request = BarsRequest(
            symbol=symbol,
            timeframe=timeframe.value,  # Protobuf enum value
            interval=interval,
        )

        # Execute request with retries
        for attempt in range(max_retries):
            try:
                # Get metadata (authorization)
                metadata = await self._client.get_metadata()

                # Apply rate limiting
                await self._client.rate_limiter.acquire()

                # Make unary call
                response: BarsResponse = await self._client.marketdata.Bars(
                    request,
                    metadata=metadata,
                )

                # Log success
                bar_count = len(response.bars)
                self._logger.debug(
                    f"Successfully loaded {bar_count} bars for {symbol} "
                    f"{timeframe.name}"
                )

                # ✅ FIX: Deep-copy protobuf bars to avoid use-after-free
                # When response goes out of scope, the underlying C++ protobuf buffer
                # may be freed. Accessing bar fields later causes segfault.
                # Solution: Copy each bar to break the reference to parent buffer.
                from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.marketdata.marketdata_service_pb2 import (
                    Bar as BarMessage,
                )
                copied_bars = []
                for bar in response.bars:
                    new_bar = BarMessage()
                    new_bar.CopyFrom(bar)
                    copied_bars.append(new_bar)
                return copied_bars

            except grpc.RpcError as e:
                self._logger.warning(
                    f"Attempt {attempt + 1}/{max_retries} failed for {symbol}: {e}"
                )

                if attempt == max_retries - 1:
                    # Last attempt failed
                    self._logger.error(
                        f"Failed to load historical bars after {max_retries} attempts"
                    )
                    raise

                # Exponential backoff
                await asyncio.sleep(2 ** attempt)

        return []  # Should never reach here due to raise above
