# EduPaperCut Web Server

This project provides a simple FastAPI-based server for processing uploaded
PDF or DOCX documents. Uploaded files are converted to images and sent to the
Aliyun **RecognizeEduPaperStructed** OCR API. The OCR results are saved
alongside the generated images and copied to a directory compatible with a
Paperless server.

## Running

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set environment variables for the OCR service:
   - `OCR_ENDPOINT` – URL of the RecognizeEduPaperStructed API (for example,
     `https://ocr-api.cn-hangzhou.aliyuncs.com/?Action=RecognizeEduPaperStructed&Version=2021-07-07`).
   - `OCR_API_KEY` – authentication token if required.
   - `CONSUME_DIR` – path to the Paperless "consume" directory (default:
     `paperless_consumption`).
3. Start the server:
   ```bash
   uvicorn app:app --reload
   ```

After starting the server, open `http://localhost:8000/` to access a simple
web interface that supports drag & drop or file selection. It posts the file to
`/upload` and shows the JSON response. Files can also be POSTed directly to
`/upload` using multipart form data if preferred.
