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
Factory functions for creating Finam adapter clients.
"""

import asyncio
import os
from functools import lru_cache

from nautilus_trader.adapters.finam.common.constants import FINAM_VENUE
from nautilus_trader.adapters.finam.config import FinamDataClientConfig
from nautilus_trader.adapters.finam.config import FinamExecClientConfig
from nautilus_trader.adapters.finam.data import FinamDataClient
from nautilus_trader.adapters.finam.execution import FinamExecutionClient
from nautilus_trader.adapters.finam.grpc.client.client import FinamGrpcClient
from nautilus_trader.adapters.finam.providers import FinamInstrumentProvider
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import LiveClock
from nautilus_trader.common.component import MessageBus
from nautilus_trader.config import InstrumentProviderConfig
from nautilus_trader.live.factories import LiveDataClientFactory
from nautilus_trader.live.factories import LiveExecClientFactory


def get_access_token(access_token: str | None = None) -> str:
    """
    Get Finam API access token from config or environment.

    Parameters
    ----------
    access_token : str, optional
        The access token from config.

    Returns
    -------
    str

    Raises
    ------
    ValueError
        If access token is not provided and not found in environment.

    """
    if access_token is not None:
        return access_token

    token = os.getenv("FINAM_SECRET_TOKEN")
    if token is None:
        msg = (
            "Finam API access token not found. "
            "Either pass `access_token` in config or set `FINAM_SECRET_TOKEN` environment variable."
        )
        raise ValueError(msg)

    return token


def get_account_id(account_id: str | None = None) -> str:
    """
    Get Finam account ID from config or environment.

    Parameters
    ----------
    account_id : str, optional
        The account ID from config.

    Returns
    -------
    str

    Raises
    ------
    ValueError
        If account ID is not provided and not found in environment.

    """
    if account_id is not None:
        return account_id

    acc_id = os.getenv("FINAM_ACCOUNT_ID")
    if acc_id is None:
        msg = (
            "Finam account ID not found. "
            "Either pass `account_id` in config or set `FINAM_ACCOUNT_ID` environment variable."
        )
        raise ValueError(msg)

    return acc_id


@lru_cache(1)
def get_cached_finam_grpc_client(
    client_id: str,
    access_token: str,
    host: str = "api.finam.ru",
    port: int = 443,
    use_ssl: bool = True,
    rate_limit_requests: int = 100,
    rate_limit_window: float = 60.0,
    auto_refresh_token: bool = True,
) -> FinamGrpcClient:
    """
    Cache and return a Finam gRPC client with the given parameters.

    If a cached client with matching parameters already exists, the cached client will be returned.

    Parameters
    ----------
    client_id : str
        The client ID for the gRPC client.
    access_token : str
        The Finam API access token (JWT).
    host : str, default "api.finam.ru"
        The gRPC server host address.
    port : int, default 443
        The gRPC server port.
    use_ssl : bool, default True
        If the client should use SSL/TLS.
    rate_limit_requests : int, default 100
        Maximum requests per time window.
    rate_limit_window : float, default 60.0
        Rate limit time window in seconds.
    auto_refresh_token : bool, default True
        If JWT token should be auto-refreshed.

    Returns
    -------
    FinamGrpcClient

    """
    return FinamGrpcClient(
        client_id=client_id,
        access_token=access_token,
        host=host,
        port=port,
        use_ssl=use_ssl,
        rate_limit_requests=rate_limit_requests,
        rate_limit_window=rate_limit_window,
        auto_refresh_token=auto_refresh_token,
    )


@lru_cache(1)
def get_cached_finam_instrument_provider(
    client: FinamGrpcClient,
    clock: LiveClock,
    config: InstrumentProviderConfig,
) -> FinamInstrumentProvider:
    """
    Cache and return a Finam instrument provider.

    If a cached provider already exists, then that provider will be returned.

    Parameters
    ----------
    client : FinamGrpcClient
        The gRPC client for the instrument provider.
    clock : LiveClock
        The clock for the instrument provider.
    config : InstrumentProviderConfig
        The configuration for the instrument provider.

    Returns
    -------
    FinamInstrumentProvider

    """
    return FinamInstrumentProvider(
        client=client,
        clock=clock,
        config=config,
    )


class FinamLiveDataClientFactory(LiveDataClientFactory):
    """
    Provides a Finam live data client factory.
    """

    @staticmethod
    def create(  # type: ignore
        loop: asyncio.AbstractEventLoop,
        name: str,
        config: FinamDataClientConfig,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
    ) -> FinamDataClient:
        """
        Create a new Finam data client.

        Parameters
        ----------
        loop : asyncio.AbstractEventLoop
            The event loop for the client.
        name : str
            The custom client ID.
        config : FinamDataClientConfig
            The client configuration.
        msgbus : MessageBus
            The message bus for the client.
        cache : Cache
            The cache for the client.
        clock : LiveClock
            The clock for the client.

        Returns
        -------
        FinamDataClient

        Raises
        ------
        ValueError
            If `access_token` or `account_id` are not provided via config or environment variables.

        """
        # Get credentials from config or environment
        access_token = get_access_token(config.access_token)
        account_id = get_account_id(config.account_id)

        # Get gRPC client singleton
        client = get_cached_finam_grpc_client(
            client_id=config.client_id,
            access_token=access_token,
            host=config.host,
            port=config.port,
            use_ssl=config.use_ssl,
            rate_limit_requests=config.rate_limit_requests,
            rate_limit_window=config.rate_limit_window,
            auto_refresh_token=config.auto_refresh_token,
        )

        # Get instrument provider singleton
        provider = get_cached_finam_instrument_provider(
            client=client,
            clock=clock,
            config=config.instrument_provider,
        )

        return FinamDataClient(
            loop=loop,
            client=client,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            instrument_provider=provider,
            venue=FINAM_VENUE,
            name=name,
        )


class FinamLiveExecClientFactory(LiveExecClientFactory):
    """
    Provides a Finam live execution client factory.
    """

    @staticmethod
    def create(  # type: ignore
        loop: asyncio.AbstractEventLoop,
        name: str,
        config: FinamExecClientConfig,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
    ) -> FinamExecutionClient:
        """
        Create a new Finam execution client.

        Parameters
        ----------
        loop : asyncio.AbstractEventLoop
            The event loop for the client.
        name : str
            The custom client ID.
        config : FinamExecClientConfig
            The configuration for the client.
        msgbus : MessageBus
            The message bus for the client.
        cache : Cache
            The cache for the client.
        clock : LiveClock
            The clock for the client.

        Returns
        -------
        FinamExecutionClient

        Raises
        ------
        ValueError
            If `access_token` or `account_id` are not provided via config or environment variables.

        """
        # Get credentials from config or environment
        access_token = get_access_token(config.access_token)
        account_id = get_account_id(config.account_id)

        # Get gRPC client singleton
        client = get_cached_finam_grpc_client(
            client_id=config.client_id,
            access_token=access_token,
            host=config.host,
            port=config.port,
            use_ssl=config.use_ssl,
            rate_limit_requests=config.rate_limit_requests,
            rate_limit_window=config.rate_limit_window,
            auto_refresh_token=config.auto_refresh_token,
        )

        # Get instrument provider singleton
        provider = get_cached_finam_instrument_provider(
            client=client,
            clock=clock,
            config=config.instrument_provider,
        )

        return FinamExecutionClient(
            loop=loop,
            client=client,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            instrument_provider=provider,
            account_id=account_id,
            name=name,
        )
