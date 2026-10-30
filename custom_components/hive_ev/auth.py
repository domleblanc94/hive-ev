"""Cognito sign-in; no credentials are logged or used in polling."""
from __future__ import annotations

import asyncio
from typing import Any

import boto3

from apyhiveapi import Auth, SMS_REQUIRED
from apyhiveapi.api.hive_auth_async import long_to_hex
from apyhiveapi.helper.hive_exceptions import (
    HiveApiError, HiveInvalid2FACode, HiveInvalidPassword, HiveInvalidUsername,
)
from botocore.exceptions import BotoCoreError, ClientError
from botocore.config import Config

from .api import HiveEVAuthError, HiveEVConnectionError, tokens_from_result
from .const import COGNITO_CLIENT_ID, COGNITO_POOL_ID


class _PrivateAuth(Auth):
    """Use upstream SRP/MFA with fixed verified config and no auth-param logs."""

    def __init__(self, username: str, password: str) -> None:
        super().__init__(username, password)
        # The installed Hive app and public SSO bootstrap use these exact IDs.
        # Avoid upstream getLoginInfo's disabled certificate verification.
        self.api.getLoginInfo = lambda: {
            "UPID": COGNITO_POOL_ID, "CLIID": COGNITO_CLIENT_ID,
            "REGION": COGNITO_POOL_ID,
        }

    async def get_auth_params(self, is_device_login: bool = False) -> dict[str, str]:
        params = {"USERNAME": self.username, "SRP_A": long_to_hex(self.large_a_value)}
        if is_device_login:
            params["DEVICE_KEY"] = self.device_key
        return params

    async def async_init(self) -> None:
        """Pinned upstream initialization with bounded transport timeouts."""
        self.loop = asyncio.get_running_loop()
        self.data = self.api.getLoginInfo()
        # These are the exact private fields used by pinned HiveAuthAsync1.0.10.
        self._HiveAuthAsync__pool_id = COGNITO_POOL_ID
        self._HiveAuthAsync__client_id = COGNITO_CLIENT_ID
        self._HiveAuthAsync__region = COGNITO_POOL_ID.split("_")[0]
        self.client = await asyncio.to_thread(
            boto3.client, "cognito-idp", self._HiveAuthAsync__region,
            aws_access_key_id="ACCESS_KEY", aws_secret_access_key="SECRET_KEY",
            aws_session_token="SESSION_TOKEN",
            config=Config(connect_timeout=10, read_timeout=15,
                          retries={"total_max_attempts": 2, "mode": "standard"}),
        )

    async def async_close(self) -> None:
        client, self.client = self.client, None
        if client is not None:
            try:
                await asyncio.to_thread(client.close)
            except Exception:
                pass


def _raise_safe(error: Exception) -> None:
    """Do not preserve exception chains containing server messages or URLs."""
    if isinstance(error, ClientError):
        code = error.response.get("Error", {}).get("Code", "")
        if code in ("TooManyRequestsException", "InternalErrorException", "ServiceUnavailableException"):
            raise HiveEVConnectionError("Hive sign-in is temporarily unavailable") from None
        raise HiveEVAuthError("Hive sign-in was rejected") from None
    if isinstance(error, (BotoCoreError, HiveApiError, asyncio.TimeoutError, OSError)):
        raise HiveEVConnectionError("Cannot connect to Hive sign-in") from None
    if isinstance(error, (HiveInvalid2FACode, HiveInvalidPassword, HiveInvalidUsername)):
        raise HiveEVAuthError("Hive sign-in was rejected") from None
    raise HiveEVAuthError("Hive sign-in could not be completed") from None


class HiveEVLogin:
    """An interactive flow retains the password only until setup completes."""

    def __init__(self, username: str, password: str) -> None:
        self._auth = _PrivateAuth(username, password)
        self._result: dict[str, Any] = {}
        self._device_confirmed = False

    @property
    def requires_sms(self) -> bool:
        return self._result.get("ChallengeName") == SMS_REQUIRED

    @property
    def requires_registration(self) -> bool:
        return bool(self._result.get("AuthenticationResult", {}).get("NewDeviceMetadata"))

    @property
    def tokens(self) -> dict[str, Any]:
        return tokens_from_result(self._result)

    async def async_start(self) -> None:
        try:
            result = await self._auth.login()
            if not isinstance(result, dict) or not ("AuthenticationResult" in result or result.get("ChallengeName") == SMS_REQUIRED):
                raise HiveEVAuthError("Hive requires an unsupported sign-in challenge")
            self._result = result
        except Exception as error:
            _raise_safe(error)
        finally:
            await self._auth.async_close()

    async def async_sms(self, code: str) -> None:
        try:
            if self._auth.client is None:
                await self._auth.async_init()
            result = await self._auth.sms_2fa(code.strip(), self._result)
            if not isinstance(result, dict) or "AuthenticationResult" not in result:
                raise HiveEVAuthError("Hive verification code was rejected")
            self._result = result
        except Exception as error:
            _raise_safe(error)
        finally:
            await self._auth.async_close()

    async def async_register(self) -> dict[str, Any]:
        """Called only after explicit setup confirmation, never during polling."""
        try:
            if self._auth.client is None:
                await self._auth.async_init()
            auth_result = self._result["AuthenticationResult"]
            metadata = auth_result["NewDeviceMetadata"]
            # Same supported Cognito operations as Auth.device_registration.
            # Call directly so unexpected client errors cannot be swallowed by
            # upstream confirm_device's narrow error handling.
            group_key, device_key = metadata["DeviceGroupKey"], metadata["DeviceKey"]
            if not self._device_confirmed:
                verifier = await self._auth.generate_hash_device(group_key, device_key)
                await asyncio.to_thread(
                    self._auth.client.confirm_device,
                    AccessToken=auth_result["AccessToken"], DeviceKey=device_key,
                    DeviceName="Home Assistant Hive EV", DeviceSecretVerifierConfig=verifier,
                )
                self._device_confirmed = True
            await asyncio.to_thread(
                self._auth.client.update_device_status,
                AccessToken=auth_result["AccessToken"], DeviceKey=device_key,
                DeviceRememberedStatus="remembered",
            )
            tokens = self.tokens
            tokens["device_key"] = device_key
            return tokens
        except Exception as error:
            _raise_safe(error)
        finally:
            await self._auth.async_close()

    def clear_password(self) -> None:
        self._auth.password = ""


async def async_refresh_tokens(tokens: dict[str, Any]) -> dict[str, Any]:
    """Renew the existing grant once, without password/MFA or device writes."""
    auth = _PrivateAuth("", "")
    try:
        await auth.async_init()
        params = {"REFRESH_TOKEN": tokens["refresh_token"]}
        if tokens.get("device_key"):
            params["DEVICE_KEY"] = tokens["device_key"]
        # Same operation as upstream refresh_token, without its raw error logs.
        return await asyncio.to_thread(
            auth.client.initiate_auth, AuthFlow="REFRESH_TOKEN_AUTH",
            AuthParameters=params, ClientId=COGNITO_CLIENT_ID,
        )
    except Exception as error:
        _raise_safe(error)
    finally:
        await auth.async_close()
