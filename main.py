from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import logging
import os

from utils import scan_and_synchronize

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
def read_root() -> FileResponse:
    """
    При переходе по ссылке в браузере направляем пользователю шаблон index.html
    """
    return FileResponse(
        "/app/static/index.html",
        media_type="text/html",
        headers={"Cache-Control": "no-cache"}
    )


@app.get('/sync')
def synchronize() -> JSONResponse:
    """
    Функция вызывает scan_and_synchronize и получает результаты
    синхронизации и затем отдает их пользователю
    """
    result = scan_and_synchronize()
    return JSONResponse({
        "uploaded": result["uploaded"],
        "updated": result["updated"],
        "deleted": result["deleted"]
    })

