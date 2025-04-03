from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import shutil
import os
from PIL import Image
import piexif
from datetime import datetime
from io import BytesIO
import openpyxl

app = FastAPI()

UPLOAD_DIR = "uploaded_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

templates = Jinja2Templates(directory="templates")
app.mount("/uploaded_images", StaticFiles(directory=UPLOAD_DIR), name="uploaded_images")

@app.get("/", response_class=HTMLResponse)
async def upload_form(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/upload", response_class=HTMLResponse)
async def upload_image(request: Request, files: list[UploadFile] = File(...)):
    images_data = []

    for file in files:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            img = Image.open(file_path)
            exif_data = img.info.get("exif")
            if exif_data:
                exif_dict = piexif.load(exif_data)
                date_taken_str = exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal].decode("utf-8")
                date_taken = datetime.strptime(date_taken_str, "%Y:%m:%d %H:%M:%S")
            else:
                date_taken = "不明"
        except Exception:
            date_taken = "不明"

        images_data.append({
            "filename": file.filename,
            "file_url": f"/uploaded_images/{file.filename}",
            "date_taken": date_taken
        })

    images_data.sort(key=lambda x: x["date_taken"] if x["date_taken"] != "不明" else datetime.max)

    return templates.TemplateResponse("upload.html", {
        "request": request,
        "images": images_data
    })

@app.get("/export")
async def export_excel():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Photo List"
    ws.append(["ファイル名", "撮影日時", "画像URL"])

    for filename in os.listdir(UPLOAD_DIR):
        file_path = os.path.join(UPLOAD_DIR, filename)
        try:
            img = Image.open(file_path)
            exif_data = img.info.get("exif")
            if exif_data:
                exif_dict = piexif.load(exif_data)
                date_taken_str = exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal].decode("utf-8")
            else:
                date_taken_str = "不明"
        except Exception:
            date_taken_str = "不明"

        ws.append([filename, date_taken_str, f"/uploaded_images/{filename}"])

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=photo_list.xlsx"}
    )
