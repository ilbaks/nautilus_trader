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
#%%
from nautilus_trader.adapters.finam.grpc.client.client import FinamGrpcClient
from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.assets.assets_service_pb2 import (
    AssetsRequest,
    GetAssetRequest,
)
from nautilus_trader.adapters.finam.parsing.instruments import parse_instrument
from nautilus_trader.adapters.finam.parsing.specs import parse_instrument_specs
from nautilus_trader.common.component import Clock
from nautilus_trader.common.providers import InstrumentProvider
from nautilus_trader.config import InstrumentProviderConfig
from nautilus_trader.core.correctness import PyCondition
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.objects import Quantity
import os
#%%

class FinamInstrumentProvider(InstrumentProvider):
    """
    Provides instruments from Finam Trade API via gRPC.

    Parameters
    ----------
    client : FinamGrpcClient
        The Finam gRPC client.
    clock : Clock
        The clock from timestamp generation.
    config : InstrumentProviderConfig, optional
        The instrument provider configuration.
    """

    def __init__(
        self,
        client: FinamGrpcClient,
        clock: Clock,
        config: InstrumentProviderConfig | None = None,
        account_id: str | None = None,
    ) -> None:
        super().__init__(config=config)

        self._client = client
        self._clock = clock
        self._account_id = account_id or os.getenv("FINAM_ACCOUNT_ID")
        
    async def load_all_async(
        self,
        filters: dict | None = None,
    ) -> None:
        """
        Load all instruments from Finam API via gRPC AssetsService.Assets().

        Parameters
        ----------
        filters : dict, optional
            Currently not used (reserved for future filtering)
        """
        self._log.info("Loading all instruments from Finam gRPC API...")

        try:
            # Ensure the gRPC client has an active channel before requesting metadata
            await self._client.connect()

            # Call gRPC AssetsService.Assets()
            request = AssetsRequest()
            metadata = await self._client.get_metadata()
            response = await self._client.assets.Assets(request, metadata=metadata)

            # Parse each Protobuf Asset -> Nautilus Instrument
            ts_init = self._clock.timestamp_ns()

            parsed_count = 0
            error_count = 0

            for protobuf_asset in response.assets:
                try:
                    nautilus_instrument = parse_instrument(
                        finam_asset=protobuf_asset,
                        ts_init=ts_init,
                    )

                    # Add to provider cache
                    self.add(nautilus_instrument)
                    parsed_count += 1

                except Exception as e:
                    error_count += 1
                    # Protobuf Asset has 'code' field (not 'symbol')
                    asset_code = getattr(protobuf_asset, 'code', 'UNKNOWN')
                    self._log.error(
                        f"Failed to parse instrument {asset_code}: {e}"
                    )

            self._log.info(
                f"Loaded {self.count} instruments "
                f"(parsed: {parsed_count}, errors: {error_count})"
            )

        except Exception as e:
            self._log.error(f"Failed to load instruments from Finam gRPC API: {e}")
            raise
    
    async def load_ids_async(
        self,
        instrument_ids: list[InstrumentId],
        filters: dict | None = None,
    ) -> None:
        """
        Load specific instruments by IDs with detailed specifications.

        This method loads precise trading parameters (lot_size, multiplier, price_increment)
        by calling GetAsset() for each requested instrument.

        Parameters
        ----------
        instrument_ids : list[InstrumentId]
            The instrument IDs to load
        filters : dict, optional
            Currently not used

        Symbol Format Handling
        ----------------------
        Supports both Nautilus format (with -) and Finam API format (with @):
        - Nautilus: "SiZ5-RTSX.FINAM"
        - Finam API: "SiZ5@RTSX"

        When filtering, we normalize symbols to support both formats.
        """
        PyCondition.not_none(instrument_ids, "instrument_ids")
        PyCondition.not_empty(instrument_ids, "instrument_ids")

        self._log.info(f"Loading {len(instrument_ids)} instruments with detailed specs...")

        # Step 1: Load all instruments (basic info) via Assets()
        await self.load_all_async(filters)

        # Step 2: Filter requested instruments
        # ВАЖНО: Поддерживаем оба формата символов (@ и -)
        # API возвращает "SiZ5@RTSX", мы запрашиваем "SiZ5-RTSX"
        requested_symbols = {instrument_id.symbol.value for instrument_id in instrument_ids}

        # Создаем set со всеми вариантами символов (@ и -)
        requested_symbols_normalized = set()
        for symbol in requested_symbols:
            requested_symbols_normalized.add(symbol)  # Оригинальный формат
            requested_symbols_normalized.add(symbol.replace("-", "@"))  # Nautilus → Finam
            requested_symbols_normalized.add(symbol.replace("@", "-"))  # Finam → Nautilus

        # Find matching instruments
        matched_instruments = []
        all_ids = list(self._instruments.keys())
        for instrument_id in all_ids:
            if instrument_id.symbol.value in requested_symbols_normalized:
                matched_instruments.append(self._instruments[instrument_id])
            else:
                # Remove non-requested instruments
                del self._instruments[instrument_id]

        self._log.info(f"Found {len(matched_instruments)} matching instruments")

        # Step 3: Load detailed specs for each matched instrument via GetAsset()
        metadata = await self._client.get_metadata()
        ts_init = self._clock.timestamp_ns()

        for instrument in matched_instruments:
            try:
                # Convert symbol to Finam API format (with @)
                finam_symbol = str(instrument.id.symbol).replace("-", "@")

                self._log.debug(f"Loading specs for {finam_symbol}...")

                # Call GetAsset() to get detailed specifications
                # Note: account_id is required by Finam API
                account_id = self._account_id or self._client._client_id
                request = GetAssetRequest(symbol=finam_symbol, account_id=account_id)
                specs_response = await self._client.assets.GetAsset(request, metadata=metadata)

                # Parse specs
                specs = parse_instrument_specs(specs_response)

                # Extract expiration_ns from specs (for futures)
                # Finam API returns expiration_date in GetAssetResponse
                expiration_ns = instrument.expiration_ns  # fallback to original (+90 days)
                if specs.get('expiration_date'):
                    from datetime import timezone
                    expiry_dt = specs['expiration_date'].replace(tzinfo=timezone.utc)
                    expiration_ns = int(expiry_dt.timestamp() * 1_000_000_000)
                    self._log.info(f"   📅 Using API expiration: {specs['expiration_date'].date()}")
                else:
                    self._log.warning(f"   ⚠️ No expiration_date from API, using fallback (+90 days)")

                # Get original Asset from first load (needed for parse_instrument)
                # We need to call Assets() again or store the original asset
                # For now, we'll reconstruct from the instrument
                # But parse_instrument needs the original protobuf Asset...

                # Alternative: directly update instrument attributes
                # This is more efficient than recreating
                from nautilus_trader.model.instruments import FuturesContract

                if isinstance(instrument, FuturesContract):
                    # Moscow Exchange futures have standardized tick value conventions:
                    #
                    # STANDARD RULE (Мосбиржа):
                    # - Most futures have tick_value = 1 RUB (стоимость мин. шага = 1 ₽)
                    # - multiplier = tick_value / price_increment
                    #
                    # EXAMPLES FROM PROTO:
                    # 1. Si (USD/RUB): decimals=0, min_step=1
                    #    → price_increment = 1/1 = 1.0
                    #    → tick_value = 1 RUB
                    #    → multiplier = 1.0 / 1.0 = 1
                    #
                    # 2. CR (CNY/RUB): decimals=3, min_step=1
                    #    → price_increment = 1/1000 = 0.001
                    #    → tick_value = 1 RUB (0.001 × 1000 lot_size)
                    #    → multiplier = 1.0 / 0.001 = 1000 = lot_size
                    #
                    # 3. SBRF (акции): decimals=0, min_step=1
                    #    → price_increment = 1.0
                    #    → tick_value = 1 RUB
                    #    → multiplier = 1.0 / 1.0 = 1
                    #
                    # This formula works universally when tick_value = 1 RUB (Мосбиржа standard)
                    from decimal import Decimal

                    # Standard tick value for Moscow Exchange = 1 RUB
                    # (for most instruments: Si, CR, SBRF, etc.)
                    tick_value_rub = Decimal("1.0")

                    # Calculate multiplier from tick value and price increment
                    # multiplier = tick_value / price_increment
                    price_inc_decimal = Decimal(str(specs['price_increment']))
                    multiplier_decimal = tick_value_rub / price_inc_decimal

                    # Convert to Quantity with appropriate precision
                    # For integer multipliers (1, 1000), use precision=0
                    # For fractional multipliers (0.02 for RTS), use higher precision
                    if multiplier_decimal == multiplier_decimal.to_integral_value():
                        # Integer multiplier
                        multiplier = Quantity.from_int(int(multiplier_decimal))
                        multiplier_precision = 0
                    else:
                        # Fractional multiplier (e.g., RTS: 0.02)
                        multiplier_str = str(multiplier_decimal)
                        multiplier_precision = len(multiplier_str.split('.')[-1]) if '.' in multiplier_str else 0
                        multiplier = Quantity(float(multiplier_decimal), multiplier_precision)

                    # Determine quoting type for logging
                    if specs['price_precision'] == 0:
                        quote_type = "contract"  # Цена за весь контракт
                    else:
                        quote_type = "base_unit"  # Цена за единицу базового актива

                    # Create updated instrument with real specs
                    updated_instrument = FuturesContract(
                        instrument_id=instrument.id,
                        raw_symbol=instrument.raw_symbol,
                        asset_class=instrument.asset_class,
                        currency=specs['currency'],
                        price_precision=specs['price_precision'],
                        price_increment=specs['price_increment'],
                        multiplier=multiplier,              # ✅ Depends on quoting method
                        lot_size=specs['lot_size'],         # ✅ Contract size from API
                        underlying=instrument.underlying,
                        activation_ns=instrument.activation_ns,
                        expiration_ns=expiration_ns,        # ✅ FIX: Real date from API
                        ts_event=ts_init,
                        ts_init=ts_init,
                        margin_init=instrument.margin_init,
                        margin_maint=instrument.margin_maint,
                    )

                    # Replace in cache
                    self._instruments[instrument.id] = updated_instrument
                    self._log.info(
                        f"✅ Updated {instrument.id}: lot_size={specs['lot_size']}, "
                        f"multiplier={multiplier} (quote_type={quote_type}), "
                        f"price_increment={specs['price_increment']}"
                    )
                else:
                    # For non-futures instruments, keep original for now
                    # TODO: Implement update logic for other instrument types
                    self._log.debug(f"Skipping spec update for non-futures: {instrument.id}")

            except Exception as e:
                self._log.warning(f"Failed to load specs for {instrument.id}: {e}")
                # Keep instrument with default values
                continue

        self._log.info(f"Loaded {self.count} instruments with detailed specs")

    async def load_async(
        self,
        instrument_id: InstrumentId,
        filters: dict | None = None,
    ) -> None:
        """
        Load a single instrument by ID.

        Parameters
        ----------
        instrument_id : InstrumentId
            The instrument ID to load
        filters : dict, optional
            Currently not used

        """
        PyCondition.not_none(instrument_id, "instrument_id")

        await self.load_ids_async([instrument_id], filters)
# %%
