import asyncio
import os
import random
from playwright.async_api import async_playwright
import re
from datetime import datetime
import json
from html import unescape

def clean_name(name: str) -> str:
    if not name:
        return "unknown"
    name = re.sub(r'[\\/:*?"<>|]', '-', name)
    name = name.replace('/', '-').replace('\\', '-')
    return name.strip()

def clean_html(html_text: str) -> str:
    if not html_text:
        return ""
    text = re.sub(r'<br\s*/?>', '\n', html_text)
    text = re.sub(r'</?p[^>]*>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = unescape(text)
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

LIMIT_SUBCATEGORIES = None
LIMIT_CATEGORY_ITEMS = None
LIMIT_PRODUCTS = 2500
SAVE_TXT = True
SAVE_JSONL = True

BASE_URL = "https://eshop.eca.ir"
OUTPUT_DIR = "eca_products"
JSONL_FILENAME = "products_dataset.jsonl"
MIN_DELAY = 2
MAX_DELAY = 4
TIMEOUT = 120000

product_counter = 0
start_time = None
log_file = None
jsonl_file = None

async def human_wait():
    await asyncio.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

def log_message(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {msg}"
    print(log_line)
    if log_file:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")

async def safe_click(page, selector):
    try:
        await page.wait_for_selector(selector, timeout=8000)
        await page.click(selector)
        await human_wait()
        return True
    except:
        log_message(f"❌ خطا در کلیک: {selector}")
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
        log_message("⛔ به محدودیت تست رسیدیم — توقف اسکرپ محصول.")
        return False

    try:
        # await page.goto(product_url, wait_until="networkidle", timeout=TIMEOUT)
        await page.goto(product_url, wait_until="domcontentloaded", timeout=TIMEOUT)


        title = await get_text(page, "#mainProduct h1")
        
        price = None
        try:
            price_elem = await page.query_selector("span.current-price.fa-number-conv")
            if price_elem:
                price = await price_elem.inner_text()
        except:
            pass
        
        short_desc = None
        try:
            short_desc_elem = await page.query_selector("div.product-description-short.typo")
            if short_desc_elem:
                short_desc = await short_desc_elem.inner_text()
        except:
            pass
        
        desc_html = None
        desc_clean = None
        try:
            desc_elem = await page.query_selector("div.product-description.typo")
            if desc_elem:
                desc_html = await desc_elem.inner_html()
                desc_clean = clean_html(desc_html)
        except:
            pass
        
        specs = {}
        specs_text = ""
        try:
            spec_names = await page.query_selector_all("section.product-features dl.data-sheet dt.name")
            spec_values = await page.query_selector_all("section.product-features dl.data-sheet dd.value")
            
            if spec_names and spec_values and len(spec_names) == len(spec_values):
                for i in range(len(spec_names)):
                    name = await spec_names[i].inner_text()
                    value = await spec_values[i].inner_text()
                    specs[name] = value
                    specs_text += f"{name}: {value}\n"
        except:
            pass

        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        if SAVE_TXT:
            folder = os.path.join(
                script_dir,
                OUTPUT_DIR, 
                clean_name(category_name),
                clean_name(subcategory_name)
            )
            os.makedirs(folder, exist_ok=True)
            filename = clean_name(title[:50]) + ".txt"
            filepath = os.path.join(folder, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"URL: {product_url}\n")
                f.write(f"{'='*80}\n\n")
                f.write(f"عنوان:\n{title}\n\n")
                if price:
                    f.write(f"قیمت:\n{price}\n\n")
                if short_desc:
                    f.write(f"توضیحات کوتاه:\n{short_desc}\n\n")
                if specs_text:
                    f.write(f"مشخصات فنی:\n{specs_text}\n")
                if desc_clean:
                    f.write(f"توضیحات کامل:\n{desc_clean}\n\n")
        
        if SAVE_JSONL:
            combined_text = f"عنوان: {title or ''}"
            if short_desc:
                combined_text += f". توضیحات کوتاه: {short_desc}"
            if specs:
                specs_str = ", ".join([f"{k}: {v}" for k, v in specs.items()])
                combined_text += f". مشخصات: {specs_str}"
            if desc_clean:
                combined_text += f". توضیحات: {desc_clean[:500]}"
            
            product_data = {
                "id": f"prod_{product_counter:04d}",
                "url": product_url,
                "title": title,
                "price": price,
                "short_desc": short_desc,
                "specs": specs,
                "description": desc_clean,
                "category": category_name,
                "subcategory": subcategory_name,
                "combined_text": combined_text
            }
            
            with open(jsonl_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(product_data, ensure_ascii=False) + "\n")

        product_counter += 1
        log_message(f"✅ محصول ذخیره شد [{product_counter}/{LIMIT_PRODUCTS}]: {title}")

        return True

    except Exception as e:
        log_message(f"❌ خطا در اسکرپ محصول {product_url}: {e}")
        return False

async def scrape():
    global start_time, log_file, jsonl_file
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    full_output_dir = os.path.join(script_dir, OUTPUT_DIR)
    os.makedirs(full_output_dir, exist_ok=True)
    
    log_filename = f"scrape_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    log_file = os.path.join(full_output_dir, log_filename)
    
    if SAVE_JSONL:
        jsonl_file = os.path.join(script_dir, JSONL_FILENAME)
        if os.path.exists(jsonl_file):
            os.remove(jsonl_file)
    
    start_time = datetime.now()
    log_message("=" * 60)
    log_message("🚀 شروع اسکرپ")
    log_message(f"⚙️ تنظیمات: SUBCATEGORIES={LIMIT_SUBCATEGORIES}, ITEMS={LIMIT_CATEGORY_ITEMS}, PRODUCTS={LIMIT_PRODUCTS}")
    log_message(f"💾 ذخیره TXT: {SAVE_TXT}, ذخیره JSONL: {SAVE_JSONL}")
    log_message("=" * 60)
    
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        page.set_default_timeout(TIMEOUT)
        
        try:
            # await page.goto(BASE_URL, wait_until="networkidle", timeout=TIMEOUT)
            await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=TIMEOUT)

        except Exception as e:
            log_message(f"❌ خطا در باز کردن صفحه اصلی: {e}")
            log_message("⚠️ در حال تلاش مجدد با domcontentloaded...")
            await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=TIMEOUT)

        await safe_click(page, "#header-main-menu > div > div > div.left-nav-trigger > div > div")

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

        log_message(f"🔵 تعداد زیر دسته‌ها پیدا شده: {len(sub_links_data)}")

        if LIMIT_SUBCATEGORIES:
            sub_links_data = sub_links_data[:LIMIT_SUBCATEGORIES]
            log_message(f"🔵 محدود شده به: {len(sub_links_data)} زیر دسته")

        for sub_index, (sub_name, sub_url) in enumerate(sub_links_data, 1):

            global product_counter
            if LIMIT_PRODUCTS and product_counter >= LIMIT_PRODUCTS:
                log_message("⛔ پایان — محدودیت تست رسید.")
                break   
            def absolute(url: str) -> str:
                if not url:
                    return ""
                if url.startswith("http"):
                    return url
                return "https://eshop.eca.ir" + url

            full_sub_url = absolute(sub_url)

            log_message(f"\n📂 [{sub_index}/{len(sub_links_data)}] زیر‌دسته: {sub_name}")
            # await page.goto(full_sub_url, wait_until="networkidle")
            await page.goto(full_sub_url, wait_until="domcontentloaded", timeout=TIMEOUT)

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

            log_message(f"   📊 تعداد زیر زیر دسته‌ها: {len(sub_subcats)}")

            for sc_index, (sc_name, sc_url) in enumerate(sub_subcats, 1):

                if LIMIT_PRODUCTS and product_counter >= LIMIT_PRODUCTS:
                    break

                full_page_url = absolute(sc_url)

                log_message(f"   🔸 [{sc_index}/{len(sub_subcats)}] زیر زیر دسته: {sc_name}")
                # await page.goto(full_page_url, wait_until="networkidle")
                await page.goto(full_page_url, wait_until="domcontentloaded", timeout=TIMEOUT)

                await human_wait()

                products = await page.query_selector_all(
                    "#js-product-list article a"
                )

                product_urls = []
                for p in products:
                    href = await p.get_attribute("href")
                    if href:
                        product_urls.append(absolute(href))


                log_message(f"      🟡 تعداد محصولات پیدا شده: {len(product_urls)}")

                if LIMIT_CATEGORY_ITEMS:
                    # product_urls = product_urls[:LIMIT_CATEGORY_ITEMS]
                    log_message(f"      🟡 محدود شده به: {len(product_urls)} محصول")

                for url in product_urls:
                    if LIMIT_PRODUCTS and product_counter >= LIMIT_PRODUCTS:
                        break

                    product_page = await browser.new_page()
                    await scrape_product(product_page, url, sub_name, sc_name)
                    await product_page.close()

                    await human_wait()

        await browser.close()
        
        end_time = datetime.now()
        duration = end_time - start_time
        log_message("\n" + "=" * 60)
        log_message("🎉 اسکرپ به پایان رسید")
        log_message(f"📊 تعداد کل محصولات ذخیره شده: {product_counter}")
        log_message(f"⏱️ مدت زمان: {duration}")
        if SAVE_TXT:
            log_message(f"📁 محل ذخیره TXT: {os.path.abspath(full_output_dir)}")
        if SAVE_JSONL:
            log_message(f"📄 فایل JSONL: {os.path.abspath(jsonl_file)}")
        log_message(f"📋 فایل لاگ: {log_filename}")
        log_message("=" * 60)


if __name__ == "__main__":
    asyncio.run(scrape())






