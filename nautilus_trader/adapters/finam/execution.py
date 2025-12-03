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
Execution client for Finam gRPC API.
"""

import asyncio
from decimal import Decimal
import grpc
from typing import Any

from nautilus_trader.adapters.finam.common.symbols import to_finam_symbol
from nautilus_trader.adapters.finam.grpc.client.client import FinamGrpcClient
from nautilus_trader.adapters.finam.grpc.parsing.execution import (
    parse_account_balances_and_margins,
    parse_account_response,
    parse_account_trade,
    parse_order_state,
)
from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.accounts.accounts_service_pb2 import (
    GetAccountRequest,
)
from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.orders.orders_service_pb2 import (
    CancelOrderRequest,
    GetOrderRequest,
    Order as FinamOrder,
    OrderTradeRequest,
    OrderTradeResponse,
    OrderType as FinamOrderType,
    TimeInForce as FinamTimeInForce,
)
from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.side_pb2 import (
    Side as FinamSide,
)
from nautilus_trader.adapters.finam.grpc.streams.orders import OrderTradeStreamManager
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import LiveClock
from nautilus_trader.common.component import MessageBus
from nautilus_trader.common.enums import LogColor
from nautilus_trader.common.providers import InstrumentProvider
from nautilus_trader.core.correctness import PyCondition
from nautilus_trader.core.uuid import UUID4
from nautilus_trader.execution.messages import CancelAllOrders
from nautilus_trader.execution.messages import CancelOrder
from nautilus_trader.execution.messages import GenerateFillReports
from nautilus_trader.execution.messages import GenerateOrderStatusReport
from nautilus_trader.execution.messages import GenerateOrderStatusReports
from nautilus_trader.execution.messages import ModifyOrder
from nautilus_trader.execution.messages import QueryAccount
from nautilus_trader.execution.messages import SubmitOrder
from nautilus_trader.execution.reports import FillReport
from nautilus_trader.execution.reports import OrderStatusReport
from nautilus_trader.live.execution_client import LiveExecutionClient
from nautilus_trader.model.enums import AccountType
from nautilus_trader.model.enums import OmsType
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.enums import OrderType
from nautilus_trader.model.enums import TimeInForce
from nautilus_trader.model.enums import OrderStatus
from nautilus_trader.model.identifiers import AccountId
from nautilus_trader.model.identifiers import ClientId
from nautilus_trader.model.identifiers import ClientOrderId
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import Symbol
from nautilus_trader.model.identifiers import VenueOrderId
from nautilus_trader.model.orders import LimitOrder
from nautilus_trader.model.orders import MarketOrder
from nautilus_trader.model.orders import Order
from nautilus_trader.model.objects import Quantity


class FinamExecutionClient(LiveExecutionClient):
    """
    Execution client for Finam gRPC API.

    Provides order management and execution capabilities through Finam gRPC streams.

    Parameters
    ----------
    loop : asyncio.AbstractEventLoop
        The event loop for the client.
    client : FinamGrpcClient
        The Finam gRPC client instance.
    msgbus : MessageBus
        The message bus for the client.
    cache : Cache
        The cache for the client.
    clock : LiveClock
        The clock for the client.
    instrument_provider : InstrumentProvider
        The instrument provider.
    account_id : str
        The Finam trading account ID.
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
        account_id: str,
        name: str | None = None,
    ) -> None:
        super().__init__(
            loop=loop,
            client_id=ClientId(name or "FINAM"),
            venue=None,  # Will be set based on instruments
            oms_type=OmsType.NETTING,  # Finam uses netting mode
            instrument_provider=instrument_provider,
            account_type=AccountType.MARGIN,  # Finam accounts are margin
            base_currency=None,  # Multi-currency account
            msgbus=msgbus,
            cache=cache,
            clock=clock,
        )

        # Configuration
        self._client = client
        self._finam_account_id = account_id
        self._set_account_id(AccountId(f"{name or 'FINAM'}-{account_id}"))

        # Stream managers
        self._order_trade_stream: OrderTradeStreamManager | None = None

        # Polling tasks
        self._update_account_task: asyncio.Task | None = None
        self._update_account_interval: int = 10  # Poll account every 10 seconds

        # Order tracking
        self._venue_order_id_to_client_order_id: dict[VenueOrderId, ClientOrderId] = {}
        self._finam_to_client_order_id: dict[str, ClientOrderId] = {}
        self._client_to_finam_order_id: dict[ClientOrderId, str] = {}
        self._client_to_venue_order_id: dict[ClientOrderId, VenueOrderId] = {}

        # Hot caches
        self._instrument_ids: dict[str, InstrumentId] = {}

        self._log.info(f"Finam account ID: {self._finam_account_id}", LogColor.BLUE)

    async def _connect(self) -> None:
        """Connect to Finam gRPC API and start streams."""
        self._log.info("Connecting to Finam execution services...")

        # Connect gRPC client
        await self._client.connect()
        self._log.debug("FinamGrpcClient connected")

        # Skip instrument provider loading here; data client loads instruments and
        # populates the shared cache. Avoiding a second GetAsset() prevents the
        # duplicate gRPC calls which have been causing segfaults.

        # NOTE: Order/trade stream subscription is disabled to avoid gRPC segfaults.
        # Execution events will be reflected via periodic account polling instead.
        self._order_trade_stream = None

        # Start account polling task
        self._update_account_task = self.create_task(self._poll_account_state())

        # Initial account state update
        await self._update_account_state()

        self._log.info("Connected to Finam execution services", LogColor.GREEN)

    async def _disconnect(self) -> None:
        """Disconnect from Finam gRPC API."""
        self._log.info("Disconnecting from Finam execution services...")

        # Cancel account polling task
        if self._update_account_task:
            self._log.debug("Canceling task 'poll_account_state'")
            self._update_account_task.cancel()
            try:
                await self._update_account_task
            except asyncio.CancelledError:
                pass
            self._update_account_task = None

        # Unsubscribe from order/trade stream
        if self._order_trade_stream:
            await self._order_trade_stream.unsubscribe_order_trade()
            await self._order_trade_stream.stop()
            self._order_trade_stream = None

        # Disconnect gRPC client
        await self._client.disconnect()
        self._log.debug("FinamGrpcClient disconnected")

        self._log.info("Disconnected from Finam execution services", LogColor.GREEN)

    async def generate_order_status_reports(self, command):
        """Finam API lacks order status bulk endpoint; return empty to satisfy reconciliation."""
        return []

    async def generate_fill_reports(self, command):
        """Finam API lacks fill history endpoint; return empty to satisfy reconciliation."""
        return []

    async def generate_position_status_reports(self, command):
        """Finam API lacks position status endpoint; return empty to satisfy reconciliation."""
        return []

    # -- ACCOUNT MANAGEMENT -----------------------------------------------------------------------

    async def _poll_account_state(self) -> None:
        """
        Periodically poll account state from Finam API.

        Polls GetAccount() every N seconds to update balances and positions.
        """
        try:
            while True:
                self._log.debug(
                    f"Scheduled task 'poll_account_state' to run in {self._update_account_interval}s"
                )
                await asyncio.sleep(self._update_account_interval)

                try:
                    await self._update_account_state()
                except Exception as e:
                    self._log.error(f"Error updating account state: {self._format_grpc_error(e)}")

        except asyncio.CancelledError:
            self._log.debug("Canceled task 'poll_account_state'")

    async def _update_account_state(self) -> None:
        """
        Update account state from Finam GetAccount() API.

        Fetches current balances, positions, and margin information.
        """
        try:
            self._log.debug("Requesting account state from Finam API...")
            metadata = await self._client.get_metadata()

            request = GetAccountRequest(account_id=self._finam_account_id)
            response = await self._client.accounts.GetAccount(request, metadata=metadata)

            ts_event = self._clock.timestamp_ns()

            # Parse balances, margins, and info from response
            balances, margins, info = parse_account_balances_and_margins(response)
            self._log.debug(f"Parsed: {len(balances)} balances, {len(margins)} margins")

            # Generate AccountState event using parent class method
            # This automatically publishes to msgbus AND adds to cache
            self.generate_account_state(
                balances=balances,
                margins=margins,
                reported=True,
                ts_event=ts_event,
                # info=info,  # REMOVED: causes issues with proto enums
            )

            self._log.info(f"Account state updated: {len(balances)} balances, {len(margins)} margins")

        except Exception as e:
            self._log.error(f"Failed to update account state: {self._format_grpc_error(e)}")
            import traceback
            self._log.debug(traceback.format_exc())

    # -- ORDER/TRADE STREAM HANDLERS --------------------------------------------------------------

    def _handle_order_trade_update(self, response: OrderTradeResponse) -> None:
        """
        Handle OrderTradeResponse from bidirectional stream.

        Parameters
        ----------
        response : OrderTradeResponse
            The response containing order states and/or trades

        """
        try:
            # Process order updates
            for order_state in response.orders:
                self._handle_order_state(order_state)

            # Process trade updates (fills)
            for trade in response.trades:
                self._handle_account_trade(trade)

        except Exception as e:
            self._log.error(
                f"Error handling order/trade update: {e}",
            )

    def _handle_order_state(self, order_state: Any) -> None:
        """
        Handle OrderState update from stream.

        Generates appropriate order events based on order status:
        - ACCEPTED → generate_order_accepted()
        - CANCELED → generate_order_canceled()
        - REJECTED → generate_order_rejected()
        - EXPIRED → generate_order_expired()

        Parameters
        ----------
        order_state : OrderState
            The Finam OrderState message

        """
        try:
            ts_init = self._clock.timestamp_ns()

            # Get symbol from order_state
            symbol = order_state.order.symbol

            # Resolve InstrumentId from symbol
            instrument_id = self._get_cached_instrument_id(symbol)

            # Parse order state
            parsed = parse_order_state(
                order_state=order_state,
                account_id=self.account_id,
                instrument_id=instrument_id,
                ts_init=ts_init,
            )

            venue_order_id = parsed["venue_order_id"]
            client_order_id = parsed["client_order_id"]
            order_status = parsed["order_status"]
            ts_event = parsed["ts_event"]

            # If client_order_id not in order, try to get from tracking dict
            if not client_order_id:
                client_order_id = self._venue_order_id_to_client_order_id.get(venue_order_id)
                if not client_order_id:
                    self._log.warning(
                        f"Cannot find client_order_id for {venue_order_id}, "
                        "sending OrderStatusReport instead"
                    )
                    # TODO: Send OrderStatusReport for unknown orders
                    return
            else:
                # Map shortened Finam ID back to full Nautilus ID if needed
                mapped = self._finam_to_client_order_id.get(client_order_id.value)
                if mapped:
                    client_order_id = mapped

            # Get strategy_id from cache
            strategy_id = self._cache.strategy_id_for_order(client_order_id)
            if strategy_id is None:
                self._log.debug(
                    f"Order {client_order_id} not found in cache (strategy_id=None), "
                    "may be external order or reconciliation needed"
                )
                # TODO: Send OrderStatusReport for unknown orders
                return

            self._log.debug(
                f"Order update: {venue_order_id} ({client_order_id}) -> {order_status}"
            )

            # Generate events based on order status
            # Import here to avoid circular imports
            from nautilus_trader.model.enums import OrderStatus

            if order_status == OrderStatus.ACCEPTED:
                self.generate_order_accepted(
                    strategy_id=strategy_id,
                    instrument_id=instrument_id,
                    client_order_id=client_order_id,
                    venue_order_id=venue_order_id,
                    ts_event=ts_event,
                )

            elif order_status == OrderStatus.CANCELED:
                self.generate_order_canceled(
                    strategy_id=strategy_id,
                    instrument_id=instrument_id,
                    client_order_id=client_order_id,
                    venue_order_id=venue_order_id,
                    ts_event=ts_event,
                )

            elif order_status == OrderStatus.REJECTED:
                self.generate_order_rejected(
                    strategy_id=strategy_id,
                    instrument_id=instrument_id,
                    client_order_id=client_order_id,
                    reason="Order rejected by exchange",  # TODO: Extract reason from order_state
                    ts_event=ts_event,
                )

            elif order_status == OrderStatus.EXPIRED:
                self.generate_order_expired(
                    strategy_id=strategy_id,
                    instrument_id=instrument_id,
                    client_order_id=client_order_id,
                    venue_order_id=venue_order_id,
                    ts_event=ts_event,
                )

            # Note: FILLED status is handled by _handle_account_trade()
            # PARTIALLY_FILLED is also handled there

        except Exception as e:
            self._log.error(f"Error handling order state: {e}")

    def _handle_account_trade(self, trade: Any) -> None:
        """
        Handle AccountTrade (fill) from stream.

        Generates OrderFilled event for each trade execution.

        Parameters
        ----------
        trade : AccountTrade
            The Finam AccountTrade message

        """
        try:
            ts_init = self._clock.timestamp_ns()

            # Get symbol from trade
            symbol = trade.symbol

            # Resolve InstrumentId from symbol
            instrument_id = self._get_cached_instrument_id(symbol)

            # Parse account trade
            parsed = parse_account_trade(
                trade=trade,
                account_id=self.account_id,
                instrument_id=instrument_id,
                ts_init=ts_init,
            )

            trade_id = parsed["trade_id"]
            venue_order_id = parsed["venue_order_id"]
            side = parsed["side"]
            quantity = parsed["quantity"]
            price = parsed["price"]
            ts_event = parsed["ts_event"]
            liquidity_side = parsed["liquidity_side"]

            # Get client_order_id from tracking dict
            client_order_id = self._venue_order_id_to_client_order_id.get(venue_order_id)
            if not client_order_id:
                self._log.warning(
                    f"Cannot find client_order_id for {venue_order_id} (trade {trade_id}), "
                    "trade fill may be for external order"
                )
                return

            # Get strategy_id from cache
            strategy_id = self._cache.strategy_id_for_order(client_order_id)
            if strategy_id is None:
                self._log.debug(
                    f"Order {client_order_id} not found in cache (strategy_id=None), "
                    "may be external order or reconciliation needed"
                )
                return

            # Get instrument for commission currency (cache first, then provider)
            instrument = self._find_instrument(instrument_id)
            if not instrument:
                self._log.error(
                    f"Cannot find instrument {instrument_id} for trade fill, "
                    "skipping commission calculation"
                )
                return

            # Finam doesn't provide commission in trade updates - use zero
            # TODO: Calculate commission from account state or fee schedule
            from nautilus_trader.model.objects import Money
            commission = Money(0, instrument.quote_currency)

            self._log.info(
                f"Trade fill: {trade_id} - {quantity} @ {price} (order {venue_order_id})"
            )

            # Generate OrderFilled event
            self.generate_order_filled(
                strategy_id=strategy_id,
                instrument_id=instrument_id,
                client_order_id=client_order_id,
                venue_order_id=venue_order_id,
                venue_position_id=None,  # NETTING mode
                trade_id=trade_id,
                order_side=side,
                order_type=self._cache.order(client_order_id).order_type,
                last_qty=quantity,
                last_px=price,
                quote_currency=instrument.quote_currency,
                commission=commission,
                liquidity_side=liquidity_side,
                ts_event=ts_event,
            )

        except Exception as e:
            self._log.error(f"Error handling account trade: {e}")

    # -- ORDER SUBMISSION -------------------------------------------------------------------------

    async def _submit_order(self, command: SubmitOrder) -> None:
        """
        Submit an order to Finam via gRPC PlaceOrder().

        Parameters
        ----------
        command : SubmitOrder
            The submit order command

        """
        order = command.order

        if order.is_closed:
            self._log.warning(f"Cannot submit already closed order {order}")
            return

        self._log.debug(f"Submitting order: {order}")

        # Generate OrderSubmitted event
        self.generate_order_submitted(
            strategy_id=order.strategy_id,
            instrument_id=order.instrument_id,
            client_order_id=order.client_order_id,
            ts_event=self._clock.timestamp_ns(),
        )

        try:
            # Map OrderType to Finam OrderType submission method
            if order.order_type == OrderType.MARKET:
                await self._submit_market_order(order)
            elif order.order_type == OrderType.LIMIT:
                await self._submit_limit_order(order)
            else:
                self._log.error(
                    f"Unsupported order type: {order.order_type}. "
                    f"Finam currently supports MARKET and LIMIT only."
                )
                self.generate_order_rejected(
                    strategy_id=order.strategy_id,
                    instrument_id=order.instrument_id,
                    client_order_id=order.client_order_id,
                    reason=f"Unsupported order type: {order.order_type}",
                    ts_event=self._clock.timestamp_ns(),
                )

        except Exception as e:
            self._log.error(f"Failed to submit order {order.client_order_id}: {self._format_grpc_error(e)}")
            self.generate_order_rejected(
                strategy_id=order.strategy_id,
                instrument_id=order.instrument_id,
                client_order_id=order.client_order_id,
                reason=str(self._format_grpc_error(e)),
                ts_event=self._clock.timestamp_ns(),
            )

    async def _submit_market_order(self, order: MarketOrder) -> None:
        """Submit a market order via PlaceOrder()."""
        metadata = await self._client.get_metadata()

        finam_symbol = self._get_finam_symbol(order.instrument_id)

        finam_order = FinamOrder(
            account_id=self._finam_account_id,
            symbol=finam_symbol,
            quantity=self._quantity_to_decimal(order.quantity),
            side=self._map_order_side(order.side),
            type=FinamOrderType.ORDER_TYPE_MARKET,
            time_in_force=FinamTimeInForce.TIME_IN_FORCE_DAY,
            client_order_id=self._to_finam_client_order_id(order.client_order_id),
        )

        response = await self._client.orders.PlaceOrder(finam_order, metadata=metadata)

        # Track venue_order_id → client_order_id mapping
        venue_order_id = VenueOrderId(response.order_id)
        self._venue_order_id_to_client_order_id[venue_order_id] = order.client_order_id
        self._client_to_venue_order_id[order.client_order_id] = venue_order_id

        self._log.info(f"Market order submitted: {response.order_id}")

    async def _submit_limit_order(self, order: LimitOrder) -> None:
        """Submit a limit order via PlaceOrder()."""
        metadata = await self._client.get_metadata()

        finam_symbol = self._get_finam_symbol(order.instrument_id)

        finam_order = FinamOrder(
            account_id=self._finam_account_id,
            symbol=finam_symbol,
            quantity=self._quantity_to_decimal(order.quantity),
            side=self._map_order_side(order.side),
            type=FinamOrderType.ORDER_TYPE_LIMIT,
            time_in_force=FinamTimeInForce.TIME_IN_FORCE_DAY,
            limit_price=self._price_to_decimal(order.price),
            client_order_id=self._to_finam_client_order_id(order.client_order_id),
        )

        response = await self._client.orders.PlaceOrder(finam_order, metadata=metadata)

        # Track venue_order_id → client_order_id mapping
        venue_order_id = VenueOrderId(response.order_id)
        self._venue_order_id_to_client_order_id[venue_order_id] = order.client_order_id
        self._client_to_venue_order_id[order.client_order_id] = venue_order_id

        self._log.info(f"Limit order submitted: {response.order_id}")

    async def _cancel_order(self, command: CancelOrder) -> None:
        """
        Cancel an order via gRPC CancelOrder().

        Parameters
        ----------
        command : CancelOrder
            The cancel order command

        """
        try:
            # Need venue_order_id to cancel
            if not command.venue_order_id:
                self._log.error(f"Cannot cancel order without venue_order_id: {command.client_order_id}")
                return

            metadata = await self._client.get_metadata()

            request = CancelOrderRequest(
                account_id=self._finam_account_id,
                order_id=command.venue_order_id.value,
            )

            response = await self._client.orders.CancelOrder(request, metadata=metadata)
            self._log.info(f"Order cancel requested: {command.venue_order_id}")

        except Exception as e:
            self._log.error(f"Failed to cancel order {command.venue_order_id}: {e}")
            self.generate_order_cancel_rejected(
                strategy_id=command.strategy_id,
                instrument_id=command.instrument_id,
                client_order_id=command.client_order_id,
                venue_order_id=command.venue_order_id,
                reason=str(e),
                ts_event=self._clock.timestamp_ns(),
            )

    async def _cancel_all_orders(self, command: CancelAllOrders) -> None:
        """Cancel all open orders (not directly supported by Finam - cancel individually)."""
        # Finam doesn't have CancelAllOrders - must cancel one-by-one
        open_orders = self._cache.orders_open(instrument_id=command.instrument_id)

        for order in open_orders:
            if order.venue_order_id:
                cancel_command = CancelOrder(
                    trader_id=command.trader_id,
                    strategy_id=command.strategy_id,
                    instrument_id=order.instrument_id,
                    client_order_id=order.client_order_id,
                    venue_order_id=order.venue_order_id,
                    command_id=UUID4(),
                    ts_init=self._clock.timestamp_ns(),
                )
                await self._cancel_order(cancel_command)

    async def _modify_order(self, command: ModifyOrder) -> None:
        """Modify order is not supported by Finam gRPC API."""
        self._log.warning("Order modification not supported by Finam - cancel and resubmit instead")
        # TODO: Implement cancel-replace pattern if needed

    # -- EXECUTION REPORTS ------------------------------------------------------------------------

    async def generate_order_status_report(
        self,
        command: GenerateOrderStatusReport,
    ) -> OrderStatusReport | None:
        """
        Generate an order status report via GetOrder().

        Parameters
        ----------
        command : GenerateOrderStatusReport
            The generate order status report command

        Returns
        -------
        OrderStatusReport | None

        """
        try:
            # Resolve venue order id
            venue_order_id = command.venue_order_id
            if not venue_order_id and command.client_order_id in self._client_to_venue_order_id:
                venue_order_id = self._client_to_venue_order_id.get(command.client_order_id)

            if not venue_order_id:
                self._log.warning(
                    f"Cannot query status: no venue_order_id for {command.client_order_id}"
                )
                return None

            metadata = await self._client.get_metadata()
            request = GetOrderRequest(
                account_id=self._finam_account_id,
                order_id=venue_order_id.value,
            )
            order_state = await self._client.orders.GetOrder(request, metadata=metadata)

            symbol = getattr(order_state.order, "symbol", "")
            instrument_id = self._get_cached_instrument_id(symbol)

            parsed = parse_order_state(
                order_state=order_state,
                account_id=self.account_id,
                instrument_id=instrument_id,
                ts_init=self._clock.timestamp_ns(),
            )

            # Map Finam client_order_id back to original if it was sanitized
            client_oid = parsed.get("client_order_id") or command.client_order_id
            mapped = None
            if client_oid and client_oid.value in self._finam_to_client_order_id:
                mapped = self._finam_to_client_order_id.get(client_oid.value)
            parsed["client_order_id"] = mapped or client_oid

            status_name = None
            try:
                # OrderState.status is an enum int; decode to name for logging
                from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.orders.orders_service_pb2 import (
                    OrderStatus as FinamOrderStatus,
                )
                status_name = FinamOrderStatus.Name(order_state.status)
            except Exception:
                status_name = str(order_state.status)

            # Build OrderStatusReport with available fields; fallback defaults for missing data
            qty = parsed["quantity"]
            filled_qty = qty if parsed["order_status"] == OrderStatus.FILLED else Quantity.zero()

            # Approximate avg_px: use limit_price if present, otherwise last cached bar close, else 0
            avg_px_decimal: Decimal | None = None
            if parsed.get("limit_price"):
                try:
                    avg_px_decimal = Decimal(str(parsed["limit_price"].value))
                except Exception:
                    avg_px_decimal = None
            if avg_px_decimal is None:
                try:
                    last_bar = self._cache.bar_latest(instrument_id)
                    if last_bar:
                        avg_px_decimal = Decimal(str(last_bar.close.value))
                except Exception:
                    avg_px_decimal = None
            if avg_px_decimal is None:
                avg_px_decimal = Decimal("0")

            report = OrderStatusReport(
                account_id=self.account_id,
                instrument_id=instrument_id,
                venue_order_id=parsed["venue_order_id"],
                order_side=parsed["side"],
                order_type=OrderType.MARKET,  # Finam GetOrder does not return type mapping here; assume MARKET
                time_in_force=TimeInForce.DAY,  # Finam currently submits DAY
                order_status=parsed["order_status"],
                quantity=qty,
                filled_qty=filled_qty,
                report_id=UUID4(),  # unique report id
                ts_accepted=parsed["ts_accepted"] or parsed["ts_event"],
                ts_last=parsed["ts_event"],
                ts_init=parsed["ts_init"],
                client_order_id=parsed["client_order_id"] or command.client_order_id,
                avg_px=avg_px_decimal,
            )

            self._log.info(
                f"GetOrder status {status_name or parsed['order_status']} "
                f"for {report.client_order_id} ({symbol}) venue_id={venue_order_id.value}"
            )

            return report

        except Exception as e:
            self._log.error(f"Failed to generate order status report: {self._format_grpc_error(e)}")
            return None

    async def generate_order_status_reports(
        self,
        command: GenerateOrderStatusReports,
    ) -> list[OrderStatusReport]:
        """Generate order status reports via Orders(). Finam has no filter, so return empty."""
        return []

    async def generate_fill_reports(
        self,
        command: GenerateFillReports,
    ) -> list[FillReport]:
        """Generate fill reports via Trades()."""
        # TODO: Implement Trades() call and parsing
        self._log.warning("generate_fill_reports not yet implemented")
        return []

    # -- HELPER METHODS ---------------------------------------------------------------------------

    def _get_cached_instrument_id(self, symbol: str) -> InstrumentId:
        """
        Get or create cached InstrumentId for symbol.

        Parameters
        ----------
        symbol : str
            The Finam symbol

        Returns
        -------
        InstrumentId

        """
        instrument_id: InstrumentId | None = self._instrument_ids.get(symbol)
        if not instrument_id:
            # Normalize Finam symbol (@) to Nautilus format (-) and try cache/provider
            from nautilus_trader.model.identifiers import Venue
            nautilus_symbol = symbol.replace("@", "-")
            instrument = self._cache.instrument(InstrumentId(Symbol(nautilus_symbol), Venue("FINAM")))
            if instrument is None:
                instrument = self._instrument_provider.find(symbol=Symbol(nautilus_symbol))
            if instrument:
                instrument_id = instrument.id
            else:
                # Create placeholder InstrumentId (venue will be set later)
                # In production, this should trigger instrument loading
                instrument_id = InstrumentId(Symbol(nautilus_symbol), Venue("FINAM"))
                self._log.warning(
                    f"Instrument {symbol} not found in provider, created placeholder {instrument_id}"
                )
            self._instrument_ids[symbol] = instrument_id
        return instrument_id

    def _find_instrument(self, instrument_id: InstrumentId):
        """Resolve instrument from cache first, then provider."""
        instrument = self._cache.instrument(instrument_id)
        if instrument:
            return instrument
        # Try alternate symbol format (swap @ and -)
        from nautilus_trader.model.identifiers import Venue
        sym_val = instrument_id.symbol.value
        alt_symbol = sym_val.replace("@", "-") if "@" in sym_val else sym_val.replace("-", "@")
        alt_id = InstrumentId(Symbol(alt_symbol), Venue("FINAM"))
        instrument = self._cache.instrument(alt_id)
        if instrument:
            return instrument
        return self._instrument_provider.find(instrument_id=instrument_id)

    def _get_finam_symbol(self, instrument_id: InstrumentId) -> str:
        """
        Return the Finam-formatted symbol for order submission.

        Preference:
        1) instrument.raw_symbol if available (usually already contains '@')
        2) convert Nautilus symbol (with '-') to Finam symbol (with '@')
        """
        instrument = self._find_instrument(instrument_id)
        if instrument and getattr(instrument, "raw_symbol", None):
            return instrument.raw_symbol.value

        return to_finam_symbol(instrument_id.symbol.value)

    def _to_finam_client_order_id(self, client_order_id: ClientOrderId) -> str:
        """
        Ensure client_order_id obeys Finam limit (<=20 chars) and keep mapping.

        Sanitizes to allowed chars (letters/numbers/space) and shortens to 20 chars max.
        Strategy:
        - strip non-alphanumeric characters
        - if still too long, keep head+tail
        - always record mapping for reverse lookup
        """
        raw = client_order_id.value
        sanitized = "".join(ch for ch in raw if ch.isalnum())

        if not sanitized:
            # Fallback to timestamp-based ID if everything was stripped
            ts_suffix = str(self._clock.timestamp_ns())[-12:]
            sanitized = f"COID{ts_suffix}"

        if len(sanitized) > 20:
            sanitized = f"{sanitized[:6]}{sanitized[-14:]}"
            if len(sanitized) > 20:
                sanitized = sanitized[-20:]

        self._finam_to_client_order_id[sanitized] = client_order_id
        self._client_to_finam_order_id[client_order_id] = sanitized
        return sanitized

    def _format_grpc_error(self, exc: Exception) -> str:
        """
        Decode gRPC errors so non-ASCII messages (e.g., Russian) are readable.
        """
        try:
            if isinstance(exc, grpc.aio.AioRpcError):
                details = exc.details() or str(exc)
                return details
        except Exception:
            pass
        return str(exc)

    def _map_order_side(self, side: OrderSide) -> FinamSide:
        """Map Nautilus OrderSide to Finam Side."""
        if side == OrderSide.BUY:
            return FinamSide.SIDE_BUY
        elif side == OrderSide.SELL:
            return FinamSide.SIDE_SELL
        else:
            raise ValueError(f"Invalid OrderSide: {side}")

    def _quantity_to_decimal(self, quantity: Any) -> Any:
        """Convert Nautilus Quantity to Protobuf Decimal."""
        # TODO: Implement proper conversion to google.type.Decimal
        from google.type.decimal_pb2 import Decimal as ProtoDecimal
        return ProtoDecimal(value=str(quantity))

    def _price_to_decimal(self, price: Any) -> Any:
        """Convert Nautilus Price to Protobuf Decimal."""
        from google.type.decimal_pb2 import Decimal as ProtoDecimal
        return ProtoDecimal(value=str(price))
