"""Minimal local Ollama planner for PEB."""
from __future__ import annotations
import json
import urllib.error
import urllib.request
from typing import Any

SYSTEM_PROMPT = """You are PEB, a simulated pastor using a theological research application.

You are NOT a developer and NOT a test judge.
You do not know the application's internal architecture.
You do not inspect databases, source code, configuration, embeddings, or APIs.
You only act as a normal end user through the visible browser UI.

Decide the next natural pastor action for the current research goal.

Return JSON only:
{
  "action": "ask|click|finish",
  "text": "text to type, if applicable",
  "target": "visible target text, if applicable",
  "reason": "brief user-intent reason"
}

Rules:
- Prefer natural user behavior over exhaustive testing.
- Ask a follow-up when evidence needs verification.
- Never claim a source was found unless the visible UI shows it.
- Do not decide PASS or FAIL.
- Finish only when the scenario goal is reasonably satisfied.
"""

class OllamaPlanner:
    def __init__(self, model: str, base_url: str = "http://127.0.0.1:11434") -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")

    def next_action(self, scenario: dict[str, Any], observation: str,
                    history: list[dict[str, Any]]) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps({
                    "goal": scenario["goal"],
                    "workflow": scenario["workflow"],
                    "limits": scenario["limits"],
                    "visible_observation": observation[:12000],
                    "interaction_history": history[-8:],
                }, ensure_ascii=False)},
            ],
        }
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Ollama is unavailable at {self.base_url}: {exc}"
            ) from exc

        content = data.get("message", {}).get("content", "")
        try:
            action = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Ollama returned non-JSON planner output: {content!r}"
            ) from exc
        self._validate_action(action)
        return action

    @staticmethod
    def _validate_action(action: dict[str, Any]) -> None:
        if action.get("action") not in {"ask", "click", "finish"}:
            raise ValueError(f"Unsupported PEB action: {action!r}")
        if action["action"] in {"ask", "click"} and not (
            action.get("text") or action.get("target")
        ):
            raise ValueError(f"PEB action has no user-visible payload: {action!r}")
