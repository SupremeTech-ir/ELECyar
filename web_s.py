import asyncio
import os
import random
import re
from playwright.async_api import async_playwright
from urllib.parse import urljoin, urlparse

# Configuration - متغیرهای قابل تغییر
BASE_URL = "https://eshop.eca.ir"
OUTPUT_DIR = "scraped_data"
MIN_DELAY = 3  # حداقل وقفه بین درخواست‌ها (ثانیه)
MAX_DELAY = 8  # حداکثر وقفه بین درخواست‌ها (ثانیه)
MAX_PAGES = None  # تعداد صفحات مورد نظر (None = همه صفحات)
SCRAPED_URLS_FILE = "scraped_urls.txt"  # فایل ذخیره URLهای اسکرپ شده

# دسته‌بندی‌ها و کلمات کلیدی مرتبط
CATEGORIES = {
    "مقاومت": ["مقاومت", "resistor"],
    "خازن": ["خازن", "capacitor"],
    "سلف": ["سلف", "inductor", "coil"],
    "دیود": ["دیود", "diode"],
    "آی سی - تراشه": ["آی سی", "تراشه", "ic", "chip"],
    "میکروکنترلر و پروسسور": ["میکروکنترلر", "میکرو کنترلر", "پروسسور", "microcontroller", "processor", "mcu"],
    "رگولاتور": ["رگولاتور", "regulator"],
    "ترانزیستور": ["ترانزیستور", "transistor"],
    "ترایاک و تریستور": ["ترایاک", "تریستور", "triac", "thyristor"],
    "LED و تجهیزات مرتبط": ["led", "ال ای دی"],
    "سگمنت و ماتریس": ["سگمنت", "ماتریس", "segment", "matrix"],
    "کریستال و اسیلاتور": ["کریستال", "اسیلاتور", "crystal", "oscillator"],
    "وریستور": ["وریستور", "varistor"],
    "رله": ["رله", "relay"],
    "پین هدر": ["پین هدر", "pin header", "header"],
    "سوكت، کانکتور، فیش": ["سوکت", "کانکتور", "فیش", "socket", "connector"],
    "کلید، سوئیچ، کیپد": ["کلید", "سوئیچ", "کیپد", "switch", "keypad", "button"],
    "ترمینال پیچی و کشویی": ["ترمینال", "terminal"],
    "فیوز": ["فیوز", "fuse"],
    "بازر، پیزو و بلندگو": ["بازر", "پیزو", "بلندگو", "buzzer", "piezo", "speaker"],
    "آنتن": ["آنتن", "antenna"],
    "ریموت کنترلر": ["ریموت", "remote"],
    "فیبر مدار چاپی - برد بورد": ["فیبر", "برد", "pcb", "breadboard", "بورد"],
    "سیم و کابل": ["سیم", "کابل", "wire", "cable"],
    "ترانس، چوک، فریت، هسته": ["ترانس", "چوک", "فریت", "هسته", "transformer", "choke", "ferrite", "core"],
    "پوگو پین - پین تست": ["پوگو", "پین تست", "pogo", "test pin"],
    "فن و محافظ فن": ["فن", "fan"],
    "هیت سینک و المان حرارتی": ["هیت سینک", "المان حرارتی", "heat sink", "heatsink"],
    "لیزر": ["لیزر", "laser"],
    "اسپارک گپ": ["اسپارک گپ", "spark gap"],
    "پیچ و اسپیسر": ["پیچ", "اسپیسر", "screw", "spacer"],
    "جعبه و کیس بردهای الکترونیکی": ["جعبه", "کیس", "box", "case", "enclosure"],
    "برق ساختمان": ["برق ساختمان", "پریز", "کلید برق"],
    "تجهیزات تعمیر موبایل": ["تجهیزات تعمیر موبایل", "mobile repair tools", "موبایل"],
    "تجهیزات تست و اندازه گیری": ["تجهیزات تست", "تجهیزات اندازه گیری", "test equipment", "measurement equipment"],
    "مولتی متر": ["مولتی متر", "multimeter", "چند متر"],
    "اسیلوسکوپ و لاجیک آنالایزر": ["اسیلوسکوپ", "لاجیک آنالایزر", "oscilloscope", "logic analyzer"],
    "پراب و کابل تست": ["پراب", "کابل تست", "probe", "test cable"],
    "آلتراسونیک کلینر": ["آلتراسونیک کلینر", "ultrasonic cleaner", "دستگاه تمیز کننده"],
    "میکروسکوپ و ذره بین": ["میکروسکوپ", "ذره بین", "microscope", "magnifying glass"],
    "دماسنج و رطوبت سنج": ["دماسنج", "رطوبت سنج", "thermometer", "hygrometer", "temperature", "humidity meter"],
    "انواع پیچ گوشتی و آچار": ["پیچ گوشتی", "آچار", "screwdriver", "wrench"],
    "آلن آچار": ["آلن آچار", "allen key", "hex key"],
    "آچار سوکت زن و پرسی": ["آچار سوکت زن", "پرسی", "socket wrench", "press tool"],
    "ابزار سوراخ کاری و برش": ["ابزار سوراخ کاری", "ابزار برش", "drilling tool", "cutting tool"],
    "اسپری سشوار و چسب حرارتی": ["اسپری", "سشوار", "چسب حرارتی", "soldering iron", "heat resistant glue"],
    "سیم چین، کف چین و لخت کن": ["سیم چین", "کف چین", "لخت کن", "wire stripper", "wire cutter"],
    "انبردست و دم باریک": ["انبردست", "دم باریک", "pliers", "thin nose pliers"],
    "پنس، تیغه و کاتر": ["پنس", "تیغه", "کاتر", "tweezers", "blade", "cutter"],
    "چسب نسوز و ساده": ["چسب نسوز", "چسب ساده", "heat resistant glue", "adhesive"],
    "جعبه ابزار و قطعات": ["جعبه ابزار", "قطعات", "tool box", "parts"],
    "اتصالات مکانیکی": ["اتصالات مکانیکی", "mechanical connections", "mechanical joints"],
    "شاسی ربات": ["شاسی ربات", "robot chassis", "frame"],
    "چرخ ربات": ["چرخ ربات", "robot wheel", "wheel"],
    "موتور": ["موتور", "motor"],
    "ملخ پروازی": ["ملخ پروازی", "propeller", "flying propeller"],
    "دسته کنترل": ["دسته کنترل", "control handle", "joystick"],
    "چرخ دنده": ["چرخ دنده", "gear", "gear wheel"],
    "فلایت کنترل ربات": ["فلایت کنترل", "flight controller", "robot flight control"],
    "پیش ساخته": ["پیش ساخته", "premade", "kit"],
    "سولونوئید": ["سولونوئید", "solenoid"],
    "ماژول اولتراسونیک - فاصله سنج": ["ماژول اولتراسونیک", "فاصله سنج", "ultrasonic module", "distance sensor"],
    "ماژول تاچ و اثر انگشت": ["ماژول تاچ", "اثر انگشت", "touch module", "fingerprint module"],
    "ماژول و سنسور بخار سرد": ["ماژول بخار", "سنسور بخار", "vapor sensor", "cool vapor sensor"],
    "ماژول پردازش تصویر و دوربین": ["ماژول پردازش تصویر", "دوربین", "camera module", "image processing module"],
    "ماژول پرینتر، چاپگر": ["ماژول پرینتر", "چاپگر", "printer module"],
    "ماژول پزشکی": ["ماژول پزشکی", "medical module"],
    "ماژول تغذیه - ولتاژ و شارژ": ["ماژول تغذیه", "ولتاژ", "شارژ", "power module", "voltage module"],
    "ولت متر و آمپر متر روپنلی": ["ولت متر", "آمپر متر", "rohde schwarz", "voltmeter", "ammeter"],
    "ماژول جریان": ["ماژول جریان", "current module"],
    "ماژول تایمر و پالس": ["ماژول تایمر", "پالس", "timer module", "pulse module"],
    "ماژول حرکت و لرزش": ["ماژول حرکت", "لرزش", "motion module", "vibration module"],
    "ماژول درایور موتور": ["ماژول درایور موتور", "motor driver module"],
    "ماژول دما و رطوبت": ["ماژول دما", "رطوبت", "temperature module", "humidity module"],
    "ماژول نمایشگر": ["ماژول نمایشگر", "display module"],
    "ماژول LED و سگمنت": ["ماژول LED", "سگمنت", "led module", "segment module"],
    "ریموت و ماژول های ارتباطی RF": ["ریموت", "RF", "remote", "rf module"],
    "ماژول شتاب سنج و ژیروسکوپ": ["ماژول شتاب سنج", "ژیروسکوپ", "accelerometer", "gyroscope"],
    "ماژول شبکه و WIFI": ["ماژول شبکه", "WIFI", "network module", "wifi module"],
    "ماژول های ESP و اینترنت اشیا": ["ESP", "اینترنت اشیا", "esp module", "iot module"],
    "ماژول بلوتوث Bluetooth": ["ماژول بلوتوث", "bluetooth", "bluetooth module"],
    "ماژول صوتی": ["ماژول صوتی", "audio module"],
    "ماژول های وزن، نیرو و فشار": ["ماژول وزن", "نیرو", "فشار", "weight module", "force module", "pressure module"],
    "ماژول و سنسور گاز": ["ماژول گاز", "سنسور گاز", "gas module", "gas sensor"],
    "دیمرهای DC و AC": ["دیمر DC", "دیمر AC", "dc dimmer", "ac dimmer"],
    "ماژول مبدل و واسط": ["ماژول مبدل", "واسط", "converter module", "interface module"],
    "ماژول رله و سوئیچ": ["ماژول رله", "سوئیچ", "relay module", "switch module"],
    "ماژول و سوئیچ PIR": ["ماژول PIR", "PIR", "pir module", "pir sensor"],
    "ماژول GPS - GSM - GPRS": ["GPS", "GSM", "GPRS", "gps module", "gsm module", "gprs module"],
    "ماژول و تگ RFID": ["ماژول RFID", "RFID", "rfid module", "rfid tag"],
    "کوره القایی ZVS": ["کوره القایی", "ZVS", "induction heater", "zvs"],
    "ماژول مادون قرمز IR": ["ماژول IR", "IR", "ir module", "infrared module"],
    "سایر ماژول های کاربردی": ["سایر ماژول", "other module", "miscellaneous module"],
    "آداپتور، سوئیچینگ و اینورتر": ["آداپتور", "سوئیچینگ", "اینورتر", "adapter", "switching", "inverter"],
    "باتری، جاباتری و شارژر": ["باتری", "شارژر", "battery", "charger"],
    "ماژول تغذیه و شارژر زبری پای": ["ماژول تغذیه زبری پای", "raspberry pi power module"],
    "رزبری پای Raspberry Pi": ["رزبری پای", "raspberry pi", "raspberry"],
    "مینی کامپیوتر لینوکسی - اندرویدی": ["مینی کامپیوتر لینوکسی", "اندرویدی", "linux mini computer", "android mini computer"],
    "تی وی باکس TV BOX": ["تی وی باکس", "tv box", "tvbox"],
    "مینی کامپیوتر ویندوزی": ["مینی کامپیوتر ویندوزی", "windows mini computer"],
    "خانواده Orange Pi": ["Orange Pi", "orange pi", "opi"],
    "نمایشگر TFT": ["نمایشگر TFT", "tft display"],
    "نمایشگر OLED": ["نمایشگر OLED", "oled display"],
    "نمایشگر LCD/GLCD": ["نمایشگر LCD", "GLCD", "lcd display", "glcd display"],
    "ماژول نمایشگر": ["ماژول نمایشگر", "display module"],
    "نمایشگر HDMI/VGA": ["نمایشگر HDMI", "VGA", "hdmi display", "vga display"],
    "تجهیزات حفاظتی و کنترلی": ["تجهیزات حفاظتی", "تجهیزات کنترلی", "safety equipment", "control equipment"],
    "متفرقه": []  # برای محصولات بدون دسته‌بندی
}

