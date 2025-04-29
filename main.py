from dotenv import load_dotenv
from os import getenv
import yadisk

load_dotenv()

DIRECTORY_PATH = getenv(
    "DIRECTORY_PATH",
)

TOKEN = getenv(
    "TOKEN",
)

y = yadisk.YaDisk(token=TOKEN)


def upload_file(file_path, filename: str) -> str:
    """Upload file to cloud"""
    try:
        y.upload(file_path, f"/app_folder/{filename}")
        return "Файл успешно загружен"
    except Exception as ex:
        return f"Ошибка: {ex}"


def download_file(filename: str) -> str:
    """Download file to local folder"""
    try:
        y.download(f"/app_folder/{filename}", f"{DIRECTORY_PATH}/{filename}")
    except Exception as ex:
        return f"Ошибка: {ex}"


# Проверка подключения
if y.check_token():
    print("Подключение успешно")
    print(upload_file("new_file.txt", "new_file.txt"))
    print(download_file("picture.jpg"))
