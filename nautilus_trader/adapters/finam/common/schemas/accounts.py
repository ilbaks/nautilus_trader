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

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from nautilus_trader.adapters.finam.common.enums import FinamAccountType


class Money(BaseModel):
    """Money balance in specific currency."""

    currency: str = Field(..., description="Currency code (e.g., 'RUB', 'USD')")
    value: Decimal = Field(..., description="Amount")


class Position(BaseModel):
    """Open position in an instrument."""

    symbol: str = Field(..., description="Instrument symbol")
    quantity: Decimal = Field(..., description="Position quantity (positive=long, negative=short)")
    average_price: Decimal = Field(..., description="Average entry price")
    current_price: Decimal = Field(..., description="Current market price")
    unrealized_pnl: Decimal | None = Field(None, description="Unrealized profit/loss")


class Transaction(BaseModel):
    """Account transaction (deposit, withdrawal, trade, etc.)."""

    transaction_id: str = Field(..., description="Unique transaction ID")
    account_id: str = Field(..., description="Account ID")
    transaction_type: str = Field(..., alias="type", description="Transaction type")
    amount: Decimal = Field(..., description="Transaction amount")
    currency: str = Field(..., description="Currency code")
    timestamp: datetime = Field(..., description="Transaction timestamp")
    description: str | None = Field(None, description="Transaction description")

    class Config:
        populate_by_name = True


class Account(BaseModel):
    """Finam trading account."""

    account_id: str = Field(..., description="Unique account ID")
    account_type: FinamAccountType = Field(..., alias="type", description="Account type")
    status: str = Field(..., description="Account status (e.g., 'ACTIVE', 'BLOCKED')")
    equity: Decimal = Field(..., description="Total account equity")
    unrealized_profit: Decimal = Field(..., description="Unrealized profit/loss")
    positions: list[Position] = Field(default_factory=list, description="Open positions")
    cash: list[Money] = Field(default_factory=list, description="Cash balances by currency")

    class Config:
        populate_by_name = True


class TransactionsResponse(BaseModel):
    """Response from GET /accounts/{account_id}/transactions."""

    transactions: list[Transaction] = Field(default_factory=list, description="List of transactions")