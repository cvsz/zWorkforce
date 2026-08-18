from __future__ import annotations

import re
import urllib.parse

from .workspace_grant_api import WorkspaceGrantApp

_EFFECTS_PATH = "/api/v1/browser-effects"
_EFFECT_PATH = re.compile(r"/api/v1/browser-effects/([0-9A-Fa-f-]{36})")
_EFFECT_ACTION = re.compile(r"/api/v1/browser-effects/([0-9A-Fa-f-]{36})/(claim|finish|reconcile)")


class BrowserEffectApp(WorkspaceGrantApp):
    """Compose tenant-scoped browser side-effect lifecycle endpoints into API serve mode."""

    def handler(self):
        app = self
        ParentHandler = super().handler()

        class Handler(ParentHandler):
            def _get_api(self, path: str):
                match = _EFFECT_PATH.fullmatch(path)
                if not match:
                    return super()._get_api(path)
                ctx, response = self._principal("viewer", "workforce:read")
                if response:
                    return response
                _, tenant_id = ctx
                effect = app.db.get_browser_effect(tenant_id, match.group(1))
                if not effect:
                    return self._error(404, "browser_effect_not_found", "browser effect not found")
                return self._json(200, effect)

            def do_POST(self):
                path = urllib.parse.urlsplit(self.path).path
                action = _EFFECT_ACTION.fullmatch(path)
                if path != _EFFECTS_PATH and not action:
                    return super().do_POST()
                self._prepare()
                try:
                    ctx, response = self._principal("operator", "task:write")
                    if response:
                        return response
                    principal, tenant_id = ctx
                    body = self._body()
                    if not isinstance(body, dict):
                        raise ValueError("browser effect request must be a JSON object")

                    if path == _EFFECTS_PATH:
                        effect = app.db.begin_browser_effect(
                            tenant_id,
                            idempotency_key=str(body.get("idempotency_key") or ""),
                            action_sha256=str(body.get("action_sha256") or ""),
                            approval_task_id=str(body.get("approval_task_id") or ""),
                        )
                        app.db.audit(
                            tenant_id,
                            principal.name,
                            "browser.effect.begin",
                            "browser_effect",
                            effect["id"],
                            {
                                "status": effect["status"],
                                "approval_task_id": effect["approval_task_id"],
                                "action_sha256": effect["action_sha256"],
                            },
                        )
                        return self._json(201 if effect["status"] == "not_started" else 200, effect)

                    effect_id, operation = action.group(1), action.group(2)
                    existing = app.db.get_browser_effect(tenant_id, effect_id)
                    if not existing:
                        return self._error(404, "browser_effect_not_found", "browser effect not found")

                    if operation == "claim":
                        effect, claimed = app.db.claim_browser_effect(tenant_id, effect_id)
                        app.db.audit(
                            tenant_id,
                            principal.name,
                            "browser.effect.claim",
                            "browser_effect",
                            effect_id,
                            {"status": effect["status"], "claimed": claimed},
                        )
                        return self._json(200, {"effect": effect, "claimed": claimed})

                    if operation == "finish":
                        effect = app.db.finish_browser_effect(
                            tenant_id,
                            effect_id,
                            status=str(body.get("status") or ""),
                            result_sha256=str(body.get("result_sha256") or ""),
                            error_code=str(body.get("error_code") or ""),
                        )
                        app.db.audit(
                            tenant_id,
                            principal.name,
                            "browser.effect.finish",
                            "browser_effect",
                            effect_id,
                            {"status": effect["status"], "result_sha256": effect["result_sha256"]},
                        )
                        return self._json(200, effect)

                    effect = app.db.reconcile_browser_effect(
                        tenant_id,
                        effect_id,
                        status=str(body.get("status") or ""),
                        result_sha256=str(body.get("result_sha256") or ""),
                        error_code=str(body.get("error_code") or ""),
                    )
                    app.db.audit(
                        tenant_id,
                        principal.name,
                        "browser.effect.reconcile",
                        "browser_effect",
                        effect_id,
                        {"status": effect["status"], "result_sha256": effect["result_sha256"]},
                    )
                    return self._json(200, effect)
                except (ValueError, TypeError) as exc:
                    return self._error(400, "invalid_browser_effect", str(exc))
                except Exception as exc:
                    return self._error(500, "internal_error", "internal server error", str(exc))

        return Handler
