from __future__ import annotations

import os

from .agent_runner import AgentRunner, BrowserAction, BrowserAutomationUnavailable
from .artifact_content import GovernedArtifactContentLoader
from .browser_approval import ZWorkforceMutationApprovalAdapter
from .browser_effects import DurableBrowserEffectExecutor
from .browser_executor import PinnedBrowserExecutor
from .playwright_runtime import PlaywrightReadOnlyTransport
from .zworkforce_bridge import ZWorkforceBridge

_CANCELED_TASK_STATES = {"canceled", "failed", "dead_letter"}


async def _approval_cancel_observer(action: BrowserAction) -> bool:
    """Observe a task cancellation that raced with browser mutation execution.

    Fail-soft by design: this is a post-execution race-window guard, not an
    authorization gate, so an unreachable control plane must not block a
    completed mutation from being recorded.
    """
    try:
        task = await ZWorkforceBridge.get_task(action.approval_task_id)
    except Exception:
        return False
    return bool(task.get("cancel_requested")) or str(task.get("status") or "").strip().lower() in _CANCELED_TASK_STATES


async def configure_browser_runtime() -> str:
    """Configure the explicitly selected browser runtime.

    Disabled is the safe default. Mutations require durable zWorkforce approval
    validation and durable browser-effect fencing. Upload content is retrieved
    only through the authenticated tenant-scoped artifact-content API; raw host
    filesystem paths are never accepted.
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

    artifact_loader = GovernedArtifactContentLoader() if approval_authorizer is not None else None
    evidence_screenshots = os.getenv("ZIDER_BROWSER_EVIDENCE_SCREENSHOTS", "0").strip().lower() in {"1", "true", "yes", "on"}
    transport = PlaywrightReadOnlyTransport(
        headless=os.getenv("ZIDER_BROWSER_HEADLESS", "1").strip().lower() not in {"0", "false", "no"},
        allow_mutations=approval_authorizer is not None,
        artifact_loader=artifact_loader,
        evidence_screenshots=evidence_screenshots,
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
        executor = DurableBrowserEffectExecutor(executor, cancel_checker=_approval_cancel_observer)

    AgentRunner.configure(
        executor=executor,
        approval_authorizer=approval_authorizer,
        timeout_seconds=timeout,
    )
    return "playwright-governed" if approval_authorizer is not None else "playwright-readonly"
