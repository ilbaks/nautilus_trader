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
Unit tests for Finam gRPC rate limiter.

Tests the RateLimiter class that prevents exceeding API rate limits.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from nautilus_trader.adapters.finam.grpc.client.rate_limiter import RateLimiter


class TestRateLimiterInit:
    """Test RateLimiter initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        # Arrange, Act
        limiter = RateLimiter()

        # Assert
        assert limiter._max_requests == 100
        assert limiter._time_window == 60.0
        assert len(limiter._requests) == 0

    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        # Arrange, Act
        limiter = RateLimiter(max_requests=50, time_window=30.0)

        # Assert
        assert limiter._max_requests == 50
        assert limiter._time_window == 30.0
        assert len(limiter._requests) == 0


class TestRateLimiterAcquire:
    """Test RateLimiter acquire() method."""

    @pytest.mark.asyncio
    async def test_acquire_under_limit(self):
        """Test acquiring when under rate limit."""
        # Arrange
        limiter = RateLimiter(max_requests=5, time_window=60.0)

        # Act
        start_time = datetime.utcnow()
        await limiter.acquire()
        await limiter.acquire()
        await limiter.acquire()
        end_time = datetime.utcnow()

        # Assert
        assert limiter.current_usage == 3
        # Should complete quickly (no waiting)
        assert (end_time - start_time).total_seconds() < 0.1

    @pytest.mark.asyncio
    async def test_acquire_at_limit_waits(self):
        """Test that acquire() blocks when limit is reached."""
        # Arrange
        limiter = RateLimiter(max_requests=3, time_window=1.0)

        # Act - Fill the bucket
        await limiter.acquire()
        await limiter.acquire()
        await limiter.acquire()

        assert limiter.current_usage == 3

        # This should wait ~1 second for oldest request to expire
        start_time = datetime.utcnow()
        await limiter.acquire()  # 4th request - should wait
        end_time = datetime.utcnow()

        # Assert
        wait_time = (end_time - start_time).total_seconds()
        assert wait_time >= 0.9  # Should wait close to 1 second
        assert limiter.current_usage == 3  # Still at limit after wait

    @pytest.mark.asyncio
    async def test_acquire_concurrent_requests(self):
        """Test concurrent acquire calls."""
        # Arrange
        limiter = RateLimiter(max_requests=5, time_window=60.0)

        # Act - Simulate 10 concurrent requests
        async def make_request():
            await limiter.acquire()

        tasks = [make_request() for _ in range(10)]
        await asyncio.gather(*tasks)

        # Assert
        assert limiter.current_usage == 10


class TestRateLimiterTimeWindow:
    """Test time window behavior."""

    @pytest.mark.asyncio
    async def test_old_requests_removed(self):
        """Test that old requests outside time window are removed."""
        # Arrange
        limiter = RateLimiter(max_requests=5, time_window=2.0)

        # Act - Make 3 requests
        await limiter.acquire()
        await limiter.acquire()
        await limiter.acquire()

        assert limiter.current_usage == 3

        # Wait for requests to expire
        await asyncio.sleep(2.1)

        # Assert - Old requests should be removed
        assert limiter.current_usage == 0

    @pytest.mark.asyncio
    async def test_partial_expiration(self):
        """Test that only old requests are removed."""
        # Arrange
        limiter = RateLimiter(max_requests=10, time_window=1.0)

        # Act - Make 2 requests
        await limiter.acquire()
        await limiter.acquire()

        # Wait 0.6 seconds
        await asyncio.sleep(0.6)

        # Make 2 more requests
        await limiter.acquire()
        await limiter.acquire()

        assert limiter.current_usage == 4

        # Wait 0.5 more seconds (total 1.1s from first requests)
        await asyncio.sleep(0.5)

        # Assert - First 2 requests should have expired
        current = limiter.current_usage
        assert current == 2  # Only last 2 requests remain


class TestRateLimiterReset:
    """Test reset() method."""

    @pytest.mark.asyncio
    async def test_reset_clears_state(self):
        """Test that reset() clears all recorded requests."""
        # Arrange
        limiter = RateLimiter(max_requests=10, time_window=60.0)

        await limiter.acquire()
        await limiter.acquire()
        await limiter.acquire()

        assert limiter.current_usage == 3

        # Act
        limiter.reset()

        # Assert
        assert limiter.current_usage == 0
        assert len(limiter._requests) == 0

    @pytest.mark.asyncio
    async def test_reset_allows_immediate_requests(self):
        """Test that after reset, requests can be made immediately."""
        # Arrange
        limiter = RateLimiter(max_requests=2, time_window=10.0)

        # Fill to limit
        await limiter.acquire()
        await limiter.acquire()

        assert limiter.current_usage == 2

        # Act
        limiter.reset()

        # Should now be able to make requests immediately without waiting
        start_time = datetime.utcnow()
        await limiter.acquire()
        await limiter.acquire()
        end_time = datetime.utcnow()

        # Assert
        assert (end_time - start_time).total_seconds() < 0.1
        assert limiter.current_usage == 2


class TestRateLimiterCurrentUsage:
    """Test current_usage property."""

    @pytest.mark.asyncio
    async def test_current_usage_accurate(self):
        """Test that current_usage returns accurate count."""
        # Arrange
        limiter = RateLimiter(max_requests=10, time_window=60.0)

        # Act, Assert
        assert limiter.current_usage == 0

        await limiter.acquire()
        assert limiter.current_usage == 1

        await limiter.acquire()
        await limiter.acquire()
        assert limiter.current_usage == 3

    @pytest.mark.asyncio
    async def test_current_usage_cleans_old_requests(self):
        """Test that current_usage removes expired requests."""
        # Arrange
        limiter = RateLimiter(max_requests=10, time_window=1.0)

        # Act
        await limiter.acquire()
        await limiter.acquire()

        assert limiter.current_usage == 2

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Assert - accessing current_usage should clean old requests
        assert limiter.current_usage == 0


class TestRateLimiterEdgeCases:
    """Test edge cases and special scenarios."""

    @pytest.mark.asyncio
    async def test_zero_time_window(self):
        """Test behavior with very small time window."""
        # Arrange
        limiter = RateLimiter(max_requests=5, time_window=0.1)

        # Act
        await limiter.acquire()
        await limiter.acquire()

        # Wait for window to expire
        await asyncio.sleep(0.15)

        # Assert - Should be able to make new requests immediately
        assert limiter.current_usage == 0

    @pytest.mark.asyncio
    async def test_high_request_limit(self):
        """Test with very high request limit."""
        # Arrange
        limiter = RateLimiter(max_requests=1000, time_window=60.0)

        # Act - Make many requests
        tasks = [limiter.acquire() for _ in range(100)]
        await asyncio.gather(*tasks)

        # Assert
        assert limiter.current_usage == 100
        assert limiter.current_usage <= limiter._max_requests
