"""
Base client class with connection state management and reconnection logic.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

import httpx

from models import ConnectionState, ClientHealth


logger = logging.getLogger(__name__)


class BaseClient(ABC):
    """
    Abstract base class for API clients.

    Provides:
    - Connection state tracking
    - Automatic reconnection with exponential backoff
    - Request/error counting for health monitoring
    """

    # Reconnection settings
    INITIAL_BACKOFF = 5  # seconds
    MAX_BACKOFF = 300  # 5 minutes
    BACKOFF_MULTIPLIER = 2

    def __init__(self, name: str, timeout: float = 30.0):
        self.name = name
        self.timeout = timeout
        self._state = ConnectionState.DISCONNECTED
        self._last_error: Optional[str] = None
        self._request_count = 0
        self._error_count = 0
        self._client: Optional[httpx.AsyncClient] = None
        self._backoff = self.INITIAL_BACKOFF
        self._reconnect_task: Optional[asyncio.Task] = None

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if required configuration is present."""
        pass

    @property
    def state(self) -> ConnectionState:
        """Current connection state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._state == ConnectionState.CONNECTED

    def get_health(self) -> ClientHealth:
        """Get health status for this client."""
        return ClientHealth(
            name=self.name,
            configured=self.is_configured,
            connected=self.is_connected,
            state=self._state,
            last_error=self._last_error,
            request_count=self._request_count,
            error_count=self._error_count,
        )

    async def connect(self) -> bool:
        """
        Establish connection to the service.
        Returns True if connection successful.
        """
        if not self.is_configured:
            logger.info(f"{self.name}: Not configured, skipping connection")
            return False

        self._state = ConnectionState.CONNECTING
        try:
            self._client = await self._create_client()
            success = await self._test_connection()
            if success:
                self._state = ConnectionState.CONNECTED
                self._backoff = self.INITIAL_BACKOFF
                logger.info(f"{self.name}: Connected successfully")
                return True
            else:
                self._state = ConnectionState.FAILED
                return False
        except Exception as e:
            self._last_error = str(e)
            self._state = ConnectionState.FAILED
            logger.error(f"{self.name}: Connection failed: {e}")
            return False

    async def disconnect(self) -> None:
        """Close the connection."""
        if self._reconnect_task:
            self._reconnect_task.cancel()
            self._reconnect_task = None

        if self._client:
            await self._client.aclose()
            self._client = None

        self._state = ConnectionState.DISCONNECTED
        logger.info(f"{self.name}: Disconnected")

    async def reconnect(self) -> None:
        """Attempt to reconnect with exponential backoff."""
        if self._state == ConnectionState.RECONNECTING:
            return  # Already reconnecting

        self._state = ConnectionState.RECONNECTING
        logger.info(f"{self.name}: Reconnecting in {self._backoff}s...")

        await asyncio.sleep(self._backoff)

        if self._client:
            await self._client.aclose()
            self._client = None

        success = await self.connect()
        if not success:
            # Increase backoff for next attempt
            self._backoff = min(self._backoff * self.BACKOFF_MULTIPLIER, self.MAX_BACKOFF)
            # Schedule another reconnection attempt
            self._reconnect_task = asyncio.create_task(self.reconnect())

    @abstractmethod
    async def _create_client(self) -> httpx.AsyncClient:
        """Create the HTTP client with appropriate auth."""
        pass

    @abstractmethod
    async def _test_connection(self) -> bool:
        """Test that connection is working."""
        pass

    async def request(
        self,
        method: str,
        path: str,
        **kwargs,
    ) -> Optional[Any]:
        """
        Make an HTTP request with error handling.

        Returns None if request fails (graceful degradation).
        """
        if not self._client or not self.is_connected:
            return None

        self._request_count += 1
        url = path if path.startswith("http") else path

        try:
            response = await self._client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            self._error_count += 1
            self._last_error = f"HTTP {e.response.status_code}: {e.response.text[:100]}"
            logger.error(f"{self.name}: {self._last_error}")
            if e.response.status_code in (401, 403):
                # Auth error - trigger reconnect
                asyncio.create_task(self.reconnect())
            return None
        except httpx.RequestError as e:
            self._error_count += 1
            self._last_error = f"Request error: {e}"
            logger.error(f"{self.name}: {self._last_error}")
            # Connection error - trigger reconnect
            asyncio.create_task(self.reconnect())
            return None
        except Exception as e:
            self._error_count += 1
            self._last_error = f"Unexpected error: {e}"
            logger.error(f"{self.name}: {self._last_error}")
            return None

    async def get(self, path: str, **kwargs) -> Optional[Any]:
        """Make a GET request."""
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs) -> Optional[Any]:
        """Make a POST request."""
        return await self.request("POST", path, **kwargs)

    async def delete(self, path: str, **kwargs) -> Optional[Any]:
        """Make a DELETE request."""
        return await self.request("DELETE", path, **kwargs)
