"""
Authentication manager for Finam Trade API.
Handles JWT token lifecycle using AuthService.
Async implementation for Nautilus Trader compatibility.
"""
from typing import Optional
from datetime import datetime, timedelta
import asyncio
import grpc.aio

from nautilus_trader.adapters.finam.grpc.proto.finam_grpc.tradeapi.v1.auth import(
    auth_service_pb2,
    auth_service_pb2_grpc,
)


class FinamAuthManager:
    """Manages async JWT authentication tokens for Finam Trade API."""

    # JWT token lifetime from Finam API documentation
    JWT_TOKEN_TTL_MINUTES = 15  # Token expires in 15 minutes
    REFRESH_BEFORE_EXPIRY_MINUTES = 5  # Refresh 5 minutes before expiry

    def __init__(
        self,
        channel: grpc.aio.Channel,
        client_id: str,
        access_token: str,
    ):
        """
        Initialize async authentication manager.

        Parameters
        ----------
        channel : grpc.aio.Channel
            Active async gRPC channel
        client_id : str
            Finam client ID
        access_token : str
            Finam access token (from web portal)
        """
        self._stub = auth_service_pb2_grpc.AuthServiceStub(channel)
        self._client_id = client_id
        self._access_token = access_token

        self._jwt_token: Optional[str] = None
        self._jwt_expires_at: Optional[datetime] = None
        self._refresh_lock = asyncio.Lock()
        self._auto_refresh_task: Optional[asyncio.Task] = None

    async def get_jwt_token(self) -> str:
        """
        Get valid JWT token, refreshing if necessary.

        Returns
        -------
        str
            Valid JWT token

        Raises
        ------
        grpc.RpcError
            If authentication fails
        """
        # Check if we have a valid token
        if self._jwt_token is not None and self._jwt_expires_at is not None:
            # Check if token is still valid (not expired and not close to expiry)
            now = datetime.utcnow()
            if now < self._jwt_expires_at - timedelta(minutes=self.REFRESH_BEFORE_EXPIRY_MINUTES):
                return self._jwt_token

        # Request new JWT token
        return await self._refresh_jwt_token()

    async def _refresh_jwt_token(self) -> str:
        """
        Request new JWT token from AuthService.

        Uses lock to prevent concurrent refresh requests.

        Returns
        -------
        str
            New JWT token

        Raises
        ------
        grpc.RpcError
            If authentication fails
        """
        async with self._refresh_lock:
            # Double-check if another coroutine already refreshed
            if self._jwt_token is not None and self._jwt_expires_at is not None:
                now = datetime.utcnow()
                if now < self._jwt_expires_at - timedelta(minutes=self.REFRESH_BEFORE_EXPIRY_MINUTES):
                    return self._jwt_token

            request = auth_service_pb2.AuthRequest(
                secret=self._access_token,
            )

            response = await self._stub.Auth(request)

            # Store token and expiration
            self._jwt_token = response.token

            # JWT expires in 15 minutes per Finam API docs
            self._jwt_expires_at = datetime.utcnow() + timedelta(minutes=self.JWT_TOKEN_TTL_MINUTES)

            return self._jwt_token

    async def create_metadata(self) -> list[tuple[str, str]]:
        """
        Create gRPC metadata with authorization header.

        Based on OsEngine: adds x-app-name header for client identification.

        Returns
        -------
        list[tuple[str, str]]
            gRPC metadata with JWT token and app identification
        """
        token = await self.get_jwt_token()
        return [
            ("authorization", token),
            ("x-app-name", "NautilusTrader"),  # Client identification per OsEngine
        ]

    def invalidate(self) -> None:
        """Invalidate current JWT token (force refresh on next request)."""
        self._jwt_token = None
        self._jwt_expires_at = None

    async def start_auto_refresh(self) -> None:
        """
        Start background task to auto-refresh JWT token.

        Refreshes token every (TTL - REFRESH_BEFORE_EXPIRY) minutes
        to ensure token is always valid.

        Based on OsEngine ReSubscribeThread that refreshes every 14 minutes.
        """
        if self._auto_refresh_task is not None and not self._auto_refresh_task.done():
            return  # Already running

        self._auto_refresh_task = asyncio.create_task(self._auto_refresh_loop())

    async def stop_auto_refresh(self) -> None:
        """Stop background auto-refresh task."""
        if self._auto_refresh_task is not None:
            self._auto_refresh_task.cancel()
            try:
                await self._auto_refresh_task
            except asyncio.CancelledError:
                pass
            self._auto_refresh_task = None

    async def _auto_refresh_loop(self) -> None:
        """
        Background loop that refreshes JWT token periodically.

        Runs every (TTL - REFRESH_BEFORE_EXPIRY) minutes.
        For 15 min TTL and 5 min buffer = refresh every 10 minutes.
        """
        refresh_interval = (self.JWT_TOKEN_TTL_MINUTES - self.REFRESH_BEFORE_EXPIRY_MINUTES) * 60

        while True:
            try:
                await asyncio.sleep(refresh_interval)
                await self._refresh_jwt_token()
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue loop
                print(f"Error during auto-refresh: {e}")
                # Wait a bit before retry
                await asyncio.sleep(30)