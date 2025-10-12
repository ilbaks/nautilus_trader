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


from nautilus_trader.model.identifiers import Venue

FINAM_VENUE = Venue("FINAM")

# Base URLs
BASE_URL = "https://api.finam.ru/v1"
# Note: WebSocket not available - REST API only

# Authentication endpoints (AuthService)
ENDPOINT_AUTH = "/sessions"  # Auth method - получение JWT токена
ENDPOINT_AUTH_DETAILS = "/sessions/details"  # TokenDetails method

# Account & Portfolio endpoints (AccountsService)
ENDPOINT_ACCOUNTS = "/accounts"
ENDPOINT_ACCOUNT_DETAIL = "/accounts/{account_id}"
ENDPOINT_ACCOUNT_TRANSACTIONS = "/accounts/{account_id}/transactions"
ENDPOINT_ACCOUNT_TRADES = "/accounts/{account_id}/trades"

# Assets endpoints (AssetsService)
# https://tradeapi.finam.ru/docs/guides/rest/assets_service/
ENDPOINT_ASSETS = "/assets"  # Get all assets list
# Note: Symbol format is "TICKER@MIC" (e.g., "SBER@MISX", "AAPL@XNGS")
ENDPOINT_ASSET = "/assets/{symbol}"  # Get specific asset details (path parameter!)
ENDPOINT_ASSET_PARAMS = "/asset/params"  # Trading parameters (query: symbol, account_id)
ENDPOINT_ASSET_SCHEDULE = "/asset/schedule"  # Trading schedule (query: symbol)
ENDPOINT_OPTIONS_CHAIN = "/options/chain"  # Options chain (query: underlying_symbol)
ENDPOINT_EXCHANGES = "/exchanges"  # List of exchanges

# Orders endpoints (OrdersService)
# Note: Exact paths not specified in docs, inferred from service structure
ENDPOINT_ORDERS = "/accounts/{account_id}/orders"
ENDPOINT_ORDER_DETAIL = "/accounts/{account_id}/orders/{order_id}"

# Market Data endpoints (MarketDataService)
ENDPOINT_MARKETDATA_BARS = "/marketdata/bars"  # Historical candles
ENDPOINT_MARKETDATA_LAST_QUOTE = "/marketdata/last_quote"  # Current quote (corrected)
ENDPOINT_MARKETDATA_ORDERBOOK = "/marketdata/orderbook"  # Order book snapshot
ENDPOINT_MARKETDATA_LATEST_TRADES = "/marketdata/latest_trades"  # Recent trades (corrected)

# Rate limits (requests per minute per endpoint)
RATE_LIMIT_DEFAULT = 200

