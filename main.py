from dotenv import load_dotenv
from functools import lru_cache
import hashlib
import multiprocessing
from multiprocessing import Manager
import os
from os import getenv
from pprint import pprint
import tempfile
import yadisk

load_dotenv()

DIRECTORY_PATH = getenv(
    "DIRECTORY_PATH",
)

CLOUD_DIRECTORY = getenv(
    "CLOUD_DIRECTORY",
)
TOKEN = getenv(
    "TOKEN",
)

y = yadisk.YaDisk(token=TOKEN)


def get_local_hash(file_path):
    """Вычисление SHA-256 хеша локального файла"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


@lru_cache(maxsize=1000)
def get_local_hash_cached(file_path):
    return get_local_hash(file_path)


def get_remote_hash(y, remote_path):
    """Получение хеша файла на Яндекс.Диске"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = os.path.join(temp_dir, "temp_file")
        y.download(remote_path, temp_file)
        return get_local_hash(temp_file)


def upload_and_update(filename, cloud_names, results):
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


def upload_and_update_file_with_processpool(filenames_list, cloud_names):
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


def scan_and_synchronize(local_path, cloud_path) -> str:
    """Сканирование файлов в локальной папке и в папке на Яндекс.диске и синхронизация"""
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
    delete_results = {"count": 0, "names": []}
    for filename in files_to_delete:
        try:
            y.remove(f"{cloud_path}/{filename}")
            delete_results["count"] += 1
            delete_results["names"].append(filename)
        except Exception as e:
            print(f"Ошибка удаления {filename}: {str(e)}")

    return {
        "uploaded": sync_results["uploaded"],
        "updated": sync_results["updated"],
        "deleted": delete_results
    }


if __name__ == "__main__":
    pprint(scan_and_synchronize(DIRECTORY_PATH, CLOUD_DIRECTORY))
