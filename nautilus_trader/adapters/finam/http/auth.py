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
from datetime import datetime, timedelta, timezone

import httpx

from nautilus_trader.adapters.finam.common.constants import BASE_URL, ENDPOINT_AUTH
from nautilus_trader.adapters.finam.common.schemas.auth import JwtTokenResponse
from nautilus_trader.common.component import Logger

class JwtTokenManager:
    """
    Manages JWT token authentication for Finam API.

    Features:
    - Automatic token refresh every 14 minutes (token TTL is 15 minutes)
    - Thread-safe token access
    - Background auto-refresh task
    - Graceful error handling

    Parameters
    ----------
    secret_token : str
        The secret token for authentication (from Finam API settings)
    base_url : str, optional
        Base URL for API (default: https://api.finam.ru/v1)
    logger : Logger, optional
        Logger instance for debug/error messages

    """

    def __init__(
        self,
        secret_token: str,
        base_url: str = BASE_URL,
        logger: Logger | None = None,
    ) -> None:
        self._secret_token = secret_token
        self._base_url = base_url
        self._logger = logger

        self._jwt_token: str | None = None
        self._token_expiry: datetime | None = None
        self._refresh_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()
        self._running = False


    async def get_token(self) -> str:
        """
        Get current valid JWT token.

        Automatically refreshes token if expired or not yet obtained.

        Returns
        -------
        str
            Valid JWT token

        Raises
        ------
        httpx.HTTPError
            If token refresh fails

        """
        async with self._lock:
            if self._jwt_token is None or self._is_token_expired():
                await self._refresh_token()
            return self._jwt_token

    def _is_token_expired(self) -> bool:
        """
        Check if current token is expired.

        Returns
        -------
        bool
            True if token is expired or not set, False otherwise

        """
        if self._token_expiry is None:
            return True
        return datetime.now(timezone.utc) >= self._token_expiry

    async def _refresh_token(self) -> None:
        """
        Refresh JWT token via API call.

        Makes POST request to /sessions endpoint with secret token.
        Updates internal token and expiry time.

        Raises
        ------
        httpx.HTTPError
            If API request fails

        """
        url = f"{self._base_url}{ENDPOINT_AUTH}"

        if self._logger:
            self._logger.debug(f"Refreshing JWT token from {url}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                json={"secret": self._secret_token},
            )
            response.raise_for_status()

            data = JwtTokenResponse(**response.json())
            self._jwt_token = data.token

            # Token lives 15 minutes, refresh every 14 minutes to be safe
            self._token_expiry = datetime.now(timezone.utc) + timedelta(minutes=14)

            if self._logger:
                self._logger.info(
                    f"JWT token refreshed successfully. Expires at {self._token_expiry.isoformat()}",
                )

    async def start_auto_refresh(self) -> None:
        """
        Start background task for automatic token refresh.

        Refreshes token every 14 minutes in the background.
        Should be called once during client initialization.

        """
        if self._running:
            if self._logger:
                self._logger.warning("Auto-refresh already running")
            return

        self._running = True

        if self._logger:
            self._logger.info("Starting JWT token auto-refresh task (every 14 minutes)")

        self._refresh_task = asyncio.create_task(self._auto_refresh_loop())

    async def stop_auto_refresh(self) -> None:
        """
        Stop background auto-refresh task.

        Should be called during client shutdown.

        """
        if not self._running:
            return

        self._running = False

        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass

        if self._logger:
            self._logger.info("JWT token auto-refresh stopped")

    async def _auto_refresh_loop(self) -> None:
        """
        Background loop for automatic token refresh.

        Runs every 14 minutes until stopped.

        """
        while self._running:
            try:
                await asyncio.sleep(14 * 60)  # 14 minutes

                if self._running:
                    async with self._lock:
                        await self._refresh_token()

            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._logger:
                    self._logger.error(f"Error in auto-refresh loop: {e}")
                # Continue loop despite errors
                await asyncio.sleep(60)  # Wait 1 minute before retry