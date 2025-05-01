from dotenv import load_dotenv
from fastapi import Path
from functools import lru_cache
import hashlib
import multiprocessing
from multiprocessing import Manager
import os
from os import getenv
from pathlib import Path
import tempfile
import yadisk
from yadisk import YaDisk

# Загружаем данные из .env
load_dotenv()

# Для локального запуска и Docker
DIRECTORY_PATH = Path(os.getenv("DIRECTORY_PATH"))
CLOUD_DIRECTORY = os.getenv("CLOUD_DIRECTORY")

TOKEN = getenv(
    "TOKEN",
)

y = yadisk.YaDisk(token=TOKEN)


def get_local_hash(file_path: Path) -> str:
    """Вычисление SHA-256 хеша локального файла"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


@lru_cache(maxsize=1000)
def get_local_hash_cached(file_path: Path) -> str:
    """Кэширование хэша локального файла"""
    return get_local_hash(file_path)


def get_remote_hash(y: YaDisk, remote_path: Path) -> str:
    """Получение хеша файла на Яндекс.Диске"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = os.path.join(temp_dir, "temp_file")
        y.download(remote_path, temp_file)
        return get_local_hash(temp_file)


def upload_and_update(filename: str, cloud_names: set, results: dict) -> str:
    """Загрузка нового файла на Яндекс.диск или обновление существующего"""
    try:
        local_file = f"{DIRECTORY_PATH}/{filename}"
        remote_file = f"{CLOUD_DIRECTORY}/{filename}"

        # Новый файл
        if filename not in list(cloud_names):
            y.upload(local_file, remote_file)
            results["uploaded"]["names"].append(filename)
            return "uploaded"

        # Проверка необходимости обновления
        if get_local_hash_cached(local_file) != get_remote_hash(
                y, remote_file
        ):
            y.upload(local_file, remote_file, overwrite=True)
            results["updated"]["names"].append(filename)
            return "updated"

        return "no_change"
    except Exception as e:
        print(f"Ошибка обработки {filename}: {str(e)}")
        return "error"


def upload_and_update_file_with_processpool(filenames_list: list[str], cloud_names: set) -> dict:
    """Загрузка и обновление файлов с использованием мультипроцессов"""
    manager = Manager()
    results = manager.dict({
        "uploaded": {"count": 0, "names": manager.list()},
        "updated": {"count": 0, "names": manager.list()}
    })

    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        args = [(f, cloud_names, results) for f in filenames_list]
        pool.starmap(upload_and_update, args)

    return {
        "uploaded": {
            "count": len(results["uploaded"]["names"]),
            "names": list(results["uploaded"]["names"])
        },
        "updated": {
            "count": len(results["updated"]["names"]),
            "names": list(results["updated"]["names"])
        }
    }


def scan_and_synchronize() -> str:
    """Сканирование файлов в локальной папке и в папке на Яндекс.диске и синхронизация"""
    local_path = DIRECTORY_PATH
    cloud_path = CLOUD_DIRECTORY
    # Проверяем подключение
    if not y.check_token():
        return {"error": "there is no connection with Yandex disk"}

    # Получаем имена файлов в папке на Яндекс.диске
    cloud_names = set(item.name for item in y.listdir(cloud_path) if item.type == "file")

    # Получаем имена локальных файлов
    local_files = set(f.name for f in os.scandir(local_path) if f.is_file())

    # Синхронизация
    sync_results = upload_and_update_file_with_processpool(local_files, cloud_names)

    # Определяем файлы для удаления (разница множеств)
    files_to_delete = cloud_names - local_files

    # Удаление
    sync_results["deleted"] = {"count": 0, "names": []}
    for filename in files_to_delete:
        try:
            y.remove(f"{cloud_path}/{filename}")
            sync_results["deleted"]["count"] += 1
            sync_results["deleted"]["names"].append(filename)
        except Exception as e:
            print(f"Ошибка удаления {filename}: {str(e)}")

    return sync_results
