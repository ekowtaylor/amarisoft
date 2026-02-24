"""HTTP client for Amarisoft REST API service."""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .exceptions import (
    APIError,
    AuthenticationError,
    ConnectionError,
    HTTPClientError,
    TimeoutError,
)


class HTTPClient:
    """Low-level HTTP client for the Amarisoft REST API.

    Handles HTTP requests, retries, timeouts, and error handling.

    Args:
        base_url: Base URL of the REST API service (e.g., "http://192.168.1.80:9010").
        timeout: Request timeout in seconds.
        retries: Number of retries for failed requests.
        api_key: Optional API key for authentication.

    Example::

        client = HTTPClient("http://192.168.1.80:9010")
        response = client.get("/enb/stats")
        print(response)
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        retries: int = 3,
        api_key: str | None = None,
    ):
        # Normalize base URL
        if not base_url.startswith(("http://", "https://")):
            base_url = f"http://{base_url}"
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api_key = api_key

        # Create session with retry logic
        self._session = requests.Session()

        retry_strategy = Retry(
            total=retries,
            backoff_factor=0.5,
            status_forcelist=[502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

        # Set default headers
        self._session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

        if api_key:
            self._session.headers["X-API-Key"] = api_key

    def _build_url(self, endpoint: str) -> str:
        """Build full URL from endpoint."""
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"
        return f"{self.base_url}{endpoint}"

    def _handle_response(self, response: requests.Response) -> dict[str, Any]:
        """Handle API response and raise appropriate errors."""
        try:
            data = response.json()
        except ValueError:
            data = {"raw": response.text}

        if response.status_code == 401:
            raise AuthenticationError(
                data.get("error", "Authentication failed")
            )

        if response.status_code >= 400:
            raise APIError(
                message=data.get("error", f"HTTP {response.status_code}"),
                status_code=response.status_code,
                error_code=data.get("error_code"),
                detail=data.get("detail"),
            )

        return data

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a GET request.

        Args:
            endpoint: API endpoint (e.g., "/enb/stats").
            params: Optional query parameters.

        Returns:
            JSON response data.

        Raises:
            ConnectionError: If connection fails.
            TimeoutError: If request times out.
            APIError: If API returns an error.
        """
        try:
            response = self._session.get(
                self._build_url(endpoint),
                params=params,
                timeout=self.timeout,
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Failed to connect to {self.base_url}: {e}") from e
        except requests.exceptions.Timeout as e:
            raise TimeoutError(f"Request to {endpoint} timed out") from e
        except requests.exceptions.RequestException as e:
            raise HTTPClientError(f"Request failed: {e}") from e

    def post(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a POST request.

        Args:
            endpoint: API endpoint.
            data: Request body data.
            params: Optional query parameters.

        Returns:
            JSON response data.
        """
        try:
            response = self._session.post(
                self._build_url(endpoint),
                json=data,
                params=params,
                timeout=self.timeout,
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Failed to connect to {self.base_url}: {e}") from e
        except requests.exceptions.Timeout as e:
            raise TimeoutError(f"Request to {endpoint} timed out") from e
        except requests.exceptions.RequestException as e:
            raise HTTPClientError(f"Request failed: {e}") from e

    def put(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a PUT request."""
        try:
            response = self._session.put(
                self._build_url(endpoint),
                json=data,
                timeout=self.timeout,
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Failed to connect to {self.base_url}: {e}") from e
        except requests.exceptions.Timeout as e:
            raise TimeoutError(f"Request to {endpoint} timed out") from e
        except requests.exceptions.RequestException as e:
            raise HTTPClientError(f"Request failed: {e}") from e

    def delete(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a DELETE request."""
        try:
            response = self._session.delete(
                self._build_url(endpoint),
                params=params,
                timeout=self.timeout,
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Failed to connect to {self.base_url}: {e}") from e
        except requests.exceptions.Timeout as e:
            raise TimeoutError(f"Request to {endpoint} timed out") from e
        except requests.exceptions.RequestException as e:
            raise HTTPClientError(f"Request failed: {e}") from e

    def health_check(self) -> dict[str, Any]:
        """Check if the REST API service is healthy.

        Returns:
            Health status response.
        """
        return self.get("/health")

    def close(self):
        """Close the HTTP session."""
        self._session.close()

    def __enter__(self) -> "HTTPClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"HTTPClient({self.base_url!r})"
