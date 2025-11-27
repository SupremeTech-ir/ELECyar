import asyncio
import os
import random
import re
from playwright.async_api import async_playwright
from urllib.parse import urljoin, urlparse

# Configuration - متغیرهای قابل تغییر
BASE_URL = "https://eshop.eca.ir"
OUTPUT_DIR = "scraped_data"
MIN_DELAY = 1  # حداقل وقفه بین درخواست‌ها (ثانیه)
MAX_DELAY = 4  # حداکثر وقفه بین درخواست‌ها (ثانیه)
MAX_PAGES = None  # تعداد صفحات مورد نظر (None = همه صفحات)
SCRAPED_URLS_FILE = "scraped_urls.txt"  # فایل ذخیره URLهای اسکرپ شده

visited_urls = set()
scraped_count = 0
user_keywords = []

def load_scraped_urls(filepath: str) -> set:
    """بارگذاری لیست URLهای قبلاً اسکرپ شده"""
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_scraped_url(filepath: str, url: str):
    """ذخیره URL اسکرپ شده در فایل"""
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(f"{url}\n")

def get_keywords_from_user():
    """دریافت کلمات کلیدی از کاربر"""
    print("="*80)
    print("لطفا کلمات کلیدی مورد نظر خود را وارد کنید:")
    print("(هر کلمه را با ویرگول جدا کنید - مثال: مقاومت, خازن, led)")
    print("="*80)
    
    keywords_input = input("کلمات کلیدی: ").strip()
    
    if not keywords_input:
        print("⚠️ هیچ کلمه کلیدی وارد نشد!")
        return []
    
    keywords = [k.strip() for k in keywords_input.split(',') if k.strip()]
    
    print(f"\n✓ تعداد {len(keywords)} کلمه کلیدی ثبت شد:")
    for i, keyword in enumerate(keywords, 1):
        print(f"  {i}. {keyword}")
    print()
    
    return keywords

def matches_keywords(title: str, keywords: list) -> bool:
    """بررسی اینکه آیا عنوان با کلمات کلیدی مطابقت دارد"""
    if not keywords:
        return False
    
    text = title.lower()
    for keyword in keywords:
        if keyword.lower() in text:
            return True
    
    return False

async def extract_product_info(page, url: str):
    """استخراج اطلاعات محصول از یک صفحه"""
    result = f"URL: {url}\n{'='*80}\n\n"
    
    title = ""
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
    
    return result, title

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

async def scrape_page(page, url: str, output_dir: str, scraped_urls_file: str, keywords: list):
    """اسکرِیپ یک صفحه و ذخیره اطلاعات"""
    global scraped_count
    
    try:
        print(f"در حال اسکرِیپ: {url}")
        await page.goto(url, wait_until="networkidle", timeout=30000)
        
        # استخراج اطلاعات
        content, title = await extract_product_info(page, url)
        
        # بررسی مطابقت با کلمات کلیدی
        if not matches_keywords(title, keywords):
            print(f"⊘ نامرتبط - نادیده گرفته شد\n")
            return False
        
        # ذخیره در فایل
        filename = f"page_{scraped_count:04d}.txt"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        # ذخیره URL در فایل URLهای اسکرپ شده
        save_scraped_url(scraped_urls_file, url)
        
        scraped_count += 1
        print(f"✓ ذخیره شد: {filename} (تعداد کل: {scraped_count})\n")
        
        return True
    except Exception as e:
        print(f"✗ خطا در اسکرِیپ {url}: {e}\n")
        return False

async def scrape_domain(base_url: str, output_dir: str, min_delay: int, max_delay: int, keywords: list, max_pages: int = None):
    """اسکرِیپ کل دامنه با وقفه تصادفی"""
    global visited_urls, scraped_count
    
    # ایجاد پوشه خروجی در کنار فایل کد
    script_dir = os.path.dirname(os.path.abspath(__file__))
    full_output_dir = os.path.join(script_dir, output_dir)
    os.makedirs(full_output_dir, exist_ok=True)
    
    # مسیر فایل URLهای اسکرپ شده
    scraped_urls_file = os.path.join(script_dir, SCRAPED_URLS_FILE)
    
    # بارگذاری URLهای قبلاً اسکرپ شده
    already_scraped = load_scraped_urls(scraped_urls_file)
    
    if already_scraped:
        print(f"🔄 تعداد {len(already_scraped)} URL قبلاً اسکرپ شده است و نادیده گرفته می‌شوند.\n")
    
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
            
            # بررسی آیا قبلاً اسکرپ شده
            if current_url in already_scraped:
                print(f"⊙ قبلاً اسکرپ شده - استخراج لینک‌ها: {current_url}")
                try:
                    await page.goto(current_url, wait_until="networkidle", timeout=30000)
                    new_links = await get_all_links(page, base_url)
                    to_visit.update(new_links - visited_urls)
                    print(f"  → {len(new_links - visited_urls)} لینک جدید یافت شد\n")
                except Exception as e:
                    print(f"  ✗ خطا در استخراج لینک‌ها: {e}\n")
                continue
            
            # اسکرِیپ صفحه
            await scrape_page(page, current_url, full_output_dir, scraped_urls_file, keywords)
            
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
        print(f"تعداد کل صفحات مرتبط اسکرپ شده: {scraped_count}")
        print(f"مسیر ذخیره: {full_output_dir}")
        print(f"فایل URLهای اسکرپ شده: {scraped_urls_file}")
        print(f"{'='*80}")

if __name__ == "__main__":
    # دریافت کلمات کلیدی از کاربرفرو
    user_keywords = get_keywords_from_user()
    
    if not user_keywords:
        print("❌ بدون کلمات کلیدی امکان اسکرِیپ وجود ندارد!")
    else:
        asyncio.run(scrape_domain(BASE_URL, OUTPUT_DIR, MIN_DELAY, MAX_DELAY, user_keywords, MAX_PAGES))
