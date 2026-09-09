"""Interactive authentication for the Monarch Money MCP server.

Uses MCP elicitation so credentials flow client-UI → server directly over
the protocol — they never appear in tool arguments or the model's context.

Codex and some other MCP hosts do not support elicitation reliably. Those
clients should authenticate with ``login_setup.py`` instead.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context
from monarchmoney import MonarchMoney, RequireMFAException
from pydantic import BaseModel, Field

from monarch_mcp_server.secure_session import secure_session


_CANCELLED = object()

_TERMINAL_SETUP_HINT = (
    "Interactive login is not available in this client. Run "
    "`python login_setup.py` from the monarch-mcp-server repo, then retry. "
    "The saved session is shared across Codex, Claude Desktop, and Claude Code."
)


def _elicit_supported(ctx: Context) -> bool:
    return hasattr(ctx, "elicit")


def _field_value(data: Any, field: str) -> Any:
    if isinstance(data, dict):
        return data.get(field)
    return getattr(data, field, None)


def _extract_accepted_data(form_result: Any, *required_fields: str) -> Any:
    """Return accepted form data, ``_CANCELLED``, or ``None`` if unusable.

    Codex has been observed to reject elicitation schemas or accept with empty
    ``content``. Treat those as "use the terminal setup script" rather than a
    successful login.
    """
    if form_result is None:
        return None
    if getattr(form_result, "action", None) != "accept":
        return _CANCELLED
    data = getattr(form_result, "data", None)
    if data is None:
        return None
    for field in required_fields:
        value = _field_value(data, field)
        if value is None:
            return None
    return data


async def _elicit(ctx: Context, message: str, schema: type[BaseModel]) -> Any:
    try:
        return await ctx.elicit(message=message, schema=schema)
    except Exception:
        return None


class LoginForm(BaseModel):
    email: str = Field(description="Monarch Money email address")
    password: str = Field(description="Monarch Money password")


class MFAForm(BaseModel):
    mfa_code: str = Field(description="Monarch Money MFA code")


class TokenForm(BaseModel):
    token: str = Field(
        description=(
            "Monarch Money session token. Grab it from browser DevTools → "
            "Application → Local Storage for app.monarchmoney.com, key 'token'."
        ),
    )


async def login_interactive(ctx: Context) -> str:
    if not _elicit_supported(ctx):
        return _TERMINAL_SETUP_HINT
    form_result = await _elicit(ctx, "Sign in to Monarch Money.", LoginForm)
    form = _extract_accepted_data(form_result, "email", "password")
    if form is _CANCELLED:
        return "Login cancelled."
    if form is None:
        return _TERMINAL_SETUP_HINT

    email = _field_value(form, "email")
    password = _field_value(form, "password")

    mm = MonarchMoney()
    try:
        await mm.login(
            email,
            password,
            use_saved_session=False,
            save_session=False,
        )
    except RequireMFAException:
        mfa_result = await _elicit(
            ctx, "Enter your Monarch Money MFA code.", MFAForm
        )
        mfa = _extract_accepted_data(mfa_result, "mfa_code")
        if mfa is _CANCELLED:
            return "Login cancelled."
        if mfa is None:
            return _TERMINAL_SETUP_HINT
        await mm.multi_factor_authenticate(
            email, password, _field_value(mfa, "mfa_code")
        )

    secure_session.save_authenticated_session(mm)
    return "Logged in. Session saved to system keyring."


async def login_with_token_interactive(ctx: Context) -> str:
    if not _elicit_supported(ctx):
        return _TERMINAL_SETUP_HINT
    form_result = await _elicit(
        ctx, "Paste your Monarch Money session token.", TokenForm
    )
    form = _extract_accepted_data(form_result, "token")
    if form is _CANCELLED:
        return "Login cancelled."
    if form is None:
        return _TERMINAL_SETUP_HINT

    token = str(_field_value(form, "token") or "").strip()
    if not token:
        return "Empty token — aborting."

    mm = MonarchMoney(token=token)
    await mm.get_subscription_details()
    secure_session.save_token(token)
    return "Session token saved to system keyring."


async def logout() -> str:
    secure_session.delete_token()
    return "Cleared stored Monarch session."
