from pathlib import Path

SCRAPED_DATA_DIR = "scraped_data"
OUTPUT_DIR = "merged_dataset_english"
MAX_FILES_PER_CATEGORY = 20
SEPARATOR = "\n" + "="*120 + "\n\n"

ENGLISH_FOLDER_NAMES = {
    "فلایت کنترل ربات": "flight_controller",
    "فن و محافظ فن": "fan",
    "فیبر مدار چاپی - برد بورد": "pcb_breadboard",
    "فیوز": "fuse",
    "کلید، سوئیچ، کیپد": "switch_keypad",
    "لیزر": "laser",
    "ماژول GPS - GSM - GPRS": "gps_gsm_gprs",
    "ماژول اولتراسونیک - فاصله سنج": "ultrasonic",
    "ماژول تایمر و پالس": "timer_pulse",
    "ماژول تغذیه - ولتاژ و شارژ": "power_supply",
    "ماژول شبکه و WIFI": "wifi_network",
    "ماژول صوتی": "audio_module",
    "ماژول مادون قرمز IR": "ir_module",
    "ماژول مبدل و واسط": "converter_interface",
    "ماژول نمایشگر": "display_module",
    "ماژول های ESP و اینترنت اشیا": "esp_iot",
    "ماژول های وزن، نیرو و فشار": "loadcell_pressure",
    "ماژول و سوئیچ PIR": "pir_sensor",
    "متفرقه": "miscellaneous",
    "مقاومت": "resistor",
    "موتور": "motor",
    "مولتی متر": "multimeter",
    "میکروسکوپ و ذره بین": "microscope_magnifier",
    "میکروکنترلر و پروسسور": "microcontroller_processor",
    "نمایشگر HDMI": "hdmi_display",
    "نمایشگر LCD": "lcd_display",
    "هیت سینک و المان حرارتی": "heatsink",
    "LED و تجهیزات مرتبط": "led",
    "آداپتور، سوئیچینگ و اینورتر": "adapter_inverter",
    "اسپارک گپ": "spark_gap",
    "اسیلوسکوپ و لاجیک آنالایزر": "oscilloscope_logic",
    "آلتراسونیک کلینر": "ultrasonic_cleaner",
    "آنتن": "antenna",
    "انواع پیچ گوشتی و آچار": "screwdrivers_wrenches",
    "آی سی - تراشه": "ic_chip",
    "باتری، جاباتری و شارژر": "battery_charger",
    "بازر، پیزو و بلندگو": "buzzer_speaker",
    "پراب و کابل تست": "probe_cables",
    "پنس، تیغه و کاتر": "tweezers_blades",
    "پیچ و اسپیسر": "screw_spacer",
    "پین هدر": "pin_header",
    "تجهیزات تعمیر موبایل": "mobile_repair_tools",
    "ترانزیستور": "transistor",
    "ترانس، چوک، فریت، هسته": "transformer_choke",
    "جعبه و کیس بردهای الکترونیکی": "enclosure",
    "چرخ دنده": "gear",
    "چرخ ربات": "robot_wheel",
    "خازن": "capacitor",
    "دماسنج و رطوبت سنج": "thermometer_hygrometer",
    "دیود": "diode",
    "رزبری پای Raspberry Pi": "raspberry_pi",
    "رگولاتور": "regulator",
    "رله": "relay",
    "ریموت کنترلر": "remote_control",
    "ریموت و ماژول های ارتباطی RF": "rf_remote",
    "سگمنت و ماتریس": "segment_matrix",
    "سلف": "inductor",
    "سوكت، کانکتور، فیش": "connector_socket",
    "سیم و کابل": "wire_cable",
}

def clean_text(text: str) -> str:
    lines = [l.rstrip() for l in text.splitlines()]
    cleaned, blanks = [], 0
    for l in lines:
        if not l.strip():
            blanks += 1
            if blanks <= 2: cleaned.append(l)
        else:
            blanks = 0
            cleaned.append(l)
    return "\n".join(cleaned).strip() + "\n\n"

def main():
    src = Path(SCRAPED_DATA_DIR)
    out = Path(OUTPUT_DIR)
    out.mkdir(exist_ok=True)

    total_products = 0
    for folder in src.iterdir():
        if not folder.is_dir(): 
            continue

        eng_name = ENGLISH_FOLDER_NAMES.get(folder.name)
        if not eng_name:
            eng_name = folder.name.replace(" ", "_").replace("-", "_")
            print(f"Auto-mapped (rare): {folder.name} → {eng_name}")

        files = sorted(folder.glob("*.txt"))[:MAX_FILES_PER_CATEGORY]
        if not files:
            continue

        merged = []
        for f in files:
            content = f.read_text(encoding="utf-8", errors="ignore")
            url = content.split("\n", 1)[0] if content.startswith("URL:") else ""
            merged.append(url + "\n" + clean_text(content))
            total_products += 1

        out_file = out / f"merged_{eng_name}.txt"
        out_file.write_text(SEPARATOR.join(merged), encoding="utf-8")
        print(f"{folder.name} → merged_{eng_name}.txt ({len(merged)} items)")

    print(f"\nDONE! Total products merged: {total_products}")       

if __name__ == "__main__":
    main()
