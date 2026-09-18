#!/usr/bin/env python3
"""AT-4: Streamlit UI 스크린샷 (질문 1~3, NAE Bridge 인용 카드)"""
import asyncio, os
from playwright.async_api import async_playwright

QUESTIONS = [
    "오직 믿음으로 구원받는다는 것은 무엇을 뜻하는가?",
    "회개와 믿음의 관계를 설명해 달라.",
    "그리스도의 속죄가 모든 사람을 위한 것인가, 선택된 자만을 위한 것인가?",
]

OUTPUT_DIR = "/tmp/at4"
os.makedirs(OUTPUT_DIR, exist_ok=True)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})

        # Streamlit UI 열기
        url = "http://localhost:8501"
        print(f"Opening {url}...")
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(8)  # UI 렌더링 대기

        # Onboarding 완료: "연구 시작하기" 클릭
        start_btn = await page.query_selector('button:has-text("연구 시작하기")')
        if start_btn and await start_btn.is_visible():
            print("Clicking '연구 시작하기' (onboarding)...")
            await start_btn.click()
            await asyncio.sleep(5)

        # 채팅 페이지로 이동: 사이드바 st.radio "AI에게 질문" 옵션 클릭
        # Streamlit st.radio는 <button>이 아닌 <input type="radio"> + <label>로 렌더됨
        print("Clicking 'AI에게 질문' in sidebar radio...")
        chat_radio = await page.query_selector('label:has-text("AI에게 질문")')
        if chat_radio and await chat_radio.is_visible():
            await chat_radio.click()
            await asyncio.sleep(4)
        else:
            print("  WARNING: Could not find 'AI에게 질문' radio label")

        # 네비게이션이 실제로 "AI에게 질문"(채팅) 페이지로 이동했는지 확인
        await asyncio.sleep(2)  # Streamlit rerender 대기
        heading = await page.query_selector('h1, h2')
        if heading and await heading.is_visible():
            heading_text = (await heading.inner_text()).strip()[:80]
            print(f"  Heading text: '{heading_text}'")
            assert "질문하기" in heading_text or "AI" in heading_text, \
                f"Expected chat page but got: '{heading_text}'"
            print("  OK: Confirmed on 'AI에게 질문' (chat) page")
        else:
            # h1/h2가 없으면 다른 요소로 확인 — chat input이 있으면 채팅 페이지
            chat_input = await page.query_selector('[data-testid="stChatInput"]')
            if chat_input and await chat_input.is_visible():
                print("  OK: Confirmed on 'AI에게 질문' page (chat input found)")
            else:
                print("  FAIL: Could not confirm navigation to chat page")
                await page.screenshot(path=os.path.join(OUTPUT_DIR, "DEBUG_not_chat.png"))
                print("  DEBUG screenshot saved: DEBUG_not_chat.png")

        # NAE Bridge 섹션의 검색어 입력 필드 찾기
        print("\nLooking for NAE Bridge search input...")

        for q_idx, question in enumerate(QUESTIONS, 1):
            print(f"\n=== Q{q_idx}: {question} ===")

            # NAE Bridge heading으로 섹션 확인
            nae_heading = await page.query_selector('h3:has-text("내서재 공개 자료")')
            if not nae_heading:
                print("  ERROR: NAE Bridge heading not found!")
                screenshot_path = os.path.join(OUTPUT_DIR, f"AT4_q{q_idx}.png")
                await page.screenshot(path=screenshot_path, full_page=False)
                continue

            # Streamlit st.text_input의 input은 [data-testid="stTextInput"] 내 input
            nae_input = await page.query_selector('[data-testid="stTextInput"] input')

            if not nae_input:
                print("  ERROR: NAE Bridge input field not found!")
                screenshot_path = os.path.join(OUTPUT_DIR, f"AT4_q{q_idx}.png")
                await page.screenshot(path=screenshot_path, full_page=False)
                continue

            # 입력 필드에 질문 입력
            await nae_input.click()
            await nae_input.fill(question)
            await asyncio.sleep(1)

            print(f"  Input filled: {question[:50]}...")

            # NAE Bridge는 '검색' 버튼을 클릭해야 검색이 실행됨 (Enter 키 아님!)
            search_btn = await page.query_selector('[data-testid="stButton"]')
            if not search_btn:
                search_btn = await page.query_selector('button:has-text("검색")')

            if search_btn and await search_btn.is_visible():
                print("  Clicking '검색' button...")
                await search_btn.click()
                print("  Search triggered via button click")
            else:
                print("  WARNING: '검색' button not found — cannot trigger search")

            # 응답 대기 (NAE Bridge 검색 결과 렌더링)
            await asyncio.sleep(8)

            # 스크린샷 저장 (전체 페이지)
            screenshot_path = os.path.join(OUTPUT_DIR, f"AT4_q{q_idx}.png")
            await page.screenshot(path=screenshot_path, full_page=True)
            file_size = os.path.getsize(screenshot_path)
            print(f"  Screenshot saved: {screenshot_path} ({file_size} bytes)")

            # 인용 카드 확인 (육안 확인용 정보)
            cards = await page.query_selector_all('[class*="stContainer"], [data-testid="stContainer"]')
            print(f"  Container elements: {len(cards)}")

            captions = await page.query_selector_all('[class*="stCaption"], [data-testid="stCaption"]')
            for cap in captions[:5]:
                text = await cap.inner_text() if await cap.is_visible() else ""
                if len(text) > 10:
                    print(f"  Caption: {text[:80]}...")

            bolds = await page.query_selector_all('strong')
            for b in bolds[:3]:
                text = await b.inner_text() if await b.is_visible() else ""
                if len(text) > 2:
                    print(f"  Bold: {text[:80]}...")

        await browser.close()
        print("\n=== AT-4 스크린샷 완료 ===")


asyncio.run(main())
