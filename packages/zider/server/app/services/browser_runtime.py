from __future__ import annotations

import os

from .agent_runner import AgentRunner, BrowserAutomationUnavailable
from .browser_approval import ZWorkforceMutationApprovalAdapter
from .browser_effects import DurableBrowserEffectExecutor
from .browser_executor import PinnedBrowserExecutor
from .playwright_runtime import PlaywrightReadOnlyTransport


async def configure_browser_runtime() -> str:
    """Configure the explicitly selected browser runtime.

    Disabled is the safe default. Mutating click/submit execution requires both
    durable zWorkforce approval validation and durable browser-effect fencing.
    Unknown effects are never automatically replayed. Upload remains fail-closed
    until the governed artifact-content boundary is wired.
    """

    runtime = os.getenv("ZIDER_BROWSER_RUNTIME", "disabled").strip().lower()
    if runtime in {"", "disabled", "off", "none"}:
        AgentRunner.reset()
        return "disabled"
    if runtime != "playwright":
        raise BrowserAutomationUnavailable("unsupported Zider browser runtime")

    approval_mode = os.getenv("ZIDER_BROWSER_APPROVAL_MODE", "disabled").strip().lower()
    approval_authorizer = None
    if approval_mode not in {"", "disabled", "off", "none"}:
        if approval_mode != "zworkforce":
            raise BrowserAutomationUnavailable("unsupported Zider browser approval mode")
        approval_ttl = int(os.getenv("ZIDER_BROWSER_APPROVAL_TTL_SECONDS", "600"))
        approval_authorizer = ZWorkforceMutationApprovalAdapter(ttl_seconds=approval_ttl).authorize

    transport = PlaywrightReadOnlyTransport(
        headless=os.getenv("ZIDER_BROWSER_HEADLESS", "1").strip().lower() not in {"0", "false", "no"},
        allow_mutations=approval_authorizer is not None,
    )
    await transport.probe()
    timeout = int(os.getenv("ZIDER_BROWSER_TIMEOUT_SECONDS", "30"))
    max_redirects = int(os.getenv("ZIDER_BROWSER_MAX_REDIRECTS", "5"))
    executor = PinnedBrowserExecutor(
        transport,
        timeout_seconds=timeout,
        redirect_validator=AgentRunner._validate_url,
        max_redirects=max_redirects,
    )
    if approval_authorizer is not None:
        executor = DurableBrowserEffectExecutor(executor)

    AgentRunner.configure(
        executor=executor,
        approval_authorizer=approval_authorizer,
        timeout_seconds=timeout,
    )
    return "playwright-governed" if approval_authorizer is not None else "playwright-readonly"
