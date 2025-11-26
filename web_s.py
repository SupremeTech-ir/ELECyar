import asyncio
import os
import random
from playwright.async_api import async_playwright
from urllib.parse import urljoin, urlparse

# Configuration - متغیرهای قابل تغییر
BASE_URL = "https://eshop.eca.ir"
OUTPUT_DIR = "scraped_data"
MIN_DELAY = 3  # حداقل وقفه بین درخواست‌ها (ثانیه)
MAX_DELAY = 8  # حداکثر وقفه بین درخواست‌ها (ثانیه)
MAX_PAGES = None  # تعداد صفحات مورد نظر (None = همه صفحات)

visited_urls = set()
scraped_count = 0

async def extract_product_info(page, url: str):
    """استخراج اطلاعات محصول از یک صفحه"""
    result = f"URL: {url}\n{'='*80}\n\n"
    
    # 1. عنوان اصلی محصول
    try:
        title_element = await page.query_selector("h1")
        if title_element:
            title = await title_element.inner_text()
            result += f"=== عنوان اصلی ===\n{title.strip()}\n\n"
    except:
        result += "=== عنوان اصلی ===\nیافت نشد\n\n"
    
    # 2. عنوان دوم/زیرعنوان
    try:
        subtitle_element = await page.query_selector("[class*='desc']")
        if subtitle_element:
            subtitle = await subtitle_element.inner_text()
            result += f"=== عنوان دوم ===\n{subtitle.strip()}\n\n"
    except:
        result += "=== عنوان دوم ===\nیافت نشد\n\n"
    
    # 3. توضیحات کامل
    try:
        description_element = await page.query_selector(".product-description")
        if description_element:
            description = await description_element.inner_text()
            result += f"=== توضیحات کامل ===\n{description.strip()}\n\n"
    except:
        result += "=== توضیحات کامل ===\nیافت نشد\n\n"
    
    # 4. قیمت
    try:
        price_element = await page.query_selector("span.current-price.fa-number-conv")
        if price_element:
            price = await price_element.inner_text()
            result += f"=== قیمت ===\n{price.strip()}\n\n"
    except:
        result += "=== قیمت ===\nیافت نشد\n\n"
    
    return result

async def get_all_links(page, base_url: str):
    """استخراج تمام لینک‌های داخلی از صفحه"""
    links = set()
    try:
        all_links = await page.query_selector_all("a[href]")
        for link in all_links:
            href = await link.get_attribute("href")
            if href:
                full_url = urljoin(base_url, href)
                parsed = urlparse(full_url)
                if parsed.netloc == urlparse(base_url).netloc:
                    links.add(full_url)
    except Exception as e:
        print(f"خطا در استخراج لینک‌ها: {e}")
    
    return links

async def scrape_page(page, url: str, output_dir: str):
    """اسکرِیپ یک صفحه و ذخیره اطلاعات"""
    global scraped_count
    
    try:
        print(f"در حال اسکرِیپ: {url}")
        await page.goto(url, wait_until="networkidle", timeout=30000)
        
        # استخراج اطلاعات
        content = await extract_product_info(page, url)
        
        # ذخیره در فایل
        filename = f"page_{scraped_count:04d}.txt"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        scraped_count += 1
        print(f"✓ ذخیره شد: {filename} (تعداد کل: {scraped_count})")
        
        return True
    except Exception as e:
        print(f"✗ خطا در اسکرِیپ {url}: {e}")
        return False

async def scrape_domain(base_url: str, output_dir: str, min_delay: int, max_delay: int, max_pages: int = None):
    """اسکرِیپ کل دامنه با وقفه تصادفی"""
    global visited_urls, scraped_count
    
    # ایجاد پوشه خروجی در کنار فایل کد
    script_dir = os.path.dirname(os.path.abspath(__file__))
    full_output_dir = os.path.join(script_dir, output_dir)
    os.makedirs(full_output_dir, exist_ok=True)
    
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # صف لینک‌ها
        to_visit = {base_url}
        
        while to_visit and (max_pages is None or scraped_count < max_pages):
            # انتخاب لینک بعدی
            current_url = to_visit.pop()
            
            if current_url in visited_urls:
                continue
            
            visited_urls.add(current_url)
            
            # اسکرِیپ صفحه
            success = await scrape_page(page, current_url, full_output_dir)
            
            if success:
                # استخراج لینک‌های جدید
                new_links = await get_all_links(page, base_url)
                to_visit.update(new_links - visited_urls)
                
                # وقفه تصادفی برای شبیه‌سازی رفتار انسانی
                delay = random.uniform(min_delay, max_delay)
                print(f"⏳ وقفه {delay:.2f} ثانیه...\n")
                await asyncio.sleep(delay)
        
        await browser.close()
        
        print(f"\n{'='*80}")
        print(f"اسکرِیپ کامل شد!")
        print(f"تعداد صفحات اسکرِیپ شده: {scraped_count}")
        print(f"مسیر ذخیره: {full_output_dir}")
        print(f"{'='*80}")

if __name__ == "__main__":
    asyncio.run(scrape_domain(BASE_URL, OUTPUT_DIR, MIN_DELAY, MAX_DELAY, MAX_PAGES))