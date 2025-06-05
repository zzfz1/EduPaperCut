import os
import shutil
import uuid
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse, HTMLResponse
from pdf2image import convert_from_path
from docx2pdf import convert as docx2pdf_convert
import requests
from typing import List

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"
CONSUME_DIR = os.environ.get("CONSUME_DIR", "paperless_consumption")
API_ENDPOINT = os.environ.get("OCR_ENDPOINT")
API_KEY = os.environ.get("OCR_API_KEY")

app = FastAPI()

HTML_PAGE = """<!DOCTYPE html>
<html lang='en'>
<head>
    <meta charset='UTF-8'>
    <title>EduPaperCut Upload</title>
    <style>
        .dropzone {
            border: 2px dashed #999;
            padding: 40px;
            text-align: center;
            cursor: pointer;
        }
        .dropzone.hover { background: #efefef; }
    </style>
</head>
<body>
<h2>Upload Document</h2>
<div id='dropzone' class='dropzone'>Drag & Drop a file here or click to choose</div>
<input type='file' id='fileInput' style='display:none'>
<pre id='output'></pre>
<script>
const zone = document.getElementById('dropzone');
const input = document.getElementById('fileInput');
zone.addEventListener('click', () => input.click());
zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('hover'); });
zone.addEventListener('dragleave', e => { zone.classList.remove('hover'); });
zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('hover');
    handleFiles(e.dataTransfer.files);
});
input.addEventListener('change', () => handleFiles(input.files));

function handleFiles(files) {
    if (!files.length) return;
    const formData = new FormData();
    formData.append('file', files[0]);
    fetch('/upload', { method: 'POST', body: formData })
      .then(r => r.json())
      .then(data => { document.getElementById('output').textContent = JSON.stringify(data, null, 2); })
      .catch(err => { document.getElementById('output').textContent = err; });
}
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve a minimal interface for uploading files."""
    return HTML_PAGE

for d in [UPLOAD_DIR, OUTPUT_DIR, CONSUME_DIR]:
    os.makedirs(d, exist_ok=True)


def save_upload(file: UploadFile) -> str:
    ext = os.path.splitext(file.filename)[1]
    file_id = f"{uuid.uuid4()}{ext}"
    dest_path = os.path.join(UPLOAD_DIR, file_id)
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return dest_path


def docx_to_pdf(docx_path: str) -> str:
    pdf_path = docx_path.replace(".docx", ".pdf")
    docx2pdf_convert(docx_path, pdf_path)
    return pdf_path


def split_pages(pdf_path: str) -> List[str]:
    images = convert_from_path(pdf_path)
    page_paths = []
    for img in images:
        page_path = os.path.join(OUTPUT_DIR, f"{uuid.uuid4()}.png")
        img.save(page_path, "PNG")
        page_paths.append(page_path)
    return page_paths


def call_ocr(image_path: str) -> dict:
    """Send an image to the Aliyun RecognizeEduPaperStructed API."""
    if not API_ENDPOINT:
        raise RuntimeError("OCR endpoint not configured")

    headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}

    # The API accepts the image bytes directly in the body. Optional parameters
    # like NeedRotate or OutputOricoord can be supplied via query params.
    params = {"NeedRotate": "false", "OutputOricoord": "false"}

    with open(image_path, "rb") as f:
        data = f.read()

    resp = requests.post(API_ENDPOINT, params=params, headers=headers, data=data)
    resp.raise_for_status()
    return resp.json()


def process_document(path: str) -> List[str]:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        path = docx_to_pdf(path)
    if ext in [".pdf"]:
        pages = split_pages(path)
    else:
        pages = [path]

    result_files = []
    for page in pages:
        ocr_result = call_ocr(page)
        result_path = page + ".json"
        with open(result_path, "w") as f:
            f.write(str(ocr_result))
        result_files.append(result_path)
    return result_files


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    path = save_upload(file)
    try:
        result_files = process_document(path)
        for f in result_files:
            shutil.copy(f, CONSUME_DIR)
        return JSONResponse({"status": "ok", "files": result_files})
    except Exception as e:
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)
