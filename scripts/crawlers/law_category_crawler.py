"""
scripts/crawlers/law_category_crawler.py
law.go.kr 법령분류별 전체 목록 크롤링

실행:
    python scripts/crawlers/law_category_crawler.py
"""

import re
import json
import asyncio
from playwright.async_api import async_playwright

SEARCH_URL = "https://law.go.kr/lsSc.do?menuId=1&subMenuId=15&tabMenuId=81&query="

# 수집할 법령분류 코드 (콤보박스 value값)
LAW_CLASS_CODES = {
    "08": "민사법",
    "09": "형사법",
    "07": "법무",
    "34": "주택·건축·도로",
    "33": "국토개발·도시",
    "35": "수자원·토지·건설업",
}

# 현재 수집할 분류
ACTIVE_CLASSES = ["08"]


async def fetch_law_list(browser, page, class_code: str, class_name: str) -> list[dict]:
    print(f"\n[{class_name}({class_code})] 목록 수집 중...")

    # 1. 페이지 접속
    await page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(2000)

    # 2. POST로 전체 목록 가져오기
    response = await page.evaluate("""
        async (classCode) => {
            const params = new URLSearchParams();
            params.append('q', '*');
            params.append('outmax', '9999');
            params.append('p18', '0');
            params.append('p19', '1,3');
            params.append('pg', '1');
            params.append('fsort', '10,41,21,31');
            params.append('lsType', 'null');
            params.append('section', 'lawNm');
            params.append('lsiSeq', '0');
            params.append('p9', '2,4');
            params.append('p10', classCode);
            params.append('psort', '50');

            const res = await fetch('/lsScListR.do?menuId=1&subMenuId=15&tabMenuId=81', {
                method: 'POST',
                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                body: params.toString()
            });
            return await res.text();
        }
    """, class_code)

    print(f"  응답 길이: {len(response)}")

    # 디버깅용 저장
    with open("scripts/crawlers/debug_response.html", "w", encoding="utf-8") as f:
        f.write(response)

    # 3. 응답 HTML 파싱
    temp_page = await browser.new_page()
    await temp_page.set_content(response)
    await temp_page.wait_for_timeout(500)

    laws = []
    items = await temp_page.query_selector_all("li[id^='liBgcolor']")
    print(f"  li 항목 수: {len(items)}")

    for item in items:
        try:
            link = await item.query_selector("a[onclick*='lsViewWideAll']")
            if not link:
                continue

            # 법령명
            span = await link.query_selector("span.tx")
            if not span:
                continue
            법령명 = (await span.inner_text()).strip()
            # 앞 번호 제거 ("195.  주택임대차보호법" → "주택임대차보호법")
            if "." in 법령명:
                법령명 = 법령명.split(".", 1)[1].strip()

            # onclick에서 MST, 시행일자 추출
            onclick = await link.get_attribute("onclick") or ""
            match = re.search(r"lsViewWideAll\('(\d+)','(\d+)'", onclick)
            if not match:
                continue
            mst      = match.group(1)
            시행일자 = match.group(2)

            # 법령종류 (tx2에서 추출)
            span2    = await link.query_selector("span.tx2")
            tx2      = (await span2.inner_text()).strip() if span2 else ""
            법령구분 = ""
            if "법률" in tx2:
                법령구분 = "법률"
            elif "대통령령" in tx2:
                법령구분 = "대통령령"
            elif "대법원규칙" in tx2:
                법령구분 = "대법원규칙"
            elif "부령" in tx2 or "령" in tx2:
                법령구분 = "부령"

            laws.append({
                "법령명":       법령명,
                "MST":          mst,
                "시행일자":     시행일자,
                "법령구분명":   법령구분,
                "법령분류코드": class_code,
                "법령분류명":   class_name,
            })
        except Exception:
            continue

    await temp_page.close()
    print(f"  파싱된 법령 수: {len(laws)}")
    return laws


async def main():
    print("=" * 60)
    print("law.go.kr 법령분류별 목록 크롤링")
    print("=" * 60)

    all_laws = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page    = await browser.new_page()

        for code, name in LAW_CLASS_CODES.items():
            if ACTIVE_CLASSES and code not in ACTIVE_CLASSES:
                continue
            laws = await fetch_law_list(browser, page, code, name)
            all_laws[name] = laws

        await browser.close()

    output_path = "scripts/crawlers/law_category_list.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_laws, f, ensure_ascii=False, indent=2)

    print(f"\n결과 저장: {output_path}")
    for name, laws in all_laws.items():
        print(f"  {name}: {len(laws)}개")


if __name__ == "__main__":
    asyncio.run(main())