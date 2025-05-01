import json
from fastapi import FastAPI, status, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import logging
import os

from utils import scan_and_synchronize
import uvicorn

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter("%(asctime)s - %(name)s - " "%(levelname)s - %(message)s")
console_handler.setFormatter(formatter)

logger.addHandler(console_handler)

app = FastAPI()

root_dir = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_FOLDER_ABSOLUTE = os.path.join(root_dir, "static")
STATIC_FOLDER = "static"
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="static")


@app.get("/", response_class=HTMLResponse)
def read_root():
    return FileResponse(
        "static/index.html",
        media_type="text/html",
        headers={"Cache-Control": "no-cache"}
    )


@app.get('/sync')
def synchronize(request: Request):
    # Определяем тип ответа на основе заголовков
    result = scan_and_synchronize()
    logger.info(f'result data: {result}')
    return JSONResponse({
        "uploaded": result["uploaded"],
        "updated": result["updated"],
        "deleted": result["deleted"]
    })


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
