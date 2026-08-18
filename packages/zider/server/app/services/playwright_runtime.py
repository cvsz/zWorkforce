from __future__ import annotations

import base64
from typing import Any, Awaitable, Callable, Mapping
from urllib.parse import urlsplit

from .agent_runner import (
    BrowserAction,
    BrowserAutomationUnavailable,
    BrowserPolicyError,
    MUTATING_ACTIONS,
    READ_ONLY_ACTIONS,
)


MAX_SCREENSHOT_BYTES = 4 * 1024 * 1024
ArtifactLoader = Callable[[str], Awaitable[Mapping[str, Any]]]


def _effective_port(parsed) -> int:
    try:
        if parsed.port is not None:
            return int(parsed.port)
    except ValueError as exc:
        raise BrowserPolicyError("browser URL contains an invalid port") from exc
    return 443 if parsed.scheme == "https" else 80


def _origin(parsed) -> tuple[str, str, int]:
    return (
        parsed.scheme.lower(),
        (parsed.hostname or "").lower().rstrip("."),
        _effective_port(parsed),
    )


def _encode_screenshot(data: bytes) -> dict[str, object]:
    if not isinstance(data, (bytes, bytearray)):
        raise BrowserAutomationUnavailable("Playwright screenshot returned invalid data")
    raw = bytes(data)
    if not raw:
        raise BrowserAutomationUnavailable("Playwright screenshot returned empty data")
    if len(raw) > MAX_SCREENSHOT_BYTES:
        raise BrowserAutomationUnavailable("Playwright screenshot exceeds the configured response bound")
    return {
        "ok": True,
        "mime_type": "image/png",
        "bytes": len(raw),
        "image_base64": base64.b64encode(raw).decode("ascii"),
    }


async def _execute_approved_mutation(
    page,
    action: BrowserAction,
    timeout_ms: int,
    artifact_loader: ArtifactLoader | None,
) -> Mapping[str, object]:
    locator = page.locator(action.selector).first
    if action.kind == "click":
        await locator.click(timeout=timeout_ms)
        return {"ok": True, "action": "click"}
    if action.kind == "submit":
        await locator.evaluate(
            """el => {
                const form = el.tagName === 'FORM' ? el : el.form;
                if (!form) throw new Error('submit selector must resolve to a form or form control');
                if (typeof form.requestSubmit === 'function') form.requestSubmit();
                else form.submit();
            }"""
        )
        return {"ok": True, "action": "submit"}
    if action.kind == "upload":
        if artifact_loader is None:
            raise BrowserPolicyError("browser upload requires the governed artifact-content adapter")
        artifact = dict(await artifact_loader(action.artifact_id))
        name = str(artifact.get("name") or "upload.bin")[:255]
        mime_type = str(artifact.get("mime_type") or "application/octet-stream")[:255]
        buffer = artifact.get("buffer")
        digest = str(artifact.get("sha256") or "")
        if not isinstance(buffer, (bytes, bytearray)) or not buffer:
            raise BrowserPolicyError("governed artifact content is empty or invalid")
        await locator.set_input_files(
            {"name": name, "mimeType": mime_type, "buffer": bytes(buffer)},
            timeout=timeout_ms,
        )
        return {
            "ok": True,
            "action": "upload",
            "artifact_id": action.artifact_id,
            "artifact_sha256": digest,
            "size_bytes": len(buffer),
        }
    raise BrowserPolicyError("unsupported browser mutation")


