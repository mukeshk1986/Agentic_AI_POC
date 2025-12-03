OCR image code-extraction

This folder contains `scripts/ocr_extract_code.py` — a small utility to recursively find images in a directory, run Tesseract OCR, and extract code-like blocks into `extracted_code/`.

Setup (Windows PowerShell):

- Install Tesseract OCR for Windows:
  - Download from https://github.com/tesseract-ocr/tesseract/releases (choose an installer for Windows) and install.
  - Make sure the Tesseract install directory (e.g. `C:\Program Files\Tesseract-OCR`) is on your `PATH`.

- Install Python dependencies (from repo root):

```powershell
python -m pip install -r requirements.txt
```

Run the script (from repo root):

```powershell
python .\scripts\ocr_extract_code.py -s . -o extracted_code
```

Options:
- `-s/--source` : source directory to scan (default `.`)
- `-o/--output` : output directory to write extracted text/code (default `extracted_code`)
- `--min-lines` : minimum non-empty lines to consider a block as code (default `2`)
- `--no-opencv` : disable OpenCV preprocessing (if OpenCV isn't desired)
- `-v/--verbose` : verbose logging

Notes:
- The script uses `pytesseract` and optionally `opencv-python` if available to improve OCR quality.
- OCR accuracy varies by image quality; consider improving contrast or using higher-resolution images for better results.
