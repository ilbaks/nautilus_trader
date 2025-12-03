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
from decimal import Decimal

from nautilus_trader.adapters.finam.common.constants import FINAM_VENUE
from nautilus_trader.adapters.finam.common.symbols import to_nautilus_symbol
from nautilus_trader.adapters.finam.common.enums import FinamInstrumentType
from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.assets.assets_service_pb2 import (
    Asset,
)
from nautilus_trader.core.correctness import PyCondition
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import Symbol
from nautilus_trader.model.enums import AssetClass
from nautilus_trader.model.instruments import Cfd
from nautilus_trader.model.instruments import CurrencyPair
from nautilus_trader.model.instruments import Equity
from nautilus_trader.model.instruments import FuturesContract
from nautilus_trader.model.instruments import FuturesSpread
from nautilus_trader.model.instruments import IndexInstrument
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.model.objects import Currency
from nautilus_trader.model.objects import Price
from nautilus_trader.model.objects import Quantity

#%%
def parse_instrument(
        finam_asset: Asset,
        ts_init: int,
        specs: dict | None = None,
        expiration_ns: int | None = None,
        activation_ns: int | None = None,
) -> Instrument:
    """
    Parse Finam Protobuf Asset to Nautilus Instrument.

    Maps Asset.type to appropriate Nautilus Instrument class:
    - EQUITIES → Equity
    - FUTURES → FuturesContract
    - CURRENCIES → CurrencyPair
    - SPREADS → FuturesSpread
    - INDICES → IndexInstrument
    - BONDS, FUNDS, SWAPS, OTHER → Cfd

    OsEngine Pattern: Fast load with defaults, then update with real specs:
    1. Initial load: parse_instrument(asset, ts_init) → defaults
    2. On subscribe: parse_instrument(asset, ts_init, specs) → real values

    Parameters
    ----------
    finam_asset : Asset
        Protobuf Asset message from gRPC AssetsService.Assets()
    ts_init : int
        Timestamp initialization (nanoseconds)
    specs : dict | None
        Optional parsed specifications from GetAssetResponse.
        If provided, uses real values. If None, uses defaults.
        Get via: parse_instrument_specs(get_asset_response)
    expiration_ns : int | None
        Optional expiration timestamp in nanoseconds for futures/spreads.
        If provided, overrides the default +90 days calculation.
        Use this when you have the real expiration date from external source.
    activation_ns : int | None
        Optional activation timestamp in nanoseconds for futures/spreads.
        If provided, overrides the default (0 for historical data).

    Returns
    -------
    Instrument
        Nautilus Instrument (Equity, FuturesContract, CurrencyPair, etc.)

    Examples
    --------
    # Stage 1: Fast load with defaults
    instrument = parse_instrument(asset, ts_init)

    # Stage 2: Update with real specs
    specs_response = await client.assets.GetAsset(...)
    specs = parse_instrument_specs(specs_response)
    instrument = parse_instrument(asset, ts_init, specs)

    # Stage 3: With explicit expiration date
    expiration_ns = int(expiry_datetime.timestamp() * 1_000_000_000)
    instrument = parse_instrument(asset, ts_init, specs, expiration_ns=expiration_ns)
    """
    PyCondition.not_none(finam_asset, "finam_asset")

    raw_symbol = Symbol(finam_asset.symbol)
    instrument_id = InstrumentId(
        symbol=Symbol(to_nautilus_symbol(finam_asset.symbol)),
        venue=FINAM_VENUE,
    )

    # Use specs if provided, otherwise use defaults
    from decimal import Decimal

    if specs is not None:
        # Real values from GetAssetResponse
        currency = specs['currency']
        price_precision = specs['price_precision']
        size_precision = specs['size_precision']
        price_increment = specs['price_increment']
        # size_increment must have same precision as size_precision
        size_increment = Quantity(1.0, size_precision)
        lot_size = specs['lot_size']
    else:
        # Default values for fast initial load
        currency = Currency.from_str("RUB")  # Default to RUB for Russian market
        price_precision = 2
        size_precision = 0
        price_increment = Price.from_str("0.01")
        size_increment = Quantity.from_int(1)
        lot_size = Quantity.from_int(1)

    # Map Asset.type to Nautilus Instrument class
    asset_type = finam_asset.type if hasattr(finam_asset, 'type') else 'OTHER'

    if asset_type == FinamInstrumentType.EQUITIES.value:
        return Equity(
            instrument_id=instrument_id,
            raw_symbol=raw_symbol,
            currency=currency,
            price_precision=price_precision,
            price_increment=price_increment,
            lot_size=lot_size,
            ts_event=ts_init,
            ts_init=ts_init,
        )

    elif asset_type == FinamInstrumentType.FUTURES.value:
        # Use provided values or calculate defaults
        # activation_ns: 0 for historical data (makes contract always active)
        # expiration_ns: use provided value or fallback to +90 days
        actual_activation_ns = activation_ns if activation_ns is not None else 0
        actual_expiration_ns = expiration_ns if expiration_ns is not None else (
            ts_init + (90 * 24 * 60 * 60 * 1_000_000_000)  # +90 days fallback
        )

        return FuturesContract(
            instrument_id=instrument_id,
            raw_symbol=raw_symbol,
            asset_class=AssetClass.COMMODITY,  # TODO: Determine from market/ticker
            currency=currency,
            price_precision=price_precision,
            price_increment=price_increment,
            multiplier=lot_size,
            lot_size=lot_size,
            underlying=finam_asset.ticker,  # Use ticker as underlying
            activation_ns=actual_activation_ns,
            expiration_ns=actual_expiration_ns,
            ts_event=ts_init,
            ts_init=ts_init,
        )

    elif asset_type == FinamInstrumentType.CURRENCIES.value:
        # Parse currency pair from symbol (e.g., "HKDRUB_TOM@MISX" -> HKD/RUB)
        base_currency, quote_currency = _parse_currency_pair(finam_asset.symbol)
        return CurrencyPair(
            instrument_id=instrument_id,
            raw_symbol=raw_symbol,
            base_currency=base_currency,
            quote_currency=quote_currency,
            price_precision=price_precision,
            size_precision=size_precision,
            price_increment=price_increment,
            size_increment=size_increment,
            lot_size=None,
            max_quantity=None,
            min_quantity=None,
            max_notional=None,
            min_notional=None,
            max_price=None,
            min_price=None,
            margin_init=Decimal(0),
            margin_maint=Decimal(0),
            maker_fee=Decimal(0),
            taker_fee=Decimal(0),
            ts_event=ts_init,
            ts_init=ts_init,
        )

    elif asset_type == FinamInstrumentType.SPREADS.value:
        # Use provided values or calculate defaults
        # activation_ns: 0 for historical data (makes contract always active)
        # expiration_ns: use provided value or fallback to +90 days
        actual_activation_ns = activation_ns if activation_ns is not None else 0
        actual_expiration_ns = expiration_ns if expiration_ns is not None else (
            ts_init + (90 * 24 * 60 * 60 * 1_000_000_000)  # +90 days fallback
        )

        # Extract exchange from symbol (after @)
        exchange = finam_asset.mic if hasattr(finam_asset, 'mic') else "RTSX"

        return FuturesSpread(
            instrument_id=instrument_id,
            raw_symbol=raw_symbol,
            asset_class=AssetClass.COMMODITY,  # TODO: Determine from market
            exchange=exchange,
            underlying=finam_asset.ticker,
            strategy_type="CALENDAR",  # Calendar spread (different expirations)
            activation_ns=actual_activation_ns,
            expiration_ns=actual_expiration_ns,
            currency=currency,
            price_precision=price_precision,
            price_increment=price_increment,
            multiplier=lot_size,
            lot_size=lot_size,
            ts_event=ts_init,
            ts_init=ts_init,
        )

    elif asset_type == FinamInstrumentType.INDICES.value:
        return IndexInstrument(
            instrument_id=instrument_id,
            raw_symbol=raw_symbol,
            currency=currency,
            price_precision=price_precision,
            price_increment=price_increment,
            size_precision=size_precision,
            size_increment=size_increment,
            ts_event=ts_init,
            ts_init=ts_init,
        )

    else:
        # BONDS, FUNDS, SWAPS, OTHER → Cfd (generic derivative)
        return Cfd(
            instrument_id=instrument_id,
            raw_symbol=raw_symbol,
            asset_class=AssetClass.DEBT if asset_type == FinamInstrumentType.BONDS.value else AssetClass.ALTERNATIVE,
            quote_currency=currency,  # Cfd uses quote_currency, not currency
            price_precision=price_precision,
            size_precision=size_precision,
            price_increment=price_increment,
            size_increment=size_increment,
            lot_size=None,
            max_quantity=None,
            min_quantity=None,
            max_notional=None,
            min_notional=None,
            max_price=None,
            min_price=None,
            margin_init=Decimal(0),
            margin_maint=Decimal(0),
            maker_fee=Decimal(0),
            taker_fee=Decimal(0),
            ts_event=ts_init,
            ts_init=ts_init,
        )


