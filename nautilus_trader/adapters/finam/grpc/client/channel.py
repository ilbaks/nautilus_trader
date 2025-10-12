"""
gRPC Channel management for Finam Trade API.
Based on OsEngine implementation analysis.
Async implementation using grpc.aio for Nautilus Trader compatibility.
"""
import grpc.aio
from typing import Optional


class FinamGrpcChannel:
    """Manages async gRPC channel lifecycle and connection."""

    def __init__(
        self,
        host: str = "api.finam.ru",  # Correct endpoint per OsEngine
        port: int = 443,
        use_ssl: bool = True,
    ):
        """
        Initialize async gRPC channel manager.

        Parameters
        ----------
        host : str
            gRPC server host (default: api.finam.ru)
        port : int
            gRPC server port (default 443 for SSL)
        use_ssl : bool
            Use secure channel with SSL/TLS
        """
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self._channel: Optional[grpc.aio.Channel] = None

    async def connect(self) -> grpc.aio.Channel:
        """
        Create and return async gRPC channel with proper HTTP/2 configuration.

        Based on OsEngine implementation:
        - Keep-alive settings for long-lived connections
        - HTTP/2 configuration
        - Retry settings

        Returns
        -------
        grpc.aio.Channel
            Active async gRPC channel
        """
        if self._channel is not None:
            return self._channel

        target = f"{self.host}:{self.port}"

        # gRPC channel options based on OsEngine configuration
        options = [
            # Message size limits (-1 = unlimited, like OsEngine)
            ('grpc.max_receive_message_length', -1),
            ('grpc.max_send_message_length', -1),

            # Keep-alive settings (critical for streams)
            ('grpc.keepalive_time_ms', 30000),  # 30 seconds
            ('grpc.keepalive_timeout_ms', 10000),  # 10 seconds
            ('grpc.keepalive_permit_without_calls', 1),
            ('grpc.http2.max_pings_without_data', 0),

            # Enable retries (like OsEngine MaxRetryAttempts = 5)
            ('grpc.enable_retries', 1),

            # Connection timeout
            ('grpc.initial_reconnect_backoff_ms', 1000),
            ('grpc.max_reconnect_backoff_ms', 5000),
        ]

        if self.use_ssl:
            # Use SSL credentials for secure connection
            credentials = grpc.ssl_channel_credentials()
            self._channel = grpc.aio.secure_channel(target, credentials, options=options)
        else:
            # Insecure channel (for testing only)
            self._channel = grpc.aio.insecure_channel(target, options=options)

        return self._channel

    async def close(self) -> None:
        """Close the async gRPC channel."""
        if self._channel is not None:
            await self._channel.close()
            self._channel = None

    async def __aenter__(self):
        """Async context manager entry."""
        return await self.connect()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
        return False
