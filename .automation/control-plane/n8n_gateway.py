"""n8n gateway / control-plane integration.

Handles POST/GET to the existing n8n Phase E State Machine webhook.
Does NOT modify any n8n workflow - only communicates via the existing webhook.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any


WEBHOOK_URL = "http://localhost:5678/webhook/dbma-control-plane-pilot"
REQUEST_TIMEOUT_S = 900


class GatewayError(Exception):
    """Raised when the n8n gateway returns an error."""
    def __init__(self, http_code: int, body: Any, message: str) -> None:
        self.http_code = http_code
        self.body = body
        super().__init__(message)


class N8NGateway:
    """Client for the existing n8n Phase E State Machine webhook."""

    def __init__(self, webhook_url: str | None = None, timeout_s: int = REQUEST_TIMEOUT_S):
        self.webhook_url = webhook_url or WEBHOOK_URL
        self.timeout_s = timeout_s
        self._request_log: list[dict[str, Any]] = []

    def post_task(self, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        """POST a task to the n8n webhook. Returns (http_code, response_body)."""
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.webhook_url, data=data,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        log_entry = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "action": "post_task",
            "task_id": payload.get("task_id", ""),
            "payload_size": len(data),
        }
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                log_entry["http_code"] = resp.status
                log_entry["status"] = "success"
                self._request_log.append(log_entry)
                return (resp.status, body)
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            try:
                body = json.loads(body_text)
            except json.JSONDecodeError:
                body = {"raw": body_text}
            log_entry["http_code"] = exc.code
            log_entry["status"] = "error"
            log_entry["error"] = body_text[:500]
            self._request_log.append(log_entry)
            raise GatewayError(exc.code, body, f"HTTP {exc.code}: {body_text[:200]}") from exc
        except urllib.error.URLError as exc:
            log_entry["status"] = "transport_error"
            log_entry["error"] = str(exc.reason)
            self._request_log.append(log_entry)
            raise GatewayError(0, {}, f"Transport error: {exc.reason}") from exc

    def verify_response(self, response: dict[str, Any], expected_task_id: str) -> tuple[bool, list[str]]:
        """Verify that the n8n response is consistent with the submitted task."""
        errors: list[str] = []
        if "task_id" in response and response["task_id"] != expected_task_id:
            errors.append(f"response task_id mismatch: {response['task_id']} != {expected_task_id}")
        status = response.get("status")
        if status is None:
            errors.append("response missing 'status' field")
        return (len(errors) == 0, errors)

    @property
    def request_log(self) -> list[dict[str, Any]]:
        return list(self._request_log)
