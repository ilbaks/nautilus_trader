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
Configuration classes for Finam adapter.
"""

from nautilus_trader.config import LiveDataClientConfig
from nautilus_trader.config import LiveExecClientConfig
from nautilus_trader.config import PositiveInt


class FinamDataClientConfig(LiveDataClientConfig, frozen=True):
    """
    Configuration for ``FinamDataClient`` instances.

    Parameters
    ----------
    client_id : str, default "FINAM"
        The client ID for the Finam gRPC client.
    access_token : str, optional
        The Finam API access token (JWT).
        If ``None`` then will source the `FINAM_SECRET_TOKEN` environment variable.
    account_id : str, optional
        The Finam trading account ID.
        If ``None`` then will source the `FINAM_ACCOUNT_ID` environment variable.
    host : str, default "api.finam.ru"
        The gRPC server host address.
    port : int, default 443
        The gRPC server port.
    use_ssl : bool, default True
        If the client should use SSL/TLS for gRPC connection.
    rate_limit_requests : int, default 100
        Maximum number of requests per rate limit window.
    rate_limit_window : float, default 60.0
        Rate limit time window in seconds.
    auto_refresh_token : bool, default True
        If the JWT token should be automatically refreshed in background.
    update_instruments_interval_mins : PositiveInt or None, default 60
        The interval (minutes) between reloading instruments from the venue.
        If ``None`` then instruments will not be automatically reloaded.

    """

    client_id: str = "FINAM"
    access_token: str | None = None
    account_id: str | None = None
    host: str = "api.finam.ru"
    port: int = 443
    use_ssl: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: float = 60.0
    auto_refresh_token: bool = True
    update_instruments_interval_mins: PositiveInt | None = 60


class FinamExecClientConfig(LiveExecClientConfig, frozen=True):
    """
    Configuration for ``FinamExecutionClient`` instances.

    Parameters
    ----------
    client_id : str, default "FINAM"
        The client ID for the Finam gRPC client.
    access_token : str, optional
        The Finam API access token (JWT).
        If ``None`` then will source the `FINAM_SECRET_TOKEN` environment variable.
    account_id : str
        The Finam trading account ID (required for execution).
        If ``None`` then will source the `FINAM_ACCOUNT_ID` environment variable.
    host : str, default "api.finam.ru"
        The gRPC server host address.
    port : int, default 443
        The gRPC server port.
    use_ssl : bool, default True
        If the client should use SSL/TLS for gRPC connection.
    rate_limit_requests : int, default 100
        Maximum number of requests per rate limit window.
    rate_limit_window : float, default 60.0
        Rate limit time window in seconds.
    auto_refresh_token : bool, default True
        If the JWT token should be automatically refreshed in background.
    update_account_interval_secs : PositiveInt, default 10
        The interval (seconds) between polling account state via GetAccount().
    max_retries : PositiveInt, optional
        The maximum number of times a submit or cancel order request will be retried.
    retry_delay_initial_ms : PositiveInt, optional
        The initial delay (milliseconds) between retries.
    retry_delay_max_ms : PositiveInt, optional
        The maximum delay (milliseconds) between retries.

    Warnings
    --------
    A short `retry_delay_initial_ms` with frequent retries may result in rate limiting.

    """

    client_id: str = "FINAM"
    access_token: str | None = None
    account_id: str | None = None
    host: str = "api.finam.ru"
    port: int = 443
    use_ssl: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: float = 60.0
    auto_refresh_token: bool = True
    update_account_interval_secs: PositiveInt = 10
    max_retries: PositiveInt | None = None
    retry_delay_initial_ms: PositiveInt | None = None
    retry_delay_max_ms: PositiveInt | None = None
