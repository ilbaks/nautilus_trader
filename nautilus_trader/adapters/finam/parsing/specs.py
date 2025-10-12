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
Helper functions for parsing Finam instrument specifications.

Extracts trading parameters from GetAssetResponse to construct
accurate Nautilus Instrument objects.
"""
from decimal import Decimal

from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.assets.assets_service_pb2 import (
    GetAssetResponse,
)
from nautilus_trader.model.objects import Currency
from nautilus_trader.model.objects import Price
from nautilus_trader.model.objects import Quantity


# Exchange MIC → Currency mapping
MIC_TO_CURRENCY = {
    "MISX": "RUB",  # Moscow Exchange
    "SPBX": "USD",  # SPB Exchange (international stocks)
    "RTSX": "RUB",  # RTS Exchange (futures)
    "RUSX": "USD",  # Default for non-Russian stocks
    "XNGS": "USD",  # NASDAQ
    "XNYS": "USD",  # NYSE
    "ARCX": "USD",  # NYSE Arca
    "XASE": "USD",  # NYSE American
    "XCME": "USD",  # CME
}


def get_currency_from_mic(mic: str) -> Currency:
    """
    Map exchange MIC code to currency.

    Parameters
    ----------
    mic : str
        Market Identifier Code (e.g., "MISX", "SPBX")

    Returns
    -------
    Currency
        Mapped currency (default: RUB)

    Examples
    --------
    >>> get_currency_from_mic("MISX")
    Currency.RUB
    >>> get_currency_from_mic("SPBX")
    Currency.USD
    """
    currency_code = MIC_TO_CURRENCY.get(mic, "RUB")  # Default to RUB
    return Currency.from_str(currency_code)


def calculate_price_precision(decimals: int) -> int:
    """
    Extract price precision from GetAssetResponse.decimals field.

    Parameters
    ----------
    decimals : int
        Number of decimal places in price (from GetAssetResponse)

    Returns
    -------
    int
        Price precision (number of decimal places)

    Examples
    --------
    >>> calculate_price_precision(2)
    2
    >>> calculate_price_precision(0)
    0
    """
    return decimals


def calculate_price_increment(decimals: int, min_step: int) -> Price:
    """
    Calculate price increment (tick size) from GetAssetResponse fields.

    Formula: price_increment = min_step / (10 ^ decimals)

    Parameters
    ----------
    decimals : int
        Number of decimal places in price
    min_step : int
        Minimum price step (raw value)

    Returns
    -------
    Price
        Price increment (tick size)

    Examples
    --------
    >>> calculate_price_increment(decimals=2, min_step=1)
    Price(0.01, 2)  # 1 / (10^2) = 0.01

    >>> calculate_price_increment(decimals=0, min_step=1)
    Price(1.00, 0)  # 1 / (10^0) = 1

    >>> calculate_price_increment(decimals=4, min_step=5)
    Price(0.0005, 4)  # 5 / (10^4) = 0.0005
    """
    if decimals == 0:
        # No decimal places - integer prices
        increment_value = float(min_step)
    else:
        # Calculate: min_step / (10 ^ decimals)
        increment_value = min_step / (10 ** decimals)

    precision = decimals
    return Price(increment_value, precision)


def parse_lot_size(lot_size_decimal: Decimal) -> Quantity:
    """
    Parse lot_size from GetAssetResponse.lot_size (google.type.Decimal).

    Parameters
    ----------
    lot_size_decimal : Decimal
        Lot size from GetAssetResponse (google.type.Decimal with value field)

    Returns
    -------
    Quantity
        Lot size as Nautilus Quantity

    Examples
    --------
    >>> from google.type import Decimal as GoogleDecimal
    >>> lot = GoogleDecimal(value="10.0")
    >>> parse_lot_size(lot)
    Quantity(10.0, 1)
    """
    # Extract string value from google.type.Decimal
    if hasattr(lot_size_decimal, 'value'):
        lot_str = lot_size_decimal.value
    else:
        lot_str = str(lot_size_decimal)

    # Convert to float and create Quantity
    lot_float = float(lot_str)

    # Calculate precision (decimal places)
    decimal_places = len(lot_str.split('.')[-1]) if '.' in lot_str else 0

    return Quantity(lot_float, decimal_places)


def parse_instrument_specs(specs: GetAssetResponse) -> dict:
    """
    Parse all instrument specifications from GetAssetResponse.

    OsEngine Pattern: Call this when subscribing to an instrument
    to get precise trading parameters.

    Parameters
    ----------
    specs : GetAssetResponse
        Response from AssetsService.GetAsset()

    Returns
    -------
    dict
        Dictionary with parsed specifications:
        - currency: Currency
        - price_precision: int
        - price_increment: Price
        - lot_size: Quantity
        - size_precision: int
        - board: str (trading board code)
        - expiration_date: datetime | None (for futures)

    Examples
    --------
    >>> response = await client.assets.GetAsset(
    ...     GetAssetRequest(symbol="SBER@MISX"),
    ...     metadata=metadata
    ... )
    >>> specs = parse_instrument_specs(response)
    >>> specs['price_precision']
    2
    >>> specs['price_increment']
    Price(0.01, 2)
    >>> specs['lot_size']
    Quantity(1.0, 1)
    """
    # Extract currency from MIC code
    currency = get_currency_from_mic(specs.mic)

    # Price specifications
    price_precision = calculate_price_precision(specs.decimals)
    price_increment = calculate_price_increment(specs.decimals, specs.min_step)

    # Lot size (volume specifications)
    lot_size = parse_lot_size(specs.lot_size)

    # Calculate size_precision from lot_size
    # If lot_size = 10.0, size_precision = 1
    # If lot_size = 1.0, size_precision = 1
    lot_str = specs.lot_size.value if hasattr(specs.lot_size, 'value') else str(specs.lot_size)
    size_precision = len(lot_str.split('.')[-1]) if '.' in lot_str else 0

    # Expiration date (for futures)
    expiration_date = None
    if hasattr(specs, 'expiration_date') and specs.expiration_date:
        # Parse google.type.Date to datetime
        from datetime import datetime
        date_obj = specs.expiration_date
        if hasattr(date_obj, 'year') and date_obj.year > 0:
            expiration_date = datetime(date_obj.year, date_obj.month, date_obj.day)

    return {
        'currency': currency,
        'price_precision': price_precision,
        'price_increment': price_increment,
        'lot_size': lot_size,
        'size_precision': size_precision,
        'board': specs.board,
        'expiration_date': expiration_date,
    }
