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
            field = self.page.get_by_label("검색어", exact=True)
            await field.fill(text)
            await self.page.get_by_role(
                "button", name=re.compile("검색 실행")
            ).click()

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
            action = planner.next_action(scenario, observation, history)
            recorder.record({
                "event": "planner_action",
                "step": step,
                "action": action,
            })
            history.append({
                "step": step,
                "action": action,
                "observation": observation[-4000:],
            })
            if action["action"] == "finish":
                return {"status": "COMPLETED", "steps": step}
            await driver.act(action)
        return {"status": "STEP_LIMIT_REACHED", "steps": max_steps}
    finally:
        await driver.close()
