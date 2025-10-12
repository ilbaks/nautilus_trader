"""
Main gRPC client for Finam Trade API.
Provides access to all gRPC services.
Async implementation for Nautilus Trader compatibility.
"""
from typing import Optional
import grpc.aio

from nautilus_trader.adapters.finam.grpc.client.channel import FinamGrpcChannel
from nautilus_trader.adapters.finam.grpc.client.auth import FinamAuthManager
from nautilus_trader.adapters.finam.grpc.client.rate_limiter import RateLimiter

from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.auth import (
    auth_service_pb2_grpc,
)
from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.assets import (
    assets_service_pb2_grpc,
)
from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.accounts import (
    accounts_service_pb2_grpc,
)
from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.marketdata import (
    marketdata_service_pb2_grpc,
)
from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.orders import (
    orders_service_pb2_grpc,
)


class FinamGrpcClient:
    """
    Main async gRPC client for Finam Trade API.

    Provides access to all services stubs with authentication and rate limiting.
    """
    def __init__(
        self,
        client_id: str,
        access_token: str,
        host: str = "api.finam.ru",  # Correct endpoint per OsEngine
        port: int = 443,
        use_ssl: bool = True,
        rate_limit_requests: int = 100,
        rate_limit_window: float = 60.0,
        auto_refresh_token: bool = True,
    ):
        """
        Initialize async Finam gRPC client.

        Parameters
        ----------
        client_id : str
            Finam client ID
        access_token : str
            Finam access token
        host : str
            gRPC server host
        port : int
            gRPC server port
        use_ssl : bool
            Use secure SSL/TLS connection
        rate_limit_requests : int
            Maximum requests per time window
        rate_limit_window : float
            Rate limit time window in seconds
        auto_refresh_token : bool
            Automatically refresh JWT token in background
        """
        self._client_id = client_id
        self._access_token = access_token
        self._auto_refresh_token = auto_refresh_token

        # Channel management
        self._channel_manager = FinamGrpcChannel(
            host=host,
            port=port,
            use_ssl=use_ssl,
        )
        self._channel: Optional[grpc.aio.Channel] = None

        # Auth management
        self._auth_manager: Optional[FinamAuthManager] = None

        # Rate limiting
        self._rate_limiter = RateLimiter(
            max_requests=rate_limit_requests,
            time_window=rate_limit_window,
        )

        # Service stubs (initialized on connect)
        self._auth_stub: Optional[auth_service_pb2_grpc.AuthServiceStub] = None
        self._assets_stub: Optional[assets_service_pb2_grpc.AssetsServiceStub] = None
        self._accounts_stub: Optional[accounts_service_pb2_grpc.AccountsServiceStub] = None
        self._marketdata_stub: Optional[marketdata_service_pb2_grpc.MarketDataServiceStub] = None
        self._orders_stub: Optional[orders_service_pb2_grpc.OrdersServiceStub] = None

    async def connect(self) -> None:
        """Establish async gRPC connection and initialize services."""
        if self._channel is not None:
            return  # Already connected

        # Create channel
        self._channel = await self._channel_manager.connect()

        # Initialize auth manager
        self._auth_manager = FinamAuthManager(
            channel=self._channel,
            client_id=self._client_id,
            access_token=self._access_token,
        )

        # Initialize service stubs
        self._auth_stub = auth_service_pb2_grpc.AuthServiceStub(self._channel)
        self._assets_stub = assets_service_pb2_grpc.AssetsServiceStub(self._channel)
        self._accounts_stub = accounts_service_pb2_grpc.AccountsServiceStub(self._channel)
        self._marketdata_stub = marketdata_service_pb2_grpc.MarketDataServiceStub(self._channel)
        self._orders_stub = orders_service_pb2_grpc.OrdersServiceStub(self._channel)

        # Start auto-refresh if enabled
        if self._auto_refresh_token:
            await self._auth_manager.start_auto_refresh()

    async def disconnect(self) -> None:
        """Close async gRPC connection and cleanup."""
        # Stop auto-refresh
        if self._auth_manager is not None:
            await self._auth_manager.stop_auto_refresh()

        # Close channel
        await self._channel_manager.close()
        self._channel = None
        self._auth_manager = None

        # Clear stubs
        self._auth_stub = None
        self._assets_stub = None
        self._accounts_stub = None
        self._marketdata_stub = None
        self._orders_stub = None

    async def get_metadata(self) -> list[tuple[str, str]]:
        """
        Get gRPC metadata with authorization.

        Returns
        -------
        list[tuple[str, str]]
            gRPC metadata
        """
        if self._auth_manager is None:
            raise RuntimeError("Client not connected. Call connect() first.")

        return await self._auth_manager.create_metadata()

    # Service stub properties

    @property
    def auth(self) -> auth_service_pb2_grpc.AuthServiceStub:
        """Get AuthService stub."""
        if self._auth_stub is None:
            raise RuntimeError("Client not connected. Call connect() first.")
        return self._auth_stub

    @property
    def assets(self) -> assets_service_pb2_grpc.AssetsServiceStub:
        """Get AssetsService stub."""
        if self._assets_stub is None:
            raise RuntimeError("Client not connected. Call connect() first.")
        return self._assets_stub

    @property
    def accounts(self) -> accounts_service_pb2_grpc.AccountsServiceStub:
        """Get AccountsService stub."""
        if self._accounts_stub is None:
            raise RuntimeError("Client not connected. Call connect() first.")
        return self._accounts_stub

    @property
    def marketdata(self) -> marketdata_service_pb2_grpc.MarketDataServiceStub:
        """Get MarketDataService stub."""
        if self._marketdata_stub is None:
            raise RuntimeError("Client not connected. Call connect() first.")
        return self._marketdata_stub

    @property
    def orders(self) -> orders_service_pb2_grpc.OrdersServiceStub:
        """Get OrdersService stub."""
        if self._orders_stub is None:
            raise RuntimeError("Client not connected. Call connect() first.")
        return self._orders_stub

    @property
    def rate_limiter(self) -> RateLimiter:
        """Get rate limiter."""
        return self._rate_limiter

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
        return False