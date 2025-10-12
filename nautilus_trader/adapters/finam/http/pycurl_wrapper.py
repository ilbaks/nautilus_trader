
"""
Async обёртка для pycurl для обхода бага gRPC transcoder в Finam API.

Используется ТОЛЬКО для endpoint /assets, т.к. большой ответ вызывает
ошибку "transcoder's internal buffer size exceeds the configured limit".

pycurl (libcurl) успешно обходит этот баг, httpx - нет.
"""

import asyncio
import json
from io import BytesIO
from typing import Any

import pycurl


class PycurlAsyncClient:
    """
    Async обёртка над pycurl для GET запросов.
    
    ВАЖНО: Используется ТОЛЬКО для /assets endpoint!
    Для остальных endpoints используй httpx.AsyncClient.
    """

    def __init__(self, timeout: float = 60.0, verbose: bool = False):
        """
        Args:
            timeout: Timeout для запросов в секундах
            verbose: Включить verbose режим pycurl (для отладки)
        """
        self._timeout = timeout
        self._verbose = verbose

    async def get(
        self,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Async GET запрос через pycurl.
        
        Args:
            url: Полный URL запроса
            headers: Словарь заголовков
            
        Returns:
            dict: Распарсенный JSON ответ
            
        Raises:
            pycurl.error: Если запрос не удался
            json.JSONDecodeError: Если ответ не JSON
            RuntimeError: Если HTTP код не 200
        """
        # Выполняем синхронный pycurl в отдельном потоке
        return await asyncio.to_thread(
            self._sync_get,
            url,
            headers or {},
        )

    def _sync_get(
        self,
        url: str,
        headers: dict[str, str],
    ) -> dict[str, Any]:
        """
        Синхронный GET запрос через pycurl.
        
        Вызывается из asyncio.to_thread().
        """
        buffer = BytesIO()
        c = pycurl.Curl()

        try:
            # Настройка запроса
            c.setopt(c.URL, url)
            c.setopt(c.WRITEDATA, buffer)
            c.setopt(c.TIMEOUT, int(self._timeout))

            # Заголовки (pycurl требует список строк)
            header_list = [f"{key}: {value}" for key, value in headers.items()]
            c.setopt(c.HTTPHEADER, header_list)

            # Verbose режим (для отладки)
            if self._verbose:
                c.setopt(c.VERBOSE, True)

            # Выполнение запроса
            c.perform()

            # Проверка HTTP кода
            http_code = c.getinfo(c.RESPONSE_CODE)
            if http_code != 200:
                body = buffer.getvalue().decode("utf-8")
                raise RuntimeError(
                    f"HTTP {http_code} error from {url}. Response: {body[:500]}",
                )

            # Парсинг JSON
            body = buffer.getvalue()
            data = json.loads(body.decode("utf-8"))

            return data

        finally:
            c.close()


# Удобная функция для одиночных запросов
async def pycurl_get(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: float = 60.0,
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Удобная функция для одиночного GET запроса.
    
    Example:
        >>> headers = {"Authorization": token}
        >>> data = await pycurl_get("https://api.finam.ru/v1/assets", headers)
        >>> print(len(data["assets"]))
        15745
    """
    client = PycurlAsyncClient(timeout=timeout, verbose=verbose)
    return await client.get(url, headers)