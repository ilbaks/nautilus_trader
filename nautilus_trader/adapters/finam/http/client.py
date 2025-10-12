
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

from typing import Any

import httpx

from nautilus_trader.adapters.finam.common.constants import BASE_URL, RATE_LIMIT_DEFAULT
from nautilus_trader.adapters.finam.http.auth import JwtTokenManager
from nautilus_trader.adapters.finam.http.rate_limiter import RateLimiter
from nautilus_trader.common.component import Logger
from nautilus_trader.adapters.finam.common.constants import ENDPOINT_ASSETS


class FinamHttpClient:
    """
    Asynchronous HTTP client for Finam REST API.

    Features:
    - JWT token authentication (automatic header injection)
    - Rate limiting per endpoint (200 req/min default)
    - Built on httpx.AsyncClient
    - Graceful error handling

    Parameters
    ----------
    auth_manager : JwtTokenManager
        JWT token manager for authentication
    base_url : str, optional
        Base URL for API (default: https://api.finam.ru/v1)
    rate_limit : int, optional
        Max requests per minute per endpoint (default: 200)
    timeout : float, optional
        Request timeout in seconds (default: 30.0)
    logger : Logger, optional
        Logger instance for debug/error messages

    """

    def __init__(
        self,
        auth_manager: JwtTokenManager,
        base_url: str = BASE_URL,
        rate_limit: int = RATE_LIMIT_DEFAULT,
        timeout: float = 30.0,
        logger: Logger | None = None,
    ) -> None:
        self._auth = auth_manager
        self._base_url = base_url
        self._logger = logger

        # Initialize rate limiter
        self._rate_limiter = RateLimiter(
            max_requests=rate_limit,
            window_seconds=60,
            logger=logger,
        )

        # Initialize httpx client
        self._client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
        )
        self._timeout = timeout

        if self._logger:
            self._logger.info(
                f"FinamHttpClient initialized. Base URL: {base_url}, "
                f"Rate limit: {rate_limit} req/min",
            )

    async def _get_headers(self) -> dict[str, str]:
        """
        Get HTTP headers with JWT token.

        Returns
        -------
        dict[str, str]
            Headers dictionary with Authorization token

        """
        token = await self._auth.get_token()

        return {
            "Authorization": token,  # Note: NO "Bearer" prefix for Finam API
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Execute HTTP request with rate limiting and authentication.

        Parameters
        ----------
        method : str
            HTTP method (GET, POST, DELETE, etc.)
        endpoint : str
            API endpoint path (e.g., "/sessions", "/instruments")
        **kwargs : Any
            Additional arguments passed to httpx.request
            (params, json, data, headers, etc.)

        Returns
        -------
        httpx.Response
            HTTP response object

        Raises
        ------
        httpx.HTTPError
            If request fails (4xx, 5xx status codes)

        """
        # Apply rate limiting
        await self._rate_limiter.acquire(endpoint)

        # Get auth headers
        headers = await self._get_headers()

        # Merge with custom headers if provided
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        # Build full URL
        url = f"{self._base_url}{endpoint}"

        if self._logger:
            self._logger.debug(f"{method} {url}")

        # Execute request
        response = await self._client.request(
            method,
            url,
            headers=headers,
            **kwargs,
        )

        # Raise exception for error status codes
        response.raise_for_status()

        if self._logger:
            self._logger.debug(
                f"{method} {url} -> {response.status_code} "
                f"({len(response.content)} bytes)",
            )

        return response

    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """
        Выполняет GET запрос к Finam API.
        
        ВАЖНО: Для /assets использует pycurl (обход бага gRPC transcoder).
        Для остальных endpoints использует httpx.
        
        Args:
            endpoint: API endpoint (например, "/assets" или "/exchanges")
            params: Query параметры (опционально)
            
        Returns:
            httpx.Response: HTTP ответ
            
        Raises:
            RuntimeError: Если запрос не удался
        """
        # СПЕЦИАЛЬНАЯ ОБРАБОТКА для /assets endpoint
        if endpoint == ENDPOINT_ASSETS:
            return await self._get_via_pycurl(endpoint)

        # Остальные endpoints через httpx (как обычно)
        token = await self._auth.get_token()
        headers = {"Authorization": token}

        url = f"{self._base_url}{endpoint}"

        response = await self._client.get(
            url,
            headers=headers,
            params=params,
            timeout=self._timeout,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"HTTP {response.status_code} error from {endpoint}. "
                f"Response: {response.text[:500]}",
            )

        return response


    async def _get_via_pycurl(self, endpoint: str) -> httpx.Response:
        """
        GET запрос через pycurl (для обхода бага gRPC transcoder).
        
        Используется ТОЛЬКО для /assets endpoint.
        Возвращает httpx.Response для совместимости.
        """
        from nautilus_trader.adapters.finam.http.pycurl_wrapper import pycurl_get

        token = await self._auth.get_token()
        headers = {"Authorization": token}
        url = f"{self._base_url}{endpoint}"

        # Получаем dict через pycurl
        data = await pycurl_get(url, headers, timeout=self._timeout)

        # Преобразуем обратно в httpx.Response для совместимости
        # (чтобы не менять код в providers.py)
        import json
        mock_response = httpx.Response(
            status_code=200,
            headers={"content-type": "application/json"},
            content=json.dumps(data).encode("utf-8"),
            request=httpx.Request("GET", url),
        )

        return mock_response

    async def post(
        self,
        endpoint: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Execute POST request.

        Parameters
        ----------
        endpoint : str
            API endpoint path
        **kwargs : Any
            Additional arguments (json, data, headers, etc.)

        Returns
        -------
        httpx.Response
            HTTP response

        """
        return await self.request("POST", endpoint, **kwargs)

    async def delete(
        self,
        endpoint: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Execute DELETE request.

        Parameters
        ----------
        endpoint : str
            API endpoint path
        **kwargs : Any
            Additional arguments (headers, etc.)

        Returns
        -------
        httpx.Response
            HTTP response

        """
        return await self.request("DELETE", endpoint, **kwargs)

    async def close(self) -> None:
        """
        Close HTTP client and cleanup resources.

        Should be called during adapter shutdown.

        """
        await self._client.aclose()

        if self._logger:
            self._logger.info("FinamHttpClient closed")