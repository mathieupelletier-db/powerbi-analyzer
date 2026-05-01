"""MSAL-based token resolver for Power BI REST."""
from __future__ import annotations

import os
from pathlib import Path

import msal  # type: ignore[import-untyped]

CACHE_PATH = Path.home() / ".cache" / "pba" / "msal_cache.json"
SCOPES = ["https://analysis.windows.net/powerbi/api/.default"]


def _persistent_cache() -> msal.SerializableTokenCache:
    cache = msal.SerializableTokenCache()
    if CACHE_PATH.exists():
        cache.deserialize(CACHE_PATH.read_text())
    return cache


def _save_cache(cache: msal.SerializableTokenCache) -> None:
    if cache.has_state_changed:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(cache.serialize())
        CACHE_PATH.chmod(0o600)


def get_token(*, tenant_id: str, auth: str = "device_code", client_id: str | None = None) -> str:
    if auth == "service_principal":
        client_id = client_id or os.environ["PBI_CLIENT_ID"]
        secret = os.environ["PBI_CLIENT_SECRET"]
        app = msal.ConfidentialClientApplication(
            client_id=client_id,
            client_credential=secret,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
        )
        result = app.acquire_token_for_client(scopes=SCOPES)
    else:
        client_id = client_id or "1950a258-227b-4e31-a9cf-717495945fc2"  # azure-cli first-party
        cache = _persistent_cache()
        app = msal.PublicClientApplication(
            client_id=client_id,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
            token_cache=cache,
        )
        accounts = app.get_accounts()
        result = app.acquire_token_silent(SCOPES, account=accounts[0]) if accounts else None
        if not result:
            flow = app.initiate_device_flow(scopes=SCOPES)
            print(flow["message"])
            result = app.acquire_token_by_device_flow(flow)
        _save_cache(cache)
    if "access_token" not in result:
        raise RuntimeError(f"auth failed: {result.get('error_description')}")
    return str(result["access_token"])
