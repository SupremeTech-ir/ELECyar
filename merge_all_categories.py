from pathlib import Path
import logging
import sys

INPUT_ROOT = Path("eca_products")
OUTPUT_ROOT = Path("eca_products_merged")
SEPARATOR = "\n" + "="*120 + "\n\n"
MAX_FILES_PER_SUBCATEGORY = None

# Setup logging
def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    
    file_handler = logging.FileHandler('merge_processing.log', encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger

logger = setup_logging()

def clean_text(text: str) -> str:
    """Clean text by removing excessive blank lines."""
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

def extract_clean_content(file_path: Path) -> str:
    """Extract and clean content from a file."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        lines = content.splitlines()
        
        if not lines:
            return ""
        
        if lines[0].startswith("URL:"):
            lines = lines[1:]
        
        if lines and lines[0].strip().startswith("="):
            lines = lines[1:]
        
        if len(lines) >= 2 and lines[0] == lines[1]:
            lines = lines[1:]
        
        cleaned_text = clean_text("\n".join(lines))
        
        if len(cleaned_text.strip()) < 20:
            return ""
        
        return cleaned_text
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return ""

def process_all_categories():
    """Process all main categories and their subcategories."""
    input_root = INPUT_ROOT
    if not input_root:
        print("\nPlease check the folder location and try again.")
        return
        
    OUTPUT_ROOT.mkdir(exist_ok=True)
    
    total_main = 0
    total_sub = 0
    
    print(f"\n{'='*60}")
    print(f"Starting Automated Merging Process")
    print(f"{'='*60}")
    
    # Process each main category
    for main_path in sorted(input_root.iterdir()):
        if not main_path.is_dir():
            continue
                
        category_name = main_path.name
        print(f"\nProcessing: {category_name}")

        main_output_dir = OUTPUT_ROOT / category_name
        main_output_dir.mkdir(exist_ok=True)
        
        # Process each subcategory
        for sub_path in sorted(main_path.iterdir()):
            if not sub_path.is_dir():
                continue
            
            sub_name = sub_path.name
            txt_files = list(sub_path.glob("*.txt"))
            
            if not txt_files:
                continue

            if MAX_FILES_PER_SUBCATEGORY:
                txt_files = txt_files[:MAX_FILES_PER_SUBCATEGORY]
            
            merged_contents = []
            valid_files = 0
            
            for txt_file in txt_files:
                content = extract_clean_content(txt_file)
                if content:
                    merged_contents.append(content)
                    valid_files += 1
            
            if not merged_contents:
                continue
            
            output_filename = f"{sub_name}_merged.txt"
            output_path = main_output_dir / output_filename

            try:
                output_path.write_text(SEPARATOR.join(merged_contents), encoding="utf-8")
                total_sub += 1
            except Exception as e:
                logger.error(f"Error writing {output_path}: {e}")
        
        total_main += 1
              
    # Summary
    print(f"\n{'='*60}")
    print(f"PROCESSING COMPLETE!")
    print(f"{'='*60}")
    print(f"Main categories: {total_main}")
    print(f"Subcategories: {total_sub}")
    print(f"{'='*60}")

def main():
    import time
    time.sleep(2)
    
    process_all_categories()
    
if __name__ == "__main__":
    main()