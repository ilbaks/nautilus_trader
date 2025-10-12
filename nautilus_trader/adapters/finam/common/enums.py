
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

from enum import Enum


class FinamOrderSide(str, Enum):
    """Finam order side enum."""
    BUY = "BUY"
    SELL = "SELL"


class FinamOrderType(str, Enum):
    """Finam order type enum."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class FinamOrderStatus(str, Enum):
    """Finam order status enum."""
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    PENDING_CANCEL = "PENDING_CANCEL"


class FinamTimeFrame(str, Enum):
    """Finam timeframe enum for bars."""
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    DAY_1 = "1d"
    WEEK_1 = "1w"
    MONTH_1 = "1M"


class FinamInstrumentType(str, Enum):
    """
    Finam instrument type enum.

    Maps to Asset.type field from gRPC AssetsService.Assets() response.
    """
    EQUITIES = "EQUITIES"      # Stocks
    BONDS = "BONDS"            # Bonds
    FUNDS = "FUNDS"            # ETFs and mutual funds
    FUTURES = "FUTURES"        # Futures contracts
    CURRENCIES = "CURRENCIES"  # Currency pairs (FX)
    SPREADS = "SPREADS"        # Calendar spreads
    SWAPS = "SWAPS"            # FX swaps
    INDICES = "INDICES"        # Stock indices
    OTHER = "OTHER"            # Other instruments


class FinamAccountType(str, Enum):
    """Finam account type enum."""
    MARGIN = "MARGIN"
    CASH = "CASH"