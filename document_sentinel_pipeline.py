import os
import re
import cv2
import numpy as np
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

# =========================
# 🔧 MANUAL PATH SETTINGS
# =========================

# 👉 Set your Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\V S Keershaa\Downloads\Tesseract\tesseract.exe"

# 👉 Set your Poppler bin path
POPPLER_PATH = r"C:\poppler\poppler-24.08.0\Library\bin"
# ⚠️ Replace 'poppler-xx' with your actual folder name

# =========================
# OCR CONFIG
# =========================
TESSERACT_CONFIG = r'--oem 3 --psm 6'

# =========================
# PREPROCESS CONFIG
# =========================
PREPROCESS_CONFIG = {
    "grayscale": True,
    "median_blur": True,
    "contrast": True,
    "threshold": True,
    "sharpen": False
}

# =========================
# IMAGE PREPROCESSING
# =========================
def preprocess_image(image, config=PREPROCESS_CONFIG):
    img = np.array(image)

    if config["grayscale"]:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    if config["median_blur"]:
        img = cv2.medianBlur(img, 3)

    if config["contrast"]:
        img = cv2.equalizeHist(img)

    if config["threshold"]:
        img = cv2.adaptiveThreshold(
            img, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, 2
        )

    if config["sharpen"]:
        kernel = np.array([[0, -1, 0],
                           [-1, 5,-1],
                           [0, -1, 0]])
        img = cv2.filter2D(img, -1, kernel)

    return img

# =========================
# OCR FUNCTIONS
# =========================
def ocr_image(image):
    return pytesseract.image_to_string(image, config=TESSERACT_CONFIG)

def extract_best_text(raw_img, processed_img):
    text_raw = ocr_image(raw_img)
    text_processed = ocr_image(processed_img)

    return text_processed if len(text_processed) > len(text_raw) else text_raw

# =========================
# TEXT CLEANING
# =========================
def clean_text(text):
    text = re.sub(r'[^\w\s@./:\-]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# =========================
# PDF PROCESSING
# =========================
def process_pdf(pdf_path):
    pages = convert_from_path(pdf_path, poppler_path=POPPLER_PATH)
    full_text = ""

    for page in pages:
        raw_img = np.array(page)
        processed_img = preprocess_image(page)

        text = extract_best_text(raw_img, processed_img)
        text = clean_text(text)

        full_text += text + "\n"

    return full_text

# =========================
# MAIN PIPELINE
# =========================
def run_pipeline(pdf_folder, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    pdf_files = [f for f in os.listdir(pdf_folder) if f.endswith(".pdf")]

    for pdf in pdf_files:
        pdf_path = os.path.join(pdf_folder, pdf)
        print(f"Processing: {pdf}")

        try:
            text = process_pdf(pdf_path)

            output_file = os.path.join(output_folder, pdf.replace(".pdf", ".txt"))
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(text)

        except Exception as e:
            print(f"❌ Error processing {pdf}: {e}")

    print("✅ DONE!")

# =========================
# ENTRY POINT
# =========================
if __name__ == "__main__":
    INPUT_FOLDER = "input_pdfs"
    OUTPUT_FOLDER = "output_texts"

    run_pipeline(INPUT_FOLDER, OUTPUT_FOLDER)