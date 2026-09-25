"""Black-box Playwright runner for PEB v0.1."""
from __future__ import annotations
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from playwright.async_api import Browser, Page, async_playwright

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class SessionRecorder:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(
                {"timestamp": utc_now(), **event}, ensure_ascii=False
            ) + "\n")

def action_signature(action: dict[str, Any]) -> tuple[str, str]:
    """Identity of an action for repeat detection: action kind + visible target."""
    target = (action.get("target") or action.get("text") or "").strip()
    return (action.get("action", ""), target)

def resolve_step_action(
    planner: Any,
    scenario: dict[str, Any],
    observation: str,
    history: list[dict[str, Any]],
    last_signature: tuple[str, str] | None,
) -> tuple[dict[str, Any], bool, bool]:
    """Ask the planner for the next action.

    If the planner repeats the exact action+target it already executed, it
    gets one more chance — with the repeat flagged via `blocked_action` — to
    pick a different visible control instead of looping or finishing early.
    Returns (action, should_execute, was_blocked).
    """
    action = planner.next_action(scenario, observation, history)
    signature = action_signature(action)
    if action["action"] == "finish" or signature != last_signature:
        return action, True, False

    retry_action = planner.next_action(
        scenario, observation, history, blocked_action=action
    )
    retry_signature = action_signature(retry_action)
    if retry_action["action"] == "finish" or retry_signature != last_signature:
        return retry_action, True, True

    return retry_action, False, True
def check_success_criteria(scenario: dict[str, Any], observation: str) -> bool:
    """Check if scenario's success_criteria are met. Returns True if all conditions satisfied."""
    criteria = scenario.get("success_criteria")
    if not criteria or criteria.get("type") != "observation_contains":
        return False
    
    conditions = criteria.get("conditions", [])
    for cond in conditions:
        field = cond.get("field", "")
        contains = cond.get("contains", "")
        if field == "body_text" and contains not in observation:
            return False
    return True



class BrowserDriver:
    def __init__(self, base_url: str, recorder: SessionRecorder,
                 headless: bool = True) -> None:
        self.base_url = base_url
        self.recorder = recorder
        self.headless = headless
        self._pw = None
        self.browser: Browser | None = None
        self.page: Page | None = None

    async def start(self) -> None:
        self._pw = await async_playwright().start()
        self.browser = await self._pw.chromium.launch(headless=self.headless)
        context = await self.browser.new_context(
            viewport={"width": 1440, "height": 1000}
        )
        self.page = await context.new_page()
        await self.page.goto(self.base_url, wait_until="domcontentloaded")
        await self.page.wait_for_timeout(1500)
        self.recorder.record({"event": "page_opened", "url": self.page.url})

    async def close(self) -> None:
        if self.browser:
            await self.browser.close()
        if self._pw:
            await self._pw.stop()

    async def observe(self) -> str:
        assert self.page is not None
        text = await self.page.locator("body").inner_text()
        return re.sub(r"\n{3,}", "\n\n", text).strip()

    async def act(self, action: dict[str, Any]) -> None:
        assert self.page is not None
        kind = action["action"]

        if kind == "ask":
            text = action.get("text", "")
            
            # Chat page textarea (primary) — placeholder="질문을 입력하세요..."
            field = self.page.get_by_placeholder("질문을 입력하세요...")
            if await field.count() > 0:
                try:
                    await field.fill(text)
                    send_btn = self.page.get_by_role("button", name="Send message")
                    try:
                        await send_btn.click()
                    except Exception:
                        pass  # button may be disabled during processing
                except Exception:
                    pass  # fill failed, continue to fallback
            else:
                # Fallback: Dashboard search input — placeholder="문서, 저자, 주제 또는 성경 구절 검색..."
                field = self.page.get_by_placeholder(
                    "문서, 저자, 주제 또는 성경 구절 검색..."
                )
                if await field.count() > 0:
                    try:
                        await field.fill(text)
                        await self.page.get_by_role(
                            "button", name="질문하기"
                        ).click()
                    except Exception:
                        pass  # fill failed, continue gracefully

        elif kind == "click":
            target = action.get("target") or action.get("text")
            await self.page.get_by_text(target, exact=False).first.click()

        elif kind == "finish":
            return

        await self.page.wait_for_timeout(1200)
        self.recorder.record({
            "event": "action",
            "action": action,
            "url": self.page.url,
        })

async def run_browser(scenario: dict[str, Any], planner: Any,
                      base_url: str, recorder: SessionRecorder,
                      headless: bool) -> dict[str, Any]:
    driver = BrowserDriver(base_url, recorder, headless=headless)
    history: list[dict[str, Any]] = []
    last_signature: tuple[str, str] | None = None
    try:
        await driver.start()
        max_steps = int(scenario["limits"]["max_steps"])
        for step in range(1, max_steps + 1):
            observation = await driver.observe()
            recorder.record({
                "event": "observation",
                "step": step,
                "text": observation,
            })
            
            # Check success criteria before planning next action
            if check_success_criteria(scenario, observation):
                recorder.record({
                    "event": "success_criteria_met",
                    "step": step,
                    "observation_preview": observation[:500],
                })
                return {"status": "COMPLETED", "steps": step, "reason": "success_criteria_met"}
            
            action, should_execute, was_blocked = resolve_step_action(
                planner, scenario, observation, history, last_signature,
            )
            if was_blocked:
                recorder.record({
                    "event": "repeated_action_blocked",
                    "step": step,
                    "action": action,
                    "executed": should_execute,
                })
            recorder.record({
                "event": "planner_action",
                "step": step,
                "action": action,
            })
            history.append({
                "step": step,
                "action": action,
                "observation": observation[-4000:],
                "blocked": was_blocked,
            })
            if not should_execute:
                continue
            if action["action"] == "finish":
                return {"status": "COMPLETED", "steps": step}
            await driver.act(action)
            last_signature = action_signature(action)
        return {"status": "STEP_LIMIT_REACHED", "steps": max_steps}
    finally:
        await driver.close()
