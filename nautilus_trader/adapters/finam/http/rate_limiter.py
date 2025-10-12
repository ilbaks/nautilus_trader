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

import asyncio
import time
from collections import defaultdict, deque

from nautilus_trader.common.component import Logger


class RateLimiter:
    """
    Rate limiter for Finam API endpoints.

    Implements sliding window rate limiting per endpoint.
    Finam API allows 200 requests per minute per endpoint.

    Parameters
    ----------
    max_requests : int
        Maximum number of requests allowed in the time window (default: 200)
    window_seconds : int
        Time window in seconds (default: 60)
    logger : Logger, optional
        Logger instance for debug messages

    """

    def __init__(
        self,
        max_requests: int = 200,
        window_seconds: int = 60,
        logger: Logger | None = None,
    ) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._logger = logger

        # Track request timestamps per endpoint
        # {endpoint: deque([timestamp1, timestamp2, ...])}
        self._requests: dict[str, deque] = defaultdict(lambda: deque())

        # Lock for thread-safety
        self._lock = asyncio.Lock()

    async def acquire(self, endpoint: str) -> None:
        """
        Acquire permission to make a request to the endpoint.

        Blocks if rate limit is exceeded, waiting until a slot becomes available.

        Parameters
        ----------
        endpoint : str
            API endpoint path (e.g., "/sessions", "/instruments")

        """
        async with self._lock:
            now = time.time()

            # Clean up old requests outside the window
            self._cleanup_old_requests(endpoint, now)

            # Check if we're at the limit
            request_queue = self._requests[endpoint]

            if len(request_queue) >= self._max_requests:
                # Calculate wait time until oldest request expires
                oldest_request_time = request_queue[0]
                wait_time = self._window_seconds - (now - oldest_request_time)

                if wait_time > 0:
                    if self._logger:
                        self._logger.warning(
                            f"Rate limit reached for {endpoint}. "
                            f"Waiting {wait_time:.2f}s...",
                        )

                    # Wait until we can make the request
                    await asyncio.sleep(wait_time)

                    # After waiting, cleanup again
                    now = time.time()
                    self._cleanup_old_requests(endpoint, now)

            # Record this request
            request_queue.append(now)

            if self._logger:
                self._logger.debug(
                    f"Request permitted for {endpoint}. "
                    f"Count: {len(request_queue)}/{self._max_requests}",
                )

    def _cleanup_old_requests(self, endpoint: str, current_time: float) -> None:
        """
        Remove requests older than the time window.

        Parameters
        ----------
        endpoint : str
            API endpoint path
        current_time : float
            Current timestamp

        """
        request_queue = self._requests[endpoint]
        cutoff_time = current_time - self._window_seconds

        # Remove all requests older than cutoff_time
        while request_queue and request_queue[0] < cutoff_time:
            request_queue.popleft()

    def get_request_count(self, endpoint: str) -> int:
        """
        Get current number of requests in the window for an endpoint.

        Parameters
        ----------
        endpoint : str
            API endpoint path

        Returns
        -------
        int
            Number of requests made to this endpoint in the current window

        """
        now = time.time()
        self._cleanup_old_requests(endpoint, now)
        return len(self._requests[endpoint])

    def reset(self, endpoint: str | None = None) -> None:
        """
        Reset rate limiter for specific endpoint or all endpoints.

        Parameters
        ----------
        endpoint : str, optional
            Endpoint to reset. If None, resets all endpoints.

        """
        if endpoint is None:
            self._requests.clear()
            if self._logger:
                self._logger.info("Rate limiter reset for all endpoints")
        else:
            if endpoint in self._requests:
                del self._requests[endpoint]
                if self._logger:
                    self._logger.info(f"Rate limiter reset for {endpoint}")