visited_urls = set()
scraped_count = 0
category_counts = {cat: 0 for cat in CATEGORIES.keys()}

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

def detect_category(title: str) -> str:
    """تشخیص دسته‌بندی بر اساس عنوان"""
    text = title.lower()
    
    for category, keywords in CATEGORIES.items():
        if category == "متفرقه":
            continue
        for keyword in keywords:
            if keyword.lower() in text:
                return category
    
    return "متفرقه"

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

async def scrape_page(page, url: str, output_dir: str, scraped_urls_file: str):
    """اسکرِیپ یک صفحه و ذخیره اطلاعات"""
    global scraped_count, category_counts
    
    try:
        print(f"در حال اسکرِیپ: {url}")
        await page.goto(url, wait_until="networkidle", timeout=30000)
        
        # استخراج اطلاعات
        content, title = await extract_product_info(page, url)
        
        # تشخیص دسته‌بندی
        category = detect_category(title)
        
        # ایجاد پوشه دسته‌بندی
        category_dir = os.path.join(output_dir, category)
        os.makedirs(category_dir, exist_ok=True)
        
        # ذخیره در فایل
        filename = f"page_{category_counts[category]:04d}.txt"
        filepath = os.path.join(category_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        # ذخیره URL در فایل URLهای اسکرپ شده
        save_scraped_url(scraped_urls_file, url)
        
        category_counts[category] += 1
        scraped_count += 1
        print(f"✓ ذخیره شد در [{category}]: {filename} (تعداد کل: {scraped_count})")
        
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
    
    # مسیر فایل URLهای اسکرپ شده
    scraped_urls_file = os.path.join(script_dir, SCRAPED_URLS_FILE)
    
    # بارگذاری URLهای قبلاً اسکرپ شده
    already_scraped = load_scraped_urls(scraped_urls_file)
    visited_urls.update(already_scraped)
    
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
            
            # اسکرِیپ صفحه
            success = await scrape_page(page, current_url, full_output_dir, scraped_urls_file)
            
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
        print(f"تعداد کل صفحات اسکرِیپ شده: {scraped_count}")
        print(f"\nتوزیع دسته‌بندی‌ها:")
        for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            if count > 0:
                print(f"  {category}: {count} محصول")
        print(f"\nمسیر ذخیره: {full_output_dir}")
        print(f"فایل URLهای اسکرپ شده: {scraped_urls_file}")
        print(f"{'='*80}")

if __name__ == "__main__":
    asyncio.run(scrape_domain(BASE_URL, OUTPUT_DIR, MIN_DELAY, MAX_DELAY, MAX_PAGES))
