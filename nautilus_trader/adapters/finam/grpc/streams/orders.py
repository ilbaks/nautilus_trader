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
OrderTrade bidirectional stream manager for Finam gRPC API.
"""

import asyncio
from typing import Callable

import grpc
from nautilus_trader.adapters.finam.grpc.client.client import FinamGrpcClient
from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.orders.orders_service_pb2 import (
    OrderTradeRequest,
    OrderTradeResponse,
)
from nautilus_trader.adapters.finam.grpc.streams.base import BaseStreamManager
from nautilus_trader.common.component import Logger


class OrderTradeStreamManager(BaseStreamManager):
    """
    Manages OrderTrade bidirectional streaming for Finam gRPC API.

    Bidirectional Stream: SubscribeOrderTrade(stream requests) -> stream of Order/Trade updates

    Features:
    - Bidirectional stream (client sends subscription requests, server sends updates)
    - KeepAlive mechanism (ping every 30 seconds to prevent timeout)
    - Auto-reconnect on disconnection
    - Real-time order and trade updates

    Parameters
    ----------
    client : FinamGrpcClient
        The gRPC client for API communication
    account_id : str
        The trading account ID
    logger : Logger
        The logger for stream events
    """

    def __init__(
        self,
        client: FinamGrpcClient,
        account_id: str,
        logger: Logger,
    ) -> None:
        super().__init__(logger)
        self._client = client
        self._account_id = account_id
        self._request_stream = None
        self._keepalive_task: asyncio.Task | None = None

    async def subscribe_order_trade(
        self,
        callback: Callable[[OrderTradeResponse], None],
        data_type: OrderTradeRequest.DataType = OrderTradeRequest.DATA_TYPE_ALL,
    ) -> None:
        """
        Subscribe to Order and Trade updates.

        Creates a bidirectional stream:
        - Client sends subscription requests (with KeepAlive pings)
        - Server sends order/trade updates

        Parameters
        ----------
        callback : Callable[[OrderTradeResponse], None]
            Handler for Order/Trade updates
        data_type : OrderTradeRequest.DataType, default DATA_TYPE_ALL
            Type of updates: ALL (orders+trades), ORDERS, or TRADES
        """
        stream_id = f"ordertrade_{self._account_id}"

        if stream_id in self._streams:
            self._logger.warning(f"Already subscribed to OrderTrade for account {self._account_id}")
            return

        async def stream_reader(cancel_token):
            """Stream reader with bidirectional communication."""
            retry_count = 0
            max_retries = 5
            base_delay = 1.0

            while not cancel_token.is_set() and self._is_running:
                try:
                    # Create bidirectional stream
                    metadata = await self._client.get_metadata()

                    call = self._client.orders.SubscribeOrderTrade(metadata=metadata)
                    self._request_stream = call

                    # Send initial subscription request
                    subscribe_request = OrderTradeRequest(
                        account_id=self._account_id,
                        action=OrderTradeRequest.ACTION_SUBSCRIBE,
                        data_type=data_type,
                    )
                    await call.write(subscribe_request)
                    self._logger.info(f"Sent subscription request for OrderTrade: {self._account_id}")

                    # Start KeepAlive task
                    self._keepalive_task = asyncio.create_task(
                        self._keepalive_loop(call, cancel_token, data_type)
                    )

                    retry_count = 0  # Reset on successful connection

                    # Read responses
                    async for response in call:
                        if cancel_token.is_set():
                            break

                        try:
                            callback(response)
                        except Exception as e:
                            self._logger.error(
                                f"Error in OrderTrade callback: {e}",
                                exc_info=True,
                            )

                    # Stream ended
                    if not cancel_token.is_set():
                        self._logger.warning("OrderTrade stream ended, reconnecting...")

                except grpc.aio.AioRpcError as e:
                    if cancel_token.is_set():
                        break

                    retry_count += 1

                    if e.code() == grpc.StatusCode.CANCELLED:
                        self._logger.info("OrderTrade stream cancelled")
                        break
                    elif e.code() == grpc.StatusCode.UNAUTHENTICATED:
                        self._logger.error(f"OrderTrade authentication failed: {e.details()}")
                        await asyncio.sleep(base_delay)
                        continue
                    else:
                        self._logger.error(
                            f"OrderTrade gRPC error (attempt {retry_count}/{max_retries}): "
                            f"{e.code()} - {e.details()}"
                        )

                    # Exponential backoff
                    if retry_count >= max_retries:
                        self._logger.error("OrderTrade max retries exceeded, giving up")
                        break

                    delay = min(base_delay * (2 ** (retry_count - 1)), 30.0)
                    self._logger.info(f"Reconnecting OrderTrade in {delay:.1f}s...")
                    await asyncio.sleep(delay)

                except asyncio.CancelledError:
                    self._logger.info("OrderTrade stream task cancelled")
                    break

                except Exception as e:
                    self._logger.error(
                        f"Unexpected error in OrderTrade stream: {e}",
                        exc_info=True,
                    )

                    retry_count += 1
                    if retry_count >= max_retries:
                        self._logger.error("OrderTrade max retries exceeded, giving up")
                        break

                    delay = min(base_delay * (2 ** (retry_count - 1)), 30.0)
                    await asyncio.sleep(delay)

                finally:
                    # Clean up KeepAlive task
                    if self._keepalive_task and not self._keepalive_task.done():
                        self._keepalive_task.cancel()
                        try:
                            await self._keepalive_task
                        except asyncio.CancelledError:
                            pass
                    self._keepalive_task = None
                    self._request_stream = None

            self._logger.info("OrderTrade stream reader exited")

        self._create_stream_task(stream_id, stream_reader)
        self._logger.info(f"Subscribed to OrderTrade: {self._account_id}")

    async def _keepalive_loop(
        self,
        call,
        cancel_token: asyncio.Event,
        data_type: OrderTradeRequest.DataType,
    ) -> None:
        """
        Send KeepAlive pings every 30 seconds.

        This prevents the bidirectional stream from timing out.
        C# implementation sends subscription request every 30 seconds.

        Parameters
        ----------
        call
            The bidirectional stream call
        cancel_token : asyncio.Event
            Event to signal cancellation
        data_type : OrderTradeRequest.DataType
            Type of subscription to maintain
        """
        try:
            while not cancel_token.is_set():
                await asyncio.sleep(30.0)

                if cancel_token.is_set():
                    break

                # Send subscription request as KeepAlive ping
                keepalive_request = OrderTradeRequest(
                    account_id=self._account_id,
                    action=OrderTradeRequest.ACTION_SUBSCRIBE,
                    data_type=data_type,
                )

                try:
                    await call.write(keepalive_request)
                    self._logger.debug(f"Sent KeepAlive ping for OrderTrade: {self._account_id}")
                except Exception as e:
                    self._logger.error(f"Failed to send KeepAlive ping: {e}")
                    break

        except asyncio.CancelledError:
            self._logger.debug("KeepAlive loop cancelled")

    async def unsubscribe_order_trade(self) -> None:
        """Unsubscribe from OrderTrade updates."""
        stream_id = f"ordertrade_{self._account_id}"

        # Send unsubscribe request if stream is active
        if self._request_stream:
            try:
                unsubscribe_request = OrderTradeRequest(
                    account_id=self._account_id,
                    action=OrderTradeRequest.ACTION_UNSUBSCRIBE,
                    data_type=OrderTradeRequest.DATA_TYPE_ALL,
                )
                await self._request_stream.write(unsubscribe_request)
                self._logger.info(f"Sent unsubscribe request for OrderTrade: {self._account_id}")
            except Exception as e:
                self._logger.error(f"Failed to send unsubscribe request: {e}")

        # Stop stream
        await self._stop_stream(stream_id)
        self._request_stream = None
        self._logger.info(f"Unsubscribed from OrderTrade: {self._account_id}")
