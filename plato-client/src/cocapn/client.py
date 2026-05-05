"""Synchronous and asynchronous PLATO clients."""

from __future__ import annotations

import json
from typing import Any

import httpx

from cocapn.types import PLATOError, Tile

_DEFAULT_BASE_URL = "http://147.224.38.131:8847"
_DEFAULT_TIMEOUT = 30.0


def _raise_for_status(response: httpx.Response) -> None:
    """Raise :class:`PLATOError` on non-2xx responses."""
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        body: Any = None
        try:
            body = response.json()
        except Exception:
            body = response.text
        raise PLATOError(
            f"HTTP {response.status_code}: {response.reason_phrase}",
            status_code=response.status_code,
            response_body=body,
        ) from exc


class PLATOClient:
    """Synchronous client for the PLATO knowledge server.

    Parameters
    ----------
    base_url:
        Root URL of the PLATO server. Defaults to the public instance.
    timeout:
        Request timeout in seconds.
    """

    def __init__(self, base_url: str = _DEFAULT_BASE_URL, timeout: float = _DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> Any:
        """Perform an HTTP request and return the decoded JSON body."""
        try:
            response = self._client.request(method, path, params=params, json=json_data)
        except httpx.NetworkError as exc:
            raise PLATOError(f"Network error: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise PLATOError(f"Request timed out after {self.timeout}s") from exc

        _raise_for_status(response)

        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise PLATOError("Invalid JSON in response") from exc

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def health(self) -> dict[str, Any]:
        """Check server health.

        Returns
        -------
        dict
            Server health payload (shape depends on the PLATO server version).
        """
        return self._request("GET", "/health")

    def list_rooms(self, prefix: str | None = None) -> list[str]:
        """List available rooms, optionally filtered by prefix.

        Parameters
        ----------
        prefix:
            If given, only rooms whose names start with this string are returned.

        Returns
        -------
        list[str]
            Room names.
        """
        params: dict[str, Any] = {}
        if prefix is not None:
            params["prefix"] = prefix
        data = self._request("GET", "/rooms", params=params)
        if isinstance(data, list):
            return [str(r) for r in data]
        if isinstance(data, dict):
            return [str(r) for r in data.get("rooms", [])]
        return []

    def query(self, room: str, query: str | None = None, *, limit: int = 10) -> list[Tile]:
        """Query tiles from a room.

        Parameters
        ----------
        room:
            Name of the room to query.
        query:
            Optional text query. When omitted the server may return recent tiles.
        limit:
            Maximum number of tiles to return (default 10).

        Returns
        -------
        list[Tile]
            Matching tiles.
        """
        params: dict[str, Any] = {"room": room, "limit": limit}
        if query is not None:
            params["q"] = query

        data = self._request("GET", "/query", params=params)

        raw_tiles: list[dict[str, Any]] = []
        if isinstance(data, list):
            raw_tiles = data
        elif isinstance(data, dict):
            raw_tiles = data.get("tiles", data.get("results", []))

        return [Tile.from_dict(t) for t in raw_tiles]

    def submit(
        self,
        domain: str,
        question: str,
        answer: str,
        source: str,
        confidence: float,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Submit a tile through the gate.

        Parameters
        ----------
        domain:
            Knowledge domain (e.g. ``"math"``, ``"marine"``).
        question:
            The question / key this tile answers.
        answer:
            The answer / value.
        source:
            Origin or authority for this tile.
        confidence:
            Confidence score in the range ``[0.0, 1.0]``.
        tags:
            Optional list of classification tags.

        Returns
        -------
        dict
            Server acknowledgement, typically containing ``tile_id`` or ``status``.
        """
        payload: dict[str, Any] = {
            "domain": domain,
            "question": question,
            "answer": answer,
            "source": source,
            "confidence": confidence,
        }
        if tags is not None:
            payload["tags"] = tags

        return self._request("POST", "/gate", json_data=payload)

    def verify(self, tile_id: str) -> dict[str, Any]:
        """Verify a tile against server-side constraints.

        .. note::
           This is currently a stub on the server side; the client faithfully
           forwards the request and returns whatever the server responds.

        Parameters
        ----------
        tile_id:
            Identifier of the tile to verify.

        Returns
        -------
        dict
            Verification result.
        """
        return self._request("GET", f"/verify/{tile_id}")

    def close(self) -> None:
        """Close the underlying HTTP client and release resources."""
        self._client.close()

    def __enter__(self) -> PLATOClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class AsyncPLATOClient:
    """Asynchronous client for the PLATO knowledge server.

    Uses ``httpx.AsyncClient`` under the hood. All methods are coroutines.

    Parameters
    ----------
    base_url:
        Root URL of the PLATO server. Defaults to the public instance.
    timeout:
        Request timeout in seconds.
    """

    def __init__(self, base_url: str = _DEFAULT_BASE_URL, timeout: float = _DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> Any:
        """Perform an async HTTP request and return the decoded JSON body."""
        try:
            response = await self._client.request(method, path, params=params, json=json_data)
        except httpx.NetworkError as exc:
            raise PLATOError(f"Network error: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise PLATOError(f"Request timed out after {self.timeout}s") from exc

        _raise_for_status(response)

        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise PLATOError("Invalid JSON in response") from exc

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def health(self) -> dict[str, Any]:
        """Check server health.

        Returns
        -------
        dict
            Server health payload.
        """
        return await self._request("GET", "/health")

    async def list_rooms(self, prefix: str | None = None) -> list[str]:
        """List available rooms, optionally filtered by prefix.

        Parameters
        ----------
        prefix:
            If given, only rooms whose names start with this string are returned.

        Returns
        -------
        list[str]
            Room names.
        """
        params: dict[str, Any] = {}
        if prefix is not None:
            params["prefix"] = prefix
        data = await self._request("GET", "/rooms", params=params)
        if isinstance(data, list):
            return [str(r) for r in data]
        if isinstance(data, dict):
            return [str(r) for r in data.get("rooms", [])]
        return []

    async def query(self, room: str, query: str | None = None, *, limit: int = 10) -> list[Tile]:
        """Query tiles from a room.

        Parameters
        ----------
        room:
            Name of the room to query.
        query:
            Optional text query.
        limit:
            Maximum number of tiles to return (default 10).

        Returns
        -------
        list[Tile]
            Matching tiles.
        """
        params: dict[str, Any] = {"room": room, "limit": limit}
        if query is not None:
            params["q"] = query

        data = await self._request("GET", "/query", params=params)

        raw_tiles: list[dict[str, Any]] = []
        if isinstance(data, list):
            raw_tiles = data
        elif isinstance(data, dict):
            raw_tiles = data.get("tiles", data.get("results", []))

        return [Tile.from_dict(t) for t in raw_tiles]

    async def submit(
        self,
        domain: str,
        question: str,
        answer: str,
        source: str,
        confidence: float,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Submit a tile through the gate.

        Parameters
        ----------
        domain:
            Knowledge domain.
        question:
            The question / key this tile answers.
        answer:
            The answer / value.
        source:
            Origin or authority for this tile.
        confidence:
            Confidence score in the range ``[0.0, 1.0]``.
        tags:
            Optional list of classification tags.

        Returns
        -------
        dict
            Server acknowledgement.
        """
        payload: dict[str, Any] = {
            "domain": domain,
            "question": question,
            "answer": answer,
            "source": source,
            "confidence": confidence,
        }
        if tags is not None:
            payload["tags"] = tags

        return await self._request("POST", "/gate", json_data=payload)

    async def verify(self, tile_id: str) -> dict[str, Any]:
        """Verify a tile against server-side constraints.

        Parameters
        ----------
        tile_id:
            Identifier of the tile to verify.

        Returns
        -------
        dict
            Verification result.
        """
        return await self._request("GET", f"/verify/{tile_id}")

    async def close(self) -> None:
        """Close the underlying async HTTP client and release resources."""
        await self._client.aclose()

    async def __aenter__(self) -> AsyncPLATOClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()
