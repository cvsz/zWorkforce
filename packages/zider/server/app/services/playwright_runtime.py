from __future__ import annotations

from typing import Mapping
from urllib.parse import urlsplit

from .agent_runner import BrowserAction, BrowserAutomationUnavailable, BrowserPolicyError, READ_ONLY_ACTIONS


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


class PlaywrightReadOnlyTransport:
    """Playwright Chromium adapter for governed read-only browser actions."""

    enforces_pinned_destination = True
    disables_automatic_redirects = True
    verifies_tls_server_identity = True

    def __init__(self, *, headless: bool = True) -> None:
        self.headless = bool(headless)

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

    async def request(
        self,
        *,
        action: BrowserAction,
        connect_ip: str,
        host_header: str,
        tls_server_name: str,
        timeout_seconds: int,
    ) -> Mapping[str, object]:
        if action.kind not in READ_ONLY_ACTIONS:
            raise BrowserPolicyError("browser mutations require the zWorkforce approval adapter")
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
        try:
            async with async_playwright() as runtime:
                browser = await runtime.chromium.launch(
                    headless=self.headless,
                    args=[f"--host-resolver-rules={resolver}"],
                )
                try:
                    context = await browser.new_context(ignore_https_errors=False)
                    page = await context.new_page()

                    async def guard(route, request):
                        target = urlsplit(request.url)
                        try:
                            target_origin = _origin(target)
                        except BrowserPolicyError:
                            await route.abort()
                            return
                        if target_origin != approved_origin:
                            await route.abort()
                            return
                        if request.is_navigation_request() and request.url != action.url:
                            await route.abort()
                            return
                        await route.continue_()

                    await context.route("**/*", guard)
                    response = await page.goto(action.url, wait_until="domcontentloaded", timeout=timeout_ms)
                    if page.url != action.url:
                        return {"redirect_url": page.url}
                    if action.kind == "navigate":
                        return {"ok": True, "status": response.status if response else 0, "title": (await page.title())[:500]}
                    selector = action.selector or "body"
                    text = await page.locator(selector).first.inner_text(timeout=timeout_ms)
                    return {"ok": True, "title": (await page.title())[:500], "text": text[:20000], "truncated": len(text) > 20000}
                finally:
                    await browser.close()
        except (BrowserPolicyError, BrowserAutomationUnavailable):
            raise
        except Exception as exc:
            raise BrowserAutomationUnavailable("Playwright read-only browser action failed") from exc
