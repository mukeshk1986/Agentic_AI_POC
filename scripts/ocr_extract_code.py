import os
import re
import argparse
import logging
from pathlib import Path
from typing import List, Tuple

from PIL import Image
import pytesseract

try:
    import cv2
    import numpy as np
    _HAS_OPENCV = True
except Exception:
    _HAS_OPENCV = False

IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.tif', '.tiff', '.bmp', '.svg'}

CODE_KEYWORDS = [
    r"\bdef\b",
    r"\bclass\b",
    r"\bimport\b",
    r"#include",
    r"using\s+System",
    r"console\.log",
    r"printf\(",
    r"SELECT\b",
    r"INSERT\b",
    r"UPDATE\b",
    r"DELETE\b",
    r"\{\s*$",
    r";\s*$",
]

CODE_PAT = re.compile('|'.join(CODE_KEYWORDS), re.IGNORECASE)


def find_images(root: Path) -> List[Path]:
    files = []
    for p in root.rglob('*'):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
            files.append(p)
    return sorted(files)


def preprocess_with_opencv(pil_img: Image.Image):
    arr = np.array(pil_img.convert('L'))
    # denoise and adaptive threshold
    arr = cv2.bilateralFilter(arr, 9, 75, 75)
    th = cv2.adaptiveThreshold(arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY, 15, 9)
    return Image.fromarray(th)


def ocr_image(path: Path, use_opencv: bool = True) -> str:
    img = Image.open(path)
    if use_opencv and _HAS_OPENCV:
        try:
            img = preprocess_with_opencv(img)
        except Exception:
            pass
    # Tesseract config: --psm 6 assumes a block of text
    try:
        text = pytesseract.image_to_string(img, config='--psm 6')
    except Exception as e:
        logging.warning("pytesseract failed on %s: %s", path, e)
        text = ''
    return text


def is_code_line(line: str) -> bool:
    if not line.strip():
        return False
    if CODE_PAT.search(line):
        return True
    # Lines with many symbols typical for code
    symbol_count = sum(line.count(c) for c in ['{', '}', ';', '(', ')', '=', '<', '>'])
    if symbol_count >= 2:
        return True
    # Indentation with 4+ spaces often indicates code
    if len(line) - len(line.lstrip(' ')) >= 4:
        return True
    return False


def extract_code_blocks(text: str, min_lines: int = 2) -> List[Tuple[int,int,List[str]]]:
    lines = text.splitlines()
    blocks = []
    buff = []
    start = None
    for i, ln in enumerate(lines):
        if is_code_line(ln):
            if start is None:
                start = i
            buff.append(ln)
        else:
            if buff:
                if len([l for l in buff if l.strip()]) >= min_lines:
                    blocks.append((start, i - 1, buff.copy()))
                buff = []
                start = None
    if buff and len([l for l in buff if l.strip()]) >= min_lines:
        blocks.append((start, len(lines) - 1, buff.copy()))
    return blocks


def guess_extension(block_lines: List[str]) -> str:
    joined = '\n'.join(block_lines)
    if re.search(r"\bdef\b|:\n\s+return|import\s+\w+", joined):
        return 'py'
    if '{' in joined and ';' in joined:
        return 'c'
    if 'class ' in joined and 'System' in joined:
        return 'cs'
    if 'SELECT' in joined.upper() or 'FROM' in joined.upper():
        return 'sql'
    if 'function ' in joined or 'console.log' in joined:
        return 'js'
    return 'txt'


def save_outputs(image_path: Path, ocr_text: str, blocks: List[Tuple[int,int,List[str]]], out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    base = image_path.stem
    # Save full OCR text
    ocr_file = out_dir / f"{base}_ocr.txt"
    ocr_file.write_text(ocr_text, encoding='utf-8')

    for idx, (s, e, lines) in enumerate(blocks, start=1):
        ext = guess_extension(lines)
        block_file = out_dir / f"{base}_block{idx}.{ext}"
        block_file.write_text('\n'.join(lines), encoding='utf-8')


def process_images(src: Path, out: Path, min_lines: int = 2):
    images = find_images(src)
    logging.info("Found %d image(s)", len(images))
    summary = []
    for p in images:
        logging.info("Processing %s", p)
        txt = ocr_image(p)
        blocks = extract_code_blocks(txt, min_lines=min_lines)
        save_outputs(p, txt, blocks, out)
        summary.append((p, len(blocks)))
    return summary


def make_argparser():
    p = argparse.ArgumentParser(description='OCR images and extract code-like blocks')
    p.add_argument('-s', '--source', default='.', help='Source directory to search for images')
    p.add_argument('-o', '--output', default='extracted_code', help='Output directory to write extracted text and code')
    p.add_argument('--min-lines', type=int, default=2, help='Minimum non-empty lines to consider a block as code')
    p.add_argument('--no-opencv', action='store_true', help='Do not use OpenCV preprocessing even if available')
    p.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    return p


def main():
    args = make_argparser().parse_args()
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format='%(levelname)s: %(message)s')
    src = Path(args.source).resolve()
    out = Path(args.output).resolve()
    logging.info("Source: %s", src)
    logging.info("Output: %s", out)
    summary = process_images(src, out, min_lines=args.min_lines)
    logging.info("Done. Summary:")
    for p, cnt in summary:
        logging.info("%s -> %d code block(s)", p, cnt)


if __name__ == '__main__':
    main()