class PlaywrightReadOnlyTransport:
    """Playwright Chromium adapter for governed browser actions."""

    enforces_pinned_destination = True
    disables_automatic_redirects = True
    verifies_tls_server_identity = True

    def __init__(
        self,
        *,
        headless: bool = True,
        allow_mutations: bool = False,
        artifact_loader: ArtifactLoader | None = None,
        evidence_screenshots: bool = False,
    ) -> None:
        self.headless = bool(headless)
        self.allow_mutations = bool(allow_mutations)
        self.artifact_loader = artifact_loader
        self.evidence_screenshots = bool(evidence_screenshots)

    @staticmethod
    def _loader():
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise BrowserAutomationUnavailable("Playwright is not installed") from exc
        return async_playwright

    async def probe(self) -> None:
        async_playwright = self._loader()
        try:
            async with async_playwright() as runtime:
                browser = await runtime.chromium.launch(headless=self.headless)
                await browser.close()
        except Exception as exc:
            raise BrowserAutomationUnavailable("Playwright Chromium is unavailable") from exc

    async def request(self, *, action: BrowserAction, connect_ip: str, host_header: str,
                      tls_server_name: str, timeout_seconds: int) -> Mapping[str, object]:
        if action.kind in MUTATING_ACTIONS and not self.allow_mutations:
            raise BrowserPolicyError("browser mutations require the zWorkforce approval adapter")
        if action.kind not in READ_ONLY_ACTIONS | MUTATING_ACTIONS:
            raise BrowserPolicyError("unsupported browser action")

        parsed = urlsplit(action.url)
        approved_origin = _origin(parsed)
        hostname = approved_origin[1]
        if not hostname or hostname != tls_server_name.lower().rstrip("."):
            raise BrowserPolicyError("approved hostname and TLS server identity do not match")
        default_port = 443 if parsed.scheme == "https" else 80
        authority_host = f"[{hostname}]" if ":" in hostname else hostname
        expected_authority = authority_host if approved_origin[2] == default_port else f"{authority_host}:{approved_origin[2]}"
        if host_header.lower() != expected_authority.lower():
            raise BrowserPolicyError("browser Host authority does not match the approved origin")

        async_playwright = self._loader()
        timeout_ms = max(1, int(timeout_seconds)) * 1000
        resolver = f"MAP {tls_server_name} {connect_ip}"
        blocked_navigation_url = ""
        try:
            async with async_playwright() as runtime:
                browser = await runtime.chromium.launch(headless=self.headless, args=[f"--host-resolver-rules={resolver}"])
                try:
                    browser_version = str(await browser.version())[:128]
                    context = await browser.new_context(ignore_https_errors=False)
                    page = await context.new_page()
                    initial_navigation_complete = False

                    async def guard(route, request):
                        nonlocal initial_navigation_complete, blocked_navigation_url
                        if request.is_navigation_request():
                            if not initial_navigation_complete and request.url == action.url:
                                await route.continue_(); return
                            blocked_navigation_url = request.url
                            await route.abort(); return
                        target = urlsplit(request.url)
                        try:
                            target_origin = _origin(target)
                        except BrowserPolicyError:
                            await route.abort(); return
                        if target_origin != approved_origin:
                            await route.abort(); return
                        await route.continue_()

                    await context.route("**/*", guard)
                    try:
                        response = await page.goto(action.url, wait_until="domcontentloaded", timeout=timeout_ms)
                    except Exception:
                        if blocked_navigation_url:
                            return {"redirect_url": blocked_navigation_url}
                        raise
                    initial_navigation_complete = True
                    if blocked_navigation_url:
                        return {"redirect_url": blocked_navigation_url}
                    if page.url != action.url:
                        return {"redirect_url": page.url}
                    if action.kind == "navigate":
                        return {"ok": True, "status": response.status if response else 0, "title": (await page.title())[:500], "browser_version": browser_version}
                    if action.kind == "screenshot":
                        screenshot = await page.screenshot(type="png", full_page=True, timeout=timeout_ms)
                        return {**_encode_screenshot(screenshot), "title": (await page.title())[:500], "browser_version": browser_version}
                    if action.kind in MUTATING_ACTIONS:
                        before_screenshot = None
                        if self.evidence_screenshots:
                            try:
                                before_screenshot = _encode_screenshot(
                                    await page.screenshot(type="png", full_page=True, timeout=timeout_ms)
                                )
                            except Exception:
                                before_screenshot = None
                        try:
                            result = dict(await _execute_approved_mutation(page, action, timeout_ms, self.artifact_loader))
                        except Exception:
                            if blocked_navigation_url:
                                return {"redirect_url": blocked_navigation_url, "mutation_redirect_blocked": True}
                            raise
                        if blocked_navigation_url:
                            return {"redirect_url": blocked_navigation_url, "mutation_redirect_blocked": True}
                        result["title"] = (await page.title())[:500]
                        result["navigation_blocked_until_revalidated"] = True
                        result["browser_version"] = browser_version
                        if self.evidence_screenshots:
                            evidence = {"browser_version": browser_version}
                            if before_screenshot is not None:
                                evidence["before"] = before_screenshot
                            try:
                                evidence["after"] = _encode_screenshot(
                                    await page.screenshot(type="png", full_page=True, timeout=timeout_ms)
                                )
                            except Exception:
                                pass
                            result["evidence_screenshots"] = evidence
                        return result
                    selector = action.selector or "body"
                    text = await page.locator(selector).first.inner_text(timeout=timeout_ms)
                    return {"ok": True, "title": (await page.title())[:500], "text": text[:20000], "truncated": len(text) > 20000, "browser_version": browser_version}
                finally:
                    await browser.close()
        except (BrowserPolicyError, BrowserAutomationUnavailable):
            raise
        except Exception as exc:
            raise BrowserAutomationUnavailable("Playwright browser action failed") from exc
