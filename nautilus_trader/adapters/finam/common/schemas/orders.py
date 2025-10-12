
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

from nautilus_trader.adapters.finam.common.enums import (
    FinamOrderSide,
    FinamOrderStatus,
    FinamOrderType,
)


class OrderRequest(BaseModel):
    """Request body for POST /accounts/{account_id}/orders."""

    symbol: str = Field(..., description="Instrument symbol")
    quantity: Decimal = Field(..., description="Order quantity")
    side: FinamOrderSide = Field(..., description="Order side (BUY/SELL)")
    order_type: FinamOrderType = Field(..., alias="type", description="Order type (MARKET/LIMIT)")
    limit_price: Decimal | None = Field(None, description="Limit price (required for LIMIT orders)")
    client_order_id: str = Field(..., description="Client-assigned order ID")

    class Config:
        populate_by_name = True


class Order(BaseModel):
    """Finam order (response from API)."""

    order_id: str = Field(..., description="Exchange-assigned order ID")
    client_order_id: str = Field(..., description="Client-assigned order ID")
    account_id: str = Field(..., description="Account ID")
    symbol: str = Field(..., description="Instrument symbol")
    side: FinamOrderSide = Field(..., description="Order side")
    order_type: FinamOrderType = Field(..., alias="type", description="Order type")
    quantity: Decimal = Field(..., description="Total order quantity")
    limit_price: Decimal | None = Field(None, description="Limit price (for LIMIT orders)")
    filled_quantity: Decimal = Field(..., description="Filled quantity")
    status: FinamOrderStatus = Field(..., description="Order status")
    timestamp: datetime = Field(..., description="Order creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")

    class Config:
        populate_by_name = True


class OrderState(BaseModel):
    """Order state update (response from submit/cancel operations)."""

    order_id: str = Field(..., description="Exchange-assigned order ID")
    client_order_id: str = Field(..., description="Client-assigned order ID")
    status: FinamOrderStatus = Field(..., description="Current order status")
    filled_quantity: Decimal = Field(..., description="Filled quantity")
    timestamp: datetime = Field(..., description="Update timestamp")
    message: str | None = Field(None, description="Status message or error description")


class OrdersResponse(BaseModel):
    """Response from GET /accounts/{account_id}/orders."""

    orders: list[Order] = Field(default_factory=list, description="List of orders")
