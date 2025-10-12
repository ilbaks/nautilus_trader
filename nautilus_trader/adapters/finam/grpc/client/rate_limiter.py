"""
Rate limiter for Finam gRPC API requests.
"""
import asyncio
from collections import deque
from datetime import datetime, timedelta
from typing import Optional


class RateLimiter:
    """
    Token bucket rate limiter for API requests.
    
    Prevents exceeding Finam API rate limits.
    """

    def __init__(
        self,
        max_requests: int = 100,
        time_window: float = 60.0,
    ):
        """
        Initialize rate limiter.
        
        Parameters
        ----------
        max_requests : int
            Maximum requests allowed in time window (default 100)
        time_window : float
            Time window in seconds (default 60.0)
        """
        self._max_requests = max_requests
        self._time_window = time_window
        self._requests: deque[datetime] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """
        Acquire permission to make a request.
        
        Blocks if rate limit would be exceeded.
        """
        async with self._lock:
            now = datetime.utcnow()
            cutoff = now - timedelta(seconds=self._time_window)

            # Remove old requests outside time window
            while self._requests and self._requests[0] < cutoff:
                self._requests.popleft()

            # Check if we need to wait
            if len(self._requests) >= self._max_requests:
                # Calculate wait time until oldest request expires
                oldest = self._requests[0]
                wait_until = oldest + timedelta(seconds=self._time_window)
                wait_seconds = (wait_until - now).total_seconds()

                if wait_seconds > 0:
                    await asyncio.sleep(wait_seconds)
                    # Recursively try again
                    return await self.acquire()

            # Record this request
            self._requests.append(now)

    def reset(self) -> None:
        """Reset rate limiter state."""
        self._requests.clear()

    @property
    def current_usage(self) -> int:
        """
        Get current number of requests in time window.
        
        Returns
        -------
        int
            Number of requests in current window
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self._time_window)

        # Clean old requests
        while self._requests and self._requests[0] < cutoff:
            self._requests.popleft()

        return len(self._requests)