import asyncio
import os
import random
from playwright.async_api import async_playwright
import re

def clean_name(name: str) -> str:
    if not name:
        return "unknown"
    name = re.sub(r'[\\/:*?"<>|]', '-', name)
    name = name.replace('/', '-').replace('\\', '-')
    return name.strip()

LIMIT_SUBCATEGORIES = 2
LIMIT_CATEGORY_ITEMS = 5
LIMIT_PRODUCTS = 80

product_counter = 0  
BASE_URL = "https://eshop.eca.ir"
OUTPUT_DIR = "eca_products"
MIN_DELAY = 2
MAX_DELAY = 4

async def human_wait():
    await asyncio.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

async def safe_click(page, selector):
    try:
        await page.wait_for_selector(selector, timeout=8000)
        await page.click(selector)
        await human_wait()
        return True
    except:
        print(f"❌ خطا در کلیک: {selector}")
        return False

async def get_text(page, selector):
    try:
        await page.wait_for_selector(selector, timeout=6000)
        return await page.locator(selector).inner_text()
    except:
        return None

async def scrape_product(page, product_url, category_name, subcategory_name):
    global product_counter

    if LIMIT_PRODUCTS and product_counter >= LIMIT_PRODUCTS:
        print("⛔ به محدودیت تست رسیدیم — توقف اسکرپ محصول.")
        return False

    try:
        await page.goto(product_url, wait_until="networkidle", timeout=30000)

        title = await get_text(page, "#mainProduct h1")
        price = await get_text(page, "#add-to-cart-or-refresh .product-prices")
        desc  = await get_text(page, "#collapseDescription > div > div")

        folder = os.path.join(
            OUTPUT_DIR, 
            clean_name(category_name),
            clean_name(subcategory_name)
        )

        os.makedirs(folder, exist_ok=True)

        filename = clean_name(title[:50]) + ".txt"

        filepath = os.path.join(folder, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"URL: {product_url}\n")
            f.write(f"عنوان:\n{title}\n\n")
            f.write(f"قیمت:\n{price}\n\n")
            f.write(f"توضیحات:\n{desc}\n")

        product_counter += 1
        print(f"✅ محصول ذخیره شد [{product_counter}]: {title}")

        return True

    except Exception as e:
        print(f"❌ خطا در اسکرپ محصول {product_url}: {e}")
        return False

async def scrape():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(BASE_URL, wait_until="networkidle")

        await safe_click(page, "#header-main-menu .left-nav-trigger")

        await safe_click(page,
            "#index .st-menu .js-sidebar-category-tree > div > ul > li:nth-child(2) > div.js-collapse-trigger"
        )

        sub_links = await page.query_selector_all(
            "#index .js-sub-categories.expanded > ul > li > a"
        )

        sub_links_data = []
        for link in sub_links:
            url = await link.get_attribute("href")
            name = await link.inner_text()
            if url:
                sub_links_data.append((name.strip(), url))

        print(f"🔵 تعداد زیر دسته‌ها: {len(sub_links_data)}")

        if LIMIT_SUBCATEGORIES:
            sub_links_data = sub_links_data[:LIMIT_SUBCATEGORIES]

        for sub_name, sub_url in sub_links_data:

            global product_counter
            if LIMIT_PRODUCTS and product_counter >= LIMIT_PRODUCTS:
                print("⛔ پایان — محدودیت تست رسید.")
                break   
            def absolute(url: str) -> str:
                if not url:
                    return ""
                if url.startswith("http"):
                    return url
                return "https://eshop.eca.ir" + url

            full_sub_url = absolute(sub_url)

            print(f"\n📂 زیر‌دسته: {sub_name}")
            await page.goto(full_sub_url, wait_until="networkidle")
            await human_wait()

            subcats = await page.query_selector_all(
                "#js-product-list-header > aside > div.subcategories-wrapper a"
            )

            sub_subcats = []
            for s in subcats:
                url = await s.get_attribute("href")
                name = await s.inner_text()
                if url:
                    sub_subcats.append((name.strip(), url))

            if not sub_subcats:
                sub_subcats = [(sub_name, sub_url)]

            if LIMIT_CATEGORY_ITEMS:
                sub_subcats = sub_subcats[:LIMIT_CATEGORY_ITEMS]

            for sc_name, sc_url in sub_subcats:

                if LIMIT_PRODUCTS and product_counter >= LIMIT_PRODUCTS:
                    break

                full_page_url = absolute(sc_url)

                print(f"   🔸 زیر زیر دسته: {sc_name}")
                await page.goto(full_page_url, wait_until="networkidle")
                await human_wait()

                products = await page.query_selector_all(
                    "#js-product-list article a"
                )

                product_urls = []
                for p in products:
                    href = await p.get_attribute("href")
                    if href:
                        product_urls.append(absolute(href))


                print(f"      🟡 تعداد محصولات: {len(product_urls)}")

                if LIMIT_CATEGORY_ITEMS:
                    product_urls = product_urls[:LIMIT_CATEGORY_ITEMS]

                for url in product_urls:
                    if LIMIT_PRODUCTS and product_counter >= LIMIT_PRODUCTS:
                        break

                    await scrape_product(page, url, sub_name, sc_name)
                    await human_wait()

        await browser.close()


if __name__ == "__main__":
    asyncio.run(scrape())
