from __future__ import annotations

import os

from .agent_runner import AgentRunner, BrowserAutomationUnavailable
from .browser_approval import ZWorkforceMutationApprovalAdapter
from .browser_executor import PinnedBrowserExecutor
from .playwright_runtime import PlaywrightReadOnlyTransport


async def configure_browser_runtime() -> str:
    """Configure the explicitly selected browser runtime.

    Disabled is the safe default. Enabling Playwright performs a startup probe so
    a missing Chromium binary fails startup instead of producing fake success.
    The optional zWorkforce approval adapter validates durable control-plane
    approvals for mutating actions, but the current Playwright transport remains
    read-only until the separate approved-mutation execution slice lands.
    """

    runtime = os.getenv("ZIDER_BROWSER_RUNTIME", "disabled").strip().lower()
    if runtime in {"", "disabled", "off", "none"}:
        AgentRunner.reset()
        return "disabled"
    if runtime != "playwright":
        raise BrowserAutomationUnavailable("unsupported Zider browser runtime")

    transport = PlaywrightReadOnlyTransport(
        headless=os.getenv("ZIDER_BROWSER_HEADLESS", "1").strip().lower() not in {"0", "false", "no"}
    )
    await transport.probe()
    timeout = int(os.getenv("ZIDER_BROWSER_TIMEOUT_SECONDS", "30"))
    executor = PinnedBrowserExecutor(transport, timeout_seconds=timeout)

    approval_mode = os.getenv("ZIDER_BROWSER_APPROVAL_MODE", "disabled").strip().lower()
    approval_authorizer = None
    if approval_mode not in {"", "disabled", "off", "none"}:
        if approval_mode != "zworkforce":
            raise BrowserAutomationUnavailable("unsupported Zider browser approval mode")
        approval_ttl = int(os.getenv("ZIDER_BROWSER_APPROVAL_TTL_SECONDS", "600"))
        approval_authorizer = ZWorkforceMutationApprovalAdapter(ttl_seconds=approval_ttl).authorize

    AgentRunner.configure(
        executor=executor,
        approval_authorizer=approval_authorizer,
        timeout_seconds=timeout,
    )
    return "playwright-readonly"