def _parse_currency_pair(symbol: str) -> tuple[Currency, Currency]:
    """
    Parse currency pair from Finam symbol.

    Examples
    --------
    HKDRUB_TOM@MISX -> (HKD, RUB)
    EURRUB_SPT@MISX -> (EUR, RUB)

    Returns
    -------
    tuple[Currency, Currency]
        (base_currency, quote_currency)
    """
    # Extract ticker from symbol (before @)
    ticker = symbol.split('@')[0]

    # Remove suffixes like _TOM, _SPT, _TOD
    ticker = ticker.split('_')[0]

    # Parse currency codes (assume 3-letter codes)
    if len(ticker) >= 6:
        base = ticker[:3]
        quote = ticker[3:6]
        return (Currency.from_str(base), Currency.from_str(quote))

    # Fallback
    return (Currency.from_str("USD"), Currency.from_str("RUB"))

def _calculate_price_precision(min_price_increment: Decimal) -> int:
    """
    Вычисляет precision из min_price_increment.

    Examples
    --------
    0.01 -> 2
    0.001 -> 3
    1.0 -> 0

    """
    if min_price_increment == 0:
        return 0

    # Конвертируем в строку и ищем количество знаков после запятой
    str_value = str(min_price_increment)

    if "." not in str_value:
        return 0

    return len(str_value.split(".")[1].rstrip("0"))
