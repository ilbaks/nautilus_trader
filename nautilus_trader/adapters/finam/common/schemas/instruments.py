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

from decimal import Decimal

from pydantic import BaseModel, Field

from nautilus_trader.adapters.finam.common.enums import FinamInstrumentType


class Instrument(BaseModel):
    """Finam instrument (tradable security)."""

    symbol: str = Field(..., description="Instrument symbol (e.g., 'SBER', 'RIH5')")
    name: str = Field(..., description="Human-readable instrument name")
    exchange: str = Field(..., description="Exchange code (e.g., 'MOEX')")
    instrument_type: FinamInstrumentType = Field(..., alias="type", description="Instrument type")
    lot_size: int = Field(..., description="Minimum lot size")
    min_price_increment: Decimal = Field(..., description="Minimum price tick")
    currency: str = Field(..., description="Currency code (e.g., 'RUB', 'USD')")

    class Config:
        populate_by_name = True  # Allow both 'type' and 'instrument_type'


class Asset(BaseModel):
    """Finam asset (underlying asset for instruments)."""

    id: str = Field(..., description="Unique asset identifier")
    symbol: str = Field(..., description="Asset symbol (TICKER@MIC format)")
    ticker: str = Field(..., description="Ticker symbol")
    mic: str = Field(..., description="Market identifier code")
    isin: str | None = Field(None, description="ISIN code (optional)")
    asset_type: str = Field(..., alias="type", description="Asset type")
    name: str = Field(..., description="Asset name")

    class Config:
        populate_by_name = True


class InstrumentsResponse(BaseModel):
    """Response from GET /instruments endpoint."""

    instruments: list[Instrument] = Field(default_factory=list, description="List of instruments")


class AssetsResponse(BaseModel):
    """Response from GET /assets endpoint."""

    assets: list[Asset] = Field(default_factory=list, description="List of assets")