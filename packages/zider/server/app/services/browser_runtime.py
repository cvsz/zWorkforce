from __future__ import annotations

import os

from .agent_runner import AgentRunner, BrowserAutomationUnavailable
from .browser_executor import PinnedBrowserExecutor
from .playwright_runtime import PlaywrightReadOnlyTransport


async def configure_browser_runtime() -> str:
    """Configure the explicitly selected browser runtime.

    Disabled is the safe default. Enabling Playwright performs a startup probe so
    a missing Chromium binary fails startup instead of producing fake success.
    Mutating actions remain denied because no approval authorizer is installed in
    this slice.
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
    AgentRunner.configure(executor=executor, timeout_seconds=timeout)
    return "playwright-readonly"
