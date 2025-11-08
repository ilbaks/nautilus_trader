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
Provides a historical data client for the Finam exchange for backtesting.
"""

import asyncio
from datetime import datetime
from typing import Any

from nautilus_trader.adapters.finam.grpc.client.client import FinamGrpcClient
from nautilus_trader.adapters.finam.grpc.common.enums import TimeFrame
from nautilus_trader.adapters.finam.grpc.parsing.market_data import parse_historical_bar
from nautilus_trader.adapters.finam.grpc.streams.bars import BarsStreamManager
from nautilus_trader.adapters.finam.providers import FinamInstrumentProvider
from nautilus_trader.common.component import LiveClock
from nautilus_trader.common.component import Logger
from nautilus_trader.common.component import init_logging
from nautilus_trader.common.component import log_level_from_str
from nautilus_trader.config import InstrumentProviderConfig
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarAggregation
from nautilus_trader.model.data import BarSpecification
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import AggregationSource
from nautilus_trader.model.enums import PriceType
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import Symbol
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.model.instruments import FuturesContract
from nautilus_trader.model.objects import Price
from nautilus_trader.model.objects import Quantity


def _normalize_instrument_id(instrument: Instrument) -> Instrument:
    """
    Create a copy of instrument with normalized ID (@ → -).

    Nautilus automatically converts @ → - in bar_type when saving to catalog,
    so instruments should also use `-` for consistency.

    Parameters
    ----------
    instrument : Instrument
        Original instrument (may contain @ in symbol)

    Returns
    -------
    Instrument
        New instrument with normalized symbol (with -)
    """
    # Only normalize FuturesContract (other instrument types handled as needed)
    if not isinstance(instrument, FuturesContract):
        return instrument

    # Normalize symbol and raw_symbol: @ → -
    normalized_symbol_str = str(instrument.id.symbol).replace("@", "-")
    normalized_symbol = Symbol(normalized_symbol_str)

    normalized_raw_symbol_str = str(instrument.raw_symbol).replace("@", "-")
    normalized_raw_symbol = Symbol(normalized_raw_symbol_str)

    # Create new InstrumentId with normalized symbol
    normalized_id = InstrumentId(symbol=normalized_symbol, venue=instrument.id.venue)

    # Create new FuturesContract with normalized ID
    return FuturesContract(
        instrument_id=normalized_id,
        raw_symbol=normalized_raw_symbol,
        asset_class=instrument.asset_class,
        currency=instrument.quote_currency,
        price_precision=instrument.price_precision,
        price_increment=instrument.price_increment,
        multiplier=instrument.multiplier,
        lot_size=instrument.lot_size,
        underlying=instrument.underlying,
        activation_ns=instrument.activation_ns,
        expiration_ns=instrument.expiration_ns,
        ts_event=instrument.ts_event,
        ts_init=instrument.ts_init,
        margin_init=instrument.margin_init,
        margin_maint=instrument.margin_maint,
        maker_fee=instrument.maker_fee if hasattr(instrument, 'maker_fee') else None,
        taker_fee=instrument.taker_fee if hasattr(instrument, 'taker_fee') else None,
        exchange=instrument.exchange if hasattr(instrument, 'exchange') else None,
        tick_scheme_name=instrument.tick_scheme_name if hasattr(instrument, 'tick_scheme_name') else None,
        info=instrument.info if hasattr(instrument, 'info') else None,
    )


class HistoricFinamClient:
    """
    Provides a means of requesting historical market data from Finam for backtesting.

    This client encapsulates all complexity of working with Finam gRPC API for historical
    data requests, providing a clean, high-level interface similar to the Interactive
    Brokers historical client.

    Features:
    - Automatic chunking for large date ranges (respects API limits)
    - Proper parsing from protobuf → Nautilus Bar objects
    - Built-in Clock management for ts_init generation
    - Integration with FinamInstrumentProvider
    - Comprehensive error handling and logging

    Parameters
    ----------
    access_token : str
        The Finam API access token for authentication.
    client_id : int, default 1
        The client ID for gRPC connection.
    log_level : str, default "INFO"
        The logging level ("DEBUG", "INFO", "WARNING", "ERROR").

    Examples
    --------
    >>> import asyncio
    >>> from datetime import datetime
    >>> from nautilus_trader.adapters.finam.historical import HistoricFinamClient
    >>> from nautilus_trader.persistence.catalog import ParquetDataCatalog
    >>>
    >>> async def main():
    ...     # Create client
    ...     client = HistoricFinamClient(
    ...         access_token="your_token_here",
    ...         client_id=1,
    ...     )
    ...     await client.connect()
    ...
    ...     # Request bars
    ...     bars = await client.request_bars(
    ...         bar_specifications=["1-MINUTE-LAST"],
    ...         start_date_time=datetime(2024, 1, 1),
    ...         end_date_time=datetime(2024, 1, 7),
    ...         contracts=[{"symbol": "SiZ5@RTSX", "name": "Si декабрь 2025"}],
    ...     )
    ...
    ...     # Save to catalog
    ...     catalog = ParquetDataCatalog("./catalog")
    ...     catalog.write_data(bars)
    ...
    >>> asyncio.run(main())

    """

    def __init__(
        self,
        access_token: str,
        client_id: int = 1,
        log_level: str = "INFO",
    ) -> None:
        # Initialize clock for ts_init generation
        self._clock = LiveClock()

        # Initialize logging
        self._log_guard = init_logging(level_stdout=log_level_from_str(log_level))
        self.log = Logger(name="HistoricFinamClient")

        # Create gRPC client
        self._client = FinamGrpcClient(
            client_id=str(client_id),
            access_token=access_token,
        )

        # Stream managers (will be initialized after connect)
        self._bars_stream: BarsStreamManager | None = None

        # Instrument provider (will be initialized after connect)
        self._instrument_provider: FinamInstrumentProvider | None = None

        # Cache for normalized instruments (@ → -)
        self._normalized_instruments_cache: dict[str, Instrument] = {}

        self.log.info(
            f"HistoricFinamClient initialized (client_id={client_id}, log_level={log_level})"
        )

    async def connect(self) -> None:
        """
        Establish connection to Finam gRPC API.

        Raises
        ------
        ConnectionError
            If connection fails.

        """
        try:
            self.log.info("Connecting to Finam gRPC API...")
            await self._client.connect()

            # Initialize stream managers
            self._bars_stream = BarsStreamManager(
                client=self._client,
                logger=self.log,
            )

            # Initialize instrument provider
            self._instrument_provider = FinamInstrumentProvider(
                client=self._client,
                clock=self._clock,
                config=InstrumentProviderConfig(),
            )

            self.log.info("✅ Connected to Finam gRPC API")

        except Exception as e:
            self.log.error(f"Failed to connect to Finam API: {e}")
            raise ConnectionError(f"Failed to connect to Finam API: {e}") from e

    async def disconnect(self) -> None:
        """
        Close connection to Finam gRPC API.
        """
        try:
            self.log.info("Disconnecting from Finam gRPC API...")
            await self._client.disconnect()
            self.log.info("✅ Disconnected from Finam gRPC API")
        except Exception as e:
            self.log.error(f"Error during disconnect: {e}")

    async def request_instruments(
        self,
        contracts: list[dict[str, Any]] | None = None,
        instrument_ids: list[str] | None = None,
    ) -> list[Instrument]:
        """
        Request instruments from Finam API.

        Parameters
        ----------
        contracts : list[dict[str, Any]], optional
            List of contract dictionaries with 'symbol' and 'name' keys.
            Example: [{"symbol": "SiZ5@RTSX", "name": "Si декабрь 2025"}]
        instrument_ids : list[str], optional
            List of instrument ID strings (alternative to contracts).
            Example: ["SiZ5@RTSX.FINAM"]

        Returns
        -------
        list[Instrument]
            List of Nautilus Instrument objects.

        Raises
        ------
        ValueError
            If neither contracts nor instrument_ids provided.
        RuntimeError
            If not connected or instrument provider not initialized.

        """
        if self._instrument_provider is None:
            raise RuntimeError(
                "Not connected. Call connect() before request_instruments()"
            )

        if not contracts and not instrument_ids:
            raise ValueError("Either contracts or instrument_ids must be provided")

        self.log.info(
            f"Requesting instruments (contracts={len(contracts or [])}, "
            f"instrument_ids={len(instrument_ids or [])})"
        )

        # Build list of InstrumentId objects from contracts/instrument_ids
        venue = Venue("FINAM")
        ids_to_load: list[InstrumentId] = []

        # Process contracts
        if contracts:
            for contract in contracts:
                if not isinstance(contract, dict):
                    self.log.warning(f"Skipping invalid contract (not dict): {contract}")
                    continue

                if "symbol" not in contract:
                    self.log.warning(f"Skipping contract without 'symbol': {contract}")
                    continue

                symbol_str = contract["symbol"]
                # Keep original symbol with @ for provider lookup
                instrument_id = InstrumentId(Symbol(symbol_str), venue)
                ids_to_load.append(instrument_id)

        # Process instrument_ids
        if instrument_ids:
            for id_str in instrument_ids:
                try:
                    # Parse instrument ID string (e.g., "SiZ5-RTSX.FINAM")
                    instrument_id = InstrumentId.from_str(id_str)
                    ids_to_load.append(instrument_id)
                except Exception as e:
                    self.log.warning(f"Failed to parse instrument_id '{id_str}': {e}")
                    continue

        if not ids_to_load:
            self.log.warning("No valid instrument IDs to load")
            return []

        self.log.info(f"Loading {len(ids_to_load)} instruments from Finam API...")

        # Load instruments using FinamInstrumentProvider.load_ids_async()
        await self._instrument_provider.load_ids_async(instrument_ids=ids_to_load)

        # Get all loaded instruments
        instruments = self._instrument_provider.list_all()
        self.log.info(f"Provider returned {len(instruments)} instruments with IDs: {[str(i.id) for i in instruments]}")

        # Normalize instrument IDs (@ → -) for catalog consistency
        normalized_instruments = [_normalize_instrument_id(inst) for inst in instruments]
        self.log.info(f"Normalized to: {[str(i.id) for i in normalized_instruments]}")

        # Cache normalized instruments for later use in request_bars()
        for norm_inst in normalized_instruments:
            cache_key = str(norm_inst.id)
            self._normalized_instruments_cache[cache_key] = norm_inst
            self.log.debug(f"Cached instrument: {cache_key}")

        self.log.info(f"✅ Loaded {len(normalized_instruments)} instruments")

        return normalized_instruments

    async def request_bars(
        self,
        bar_specifications: list[str],
        start_date_time: datetime,
        end_date_time: datetime,
        contracts: list[dict[str, Any]] | None = None,
        instrument_ids: list[str] | None = None,
        chunk_days: int = 7,
    ) -> list[Bar]:
        """
        Request historical bars from Finam API.

        Automatically handles:
        - Chunking for large date ranges (respects API limits)
        - Parsing from protobuf → Nautilus Bar objects
        - Monotonic ts_init generation using Clock
        - Error handling and retries

        Parameters
        ----------
        bar_specifications : list[str]
            Bar specifications as strings (e.g., ["1-MINUTE-LAST", "5-MINUTE-LAST"]).
        start_date_time : datetime
            Start date/time for historical data (timezone-aware recommended).
        end_date_time : datetime
            End date/time for historical data (timezone-aware recommended).
        contracts : list[dict[str, Any]], optional
            List of contract dictionaries with 'symbol' and 'name' keys.
        instrument_ids : list[str], optional
            List of instrument ID strings (alternative to contracts).
        chunk_days : int, default 7
            Size of chunks in days for splitting large requests.
            Default 7 is optimal for M1 timeframe (respects 30-day API limit).

        Returns
        -------
        list[Bar]
            Historical bars sorted by ts_event, ready for ParquetDataCatalog.

        Raises
        ------
        ValueError
            If parameters invalid or neither contracts/instrument_ids provided.
        RuntimeError
            If not connected or required components not initialized.

        Examples
        --------
        >>> bars = await client.request_bars(
        ...     bar_specifications=["1-MINUTE-LAST"],
        ...     start_date_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ...     end_date_time=datetime(2024, 1, 7, tzinfo=timezone.utc),
        ...     contracts=[{"symbol": "SiZ5@RTSX", "name": "Si Dec 2025"}],
        ...     chunk_days=7,
        ... )
        >>> print(f"Loaded {len(bars)} bars")

        """
        if self._bars_stream is None or self._instrument_provider is None:
            raise RuntimeError("Not connected. Call connect() before request_bars()")

        if not contracts and not instrument_ids:
            raise ValueError("Either contracts or instrument_ids must be provided")

        if start_date_time >= end_date_time:
            raise ValueError("start_date_time must be before end_date_time")

        self.log.info(
            f"Requesting bars: {len(bar_specifications)} specs, "
            f"{start_date_time} → {end_date_time}, "
            f"chunk_days={chunk_days}"
        )

        # Ensure we have contracts to process
        contracts = contracts or []
        instrument_ids_list = instrument_ids or []

        all_bars: list[Bar] = []
        venue = Venue("FINAM")  # Finam venue

        # Process each contract
        for contract in contracts:
            # Validate contract format
            if not isinstance(contract, dict):
                self.log.error(f"Contract must be dict, got {type(contract)}")
                continue

            if "symbol" not in contract:
                self.log.error(f"Contract missing 'symbol' field: {contract}")
                continue

            symbol_str = contract["symbol"]
            self.log.info(f"Processing contract: {symbol_str}")

            # Process each bar specification
            for bar_spec_str in bar_specifications:
                try:
                    # Parse bar specification
                    bar_spec = BarSpecification.from_str(bar_spec_str)

                    # Create instrument ID (convert @ to - for Nautilus format)
                    nautilus_symbol = symbol_str.replace("@", "-")
                    instrument_id = InstrumentId(Symbol(nautilus_symbol), venue)

                    # Create bar type
                    bar_type = BarType(
                        instrument_id=instrument_id,
                        bar_spec=bar_spec,
                        aggregation_source=AggregationSource.EXTERNAL,
                    )

                    # Map bar specification to Finam TimeFrame
                    timeframe = self._bar_spec_to_timeframe(bar_spec)

                    self.log.debug(
                        f"Loading {bar_spec_str} for {symbol_str} "
                        f"(timeframe={timeframe.name})"
                    )

                    # Request historical bars from Finam API
                    proto_bars = await self._bars_stream.request_historical_bars(
                        symbol=symbol_str,
                        timeframe=timeframe,
                        start_time=start_date_time,
                        end_time=end_date_time,
                        chunk_days=chunk_days,
                    )

                    self.log.info(
                        f"Received {len(proto_bars)} protobuf bars for {symbol_str} {bar_spec_str}"
                    )

                    # Get price_precision from cached normalized instrument
                    # IMPORTANT: Instrument must be loaded first via request_instruments()
                    cache_key = str(instrument_id)
                    normalized_instrument = self._normalized_instruments_cache.get(cache_key)

                    if normalized_instrument is None:
                        self.log.error(
                            f"Instrument {instrument_id} not found in cache. "
                            f"Call request_instruments() first to load metadata."
                        )
                        continue

                    price_precision = normalized_instrument.price_precision

                    # Parse protobuf bars to Nautilus Bar objects
                    for proto_bar in proto_bars:
                        ts_init = self._clock.timestamp_ns()
                        bar = parse_historical_bar(
                            proto_bar=proto_bar,
                            instrument_id=instrument_id,
                            bar_type=bar_type,
                            price_precision=price_precision,
                            ts_init=ts_init,
                        )
                        all_bars.append(bar)

                except Exception as e:
                    self.log.error(
                        f"Error loading bars for {symbol_str} {bar_spec_str}: {e}",
                        exc_info=True,
                    )
                    continue

        # Sort bars by ts_event for proper chronological ordering
        all_bars.sort(key=lambda b: b.ts_event)

        self.log.info(
            f"✅ Total bars loaded: {len(all_bars)} "
            f"({len(contracts)} contracts × {len(bar_specifications)} specs)"
        )

        return all_bars

    def _bar_spec_to_timeframe(self, bar_spec: BarSpecification) -> TimeFrame:
        """
        Convert Nautilus BarSpecification to Finam TimeFrame enum.

        Parameters
        ----------
        bar_spec : BarSpecification
            Nautilus bar specification.

        Returns
        -------
        TimeFrame
            Corresponding Finam TimeFrame enum value.

        Raises
        ------
        ValueError
            If bar specification is not supported.

        """
        # Map based on aggregation type and step
        if bar_spec.aggregation == BarAggregation.MINUTE:
            if bar_spec.step == 1:
                return TimeFrame.M1
            elif bar_spec.step == 5:
                return TimeFrame.M5
            elif bar_spec.step == 15:
                return TimeFrame.M15
            elif bar_spec.step == 30:
                return TimeFrame.M30
        elif bar_spec.aggregation == BarAggregation.HOUR:
            if bar_spec.step == 1:
                return TimeFrame.H1
            elif bar_spec.step == 2:
                return TimeFrame.H2
            elif bar_spec.step == 4:
                return TimeFrame.H4
            elif bar_spec.step == 8:
                return TimeFrame.H8
        elif bar_spec.aggregation == BarAggregation.DAY:
            if bar_spec.step == 1:
                return TimeFrame.D
        elif bar_spec.aggregation == BarAggregation.WEEK:
            if bar_spec.step == 1:
                return TimeFrame.W
        elif bar_spec.aggregation == BarAggregation.MONTH:
            if bar_spec.step == 1:
                return TimeFrame.MN

        # Unsupported specification
        raise ValueError(
            f"Unsupported bar specification: {bar_spec}. "
            f"Supported: 1/5/15/30-MINUTE, 1/2/4/8-HOUR, 1-DAY, 1-WEEK, 1-MONTH"
        )
