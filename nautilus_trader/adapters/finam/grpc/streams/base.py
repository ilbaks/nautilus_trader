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
Base stream management for Finam gRPC API.
"""

import asyncio
from typing import Any, Callable

import grpc
from nautilus_trader.common.component import Logger


class BaseStreamManager:
    """
    Base class for managing gRPC streams with auto-reconnect logic.

    Provides:
    - Stream lifecycle management (start/stop)
    - Auto-reconnect with exponential backoff
    - Graceful cancellation
    - Error handling and logging

    Parameters
    ----------
    logger : Logger
        The logger for stream events
    """

    def __init__(self, logger: Logger) -> None:
        self._logger = logger
        self._streams: dict[str, asyncio.Task] = {}
        self._cancellation_tokens: dict[str, asyncio.Event] = {}
        self._is_running: bool = True  # Start in running state by default

    async def start(self) -> None:
        """Start the stream manager."""
        self._is_running = True
        self._logger.info("Stream manager started")

    async def stop(self) -> None:
        """Stop all streams gracefully."""
        self._is_running = False

        # Cancel all active streams
        for stream_id in list(self._streams.keys()):
            await self._stop_stream(stream_id)

        self._logger.info("Stream manager stopped")

    async def _stop_stream(self, stream_id: str) -> None:
        """
        Stop a specific stream gracefully.

        Parameters
        ----------
        stream_id : str
            The unique identifier for the stream
        """
        if stream_id in self._cancellation_tokens:
            self._cancellation_tokens[stream_id].set()

        if stream_id in self._streams:
            task = self._streams[stream_id]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            del self._streams[stream_id]
            self._logger.info(f"Stream stopped: {stream_id}")

        if stream_id in self._cancellation_tokens:
            del self._cancellation_tokens[stream_id]

    def _create_stream_task(
        self,
        stream_id: str,
        coro: Callable[..., Any]
    ) -> asyncio.Task:
        """
        Create and register a new stream task.

        Parameters
        ----------
        stream_id : str
            The unique identifier for the stream
        coro : Callable
            The coroutine for the stream reader

        Returns
        -------
        asyncio.Task
            The created stream task
        """
        # Create cancellation token
        cancel_token = asyncio.Event()
        self._cancellation_tokens[stream_id] = cancel_token

        # Create and register task
        task = asyncio.create_task(coro(cancel_token))
        self._streams[stream_id] = task

        self._logger.info(f"Stream created: {stream_id}")
        return task

    async def _stream_reader_with_reconnect(
        self,
        stream_id: str,
        stream_factory: Callable[[], Any],
        message_handler: Callable[[Any], None],
        cancel_token: asyncio.Event,
        max_retries: int = 5,
        base_delay: float = 1.0,
    ) -> None:
        """
        Generic stream reader with auto-reconnect logic.

        Parameters
        ----------
        stream_id : str
            The unique identifier for the stream
        stream_factory : Callable
            Factory function to create the gRPC stream
        message_handler : Callable
            Handler for incoming stream messages
        cancel_token : asyncio.Event
            Event to signal stream cancellation
        max_retries : int, default 5
            Maximum number of reconnect attempts
        base_delay : float, default 1.0
            Base delay for exponential backoff (seconds)
        """
        self._logger.debug(f"Stream reader started for: {stream_id}, is_running={self._is_running}")
        retry_count = 0

        while not cancel_token.is_set() and self._is_running:
            try:
                # Create stream
                self._logger.debug(f"Creating stream: {stream_id}")
                stream = await stream_factory()
                retry_count = 0  # Reset on successful connection

                self._logger.info(f"Stream connected: {stream_id}")

                # Read messages
                async for message in stream:
                    if cancel_token.is_set():
                        break

                    try:
                        message_handler(message)
                    except Exception as e:
                        self._logger.error(
                            f"Error handling message in {stream_id}: {e}",
                            exc_info=True
                        )

                # Stream ended normally
                if not cancel_token.is_set():
                    self._logger.warning(f"Stream {stream_id} ended normally, reconnecting...")
                else:
                    self._logger.info(f"Stream {stream_id} cancelled by token")

            except grpc.aio.AioRpcError as e:
                if cancel_token.is_set():
                    break

                retry_count += 1

                if e.code() == grpc.StatusCode.CANCELLED:
                    self._logger.info(f"Stream {stream_id} cancelled")
                    break
                elif e.code() == grpc.StatusCode.UNAUTHENTICATED:
                    self._logger.error(f"Stream {stream_id} authentication failed: {e.details()}")
                    # JWT token expired, need to refresh
                    await asyncio.sleep(base_delay)
                    continue
                else:
                    self._logger.error(
                        f"Stream {stream_id} gRPC error (attempt {retry_count}/{max_retries}): "
                        f"{e.code()} - {e.details()}"
                    )

                # Exponential backoff
                if retry_count >= max_retries:
                    self._logger.error(f"Stream {stream_id} max retries exceeded, giving up")
                    break

                delay = min(base_delay * (2 ** (retry_count - 1)), 30.0)
                self._logger.info(f"Reconnecting {stream_id} in {delay:.1f}s...")
                await asyncio.sleep(delay)

            except asyncio.CancelledError:
                self._logger.info(f"Stream {stream_id} task cancelled")
                break

            except Exception as e:
                self._logger.error(
                    f"Unexpected error in stream {stream_id}: {e}",
                    exc_info=True
                )

                retry_count += 1
                if retry_count >= max_retries:
                    self._logger.error(f"Stream {stream_id} max retries exceeded, giving up")
                    break

                delay = min(base_delay * (2 ** (retry_count - 1)), 30.0)
                await asyncio.sleep(delay)

        self._logger.info(f"Stream reader exited: {stream_id}")
