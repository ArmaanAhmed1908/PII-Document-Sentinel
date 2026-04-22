# PII-Document-Sentinel
PII Document Sentinel is a full‑stack data security platform designed to automatically ingest, analyze, and encrypt sensitive Personally Identifiable Information (PII) from unstructured documents. It combines advanced OCR, AI‑driven sanitization, and dynamic cryptographic key rotation to safeguard enterprise data against unauthorized access.

Key Features
- **Parallel Document Ingestion:** Upload single or bulk PDF files smoothly. The FastAPI backend employs multithreading (`ThreadPoolExecutor`) to chew through heavily nested data concurrently without freezing the user interface.
- **Robust OCR Extraction:** A custom visual pipeline utilizing OpenCV cleans messy PDF scans (handling blurring, thresholding, and grayscaling) before Tesseract accurately reads the nested text.
- **Dynamic PII Classification:** Custom Regex and Pattern Recognition logic built directly onto Microsoft Presidio categorizes extracted text into three distinct tiers: `CONFIDENTIAL`, `PERSONAL`, and `NON_SENSITIVE`.
- **Self-Healing Key Management:** A decoupled background daemon creates and injects a fresh AES encryption master key every 5 minutes (`key_manager.py`). If a key is stolen, it is almost immediately useless.
- **Data Interceptor & Auth Flow:** An LLM chatbot natively answers questions about uploaded documents while **masking** all sensitive data points with `[Encrypted Tokens]`. Raw data is only unlocked if the original Document Owner explicitly clicks an authorization link generated in real-time via the **EmailJS Rest API**.
- **Performance Analytics:** Real-time metrics processing visually measures our NLP classification precision, recall, and F1-Scores directly on the dashboard.

- Technology Stack
- **Frontend / Dashboard:** [Streamlit](https://streamlit.io/)
- **Backend / Server:** [FastAPI](https://fastapi.tiangolo.com/) (Uvicorn)
- **Computer Vision (OCR):** OpenCV, Tesseract-OCR, pdf2image
- **Machine Learning (PII):** Microsoft Presidio Analyzer
- **Generative AI:** OpenAI SDK
- **Security:** Python Cryptography (Fernet AES)
- **Database:** MySQL
- **Integrations:** EmailJS
- **Reporting:** FPDF, Pandas
