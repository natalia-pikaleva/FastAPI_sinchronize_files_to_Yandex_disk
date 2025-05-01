from datetime import datetime, timezone
from dateutil.parser import parse
from dotenv import load_dotenv
import hashlib
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


def get_local_metadata(file_path):
    """Метаданные локального файла"""
    stat = os.stat(file_path)
    return {
        "size": stat.st_size,
        "mtime": int(stat.st_mtime)
    }


def get_cloud_metadata(y, cloud_path):
    """Получение метаданных с обработкой разных форматов времени"""
    metadata = {}
    for item in y.listdir(cloud_path):
        if item.type != "file":
            continue

        try:
            # Если modified уже datetime
            if isinstance(item.modified, datetime):
                dt = item.modified.astimezone(timezone.utc)
                mtime = int(dt.timestamp())
            # Если modified - строка
            else:
                dt = datetime.fromisoformat(
                    item.modified.replace('Z', '+00:00')
                ).astimezone(timezone.utc)
                mtime = int(dt.timestamp())

            metadata[item.name] = {
                "size": item.size,
                "mtime": mtime
            }

        except Exception as e:
            print(f"Ошибка обработки {item.name}: {str(e)}")
            continue

    return metadata


def get_local_hash(file_path):
    """Вычисление SHA-256 хеша локального файла"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


def get_remote_hash(y, remote_path):
    """Получение хеша файла на Яндекс.Диске"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = os.path.join(temp_dir, "temp_file")
        y.download(remote_path, temp_file)
        return get_local_hash(temp_file)


def scan_and_synchronize(local_path, cloud_path) -> str:
    """Сканирование файлов в локальной папке и в папке на Яндекс.диске и синхронизация"""
    # Проверяем подключение
    if not y.check_token():
        return {"error": "there is no connection with Yandex disk"}

    cloud_names = set([file.name for file in y.listdir(cloud_path) if file.type == "file"])

    pprint(cloud_names)
    results = {
        "uploaded": {"count": 0,
                     "names": []},
        "updated": {"count": 0,
                    "names": []},
        "deleted": {"count": 0,
                    "names": []}
    }

    # Перебираем файлы в локальной папке, загружаем на Яндекс.диск отсутствующие файлы,
    # обновляем файлы
    for file in os.scandir(local_path):
        if not file.is_file():
            continue

        local_file = file.path
        remote_file = f"{cloud_path}/{file.name}"

        # Новый файл
        if file.name not in list(cloud_names):
            y.upload(local_file, remote_file)
            results["uploaded"]["count"] += 1
            results["uploaded"]["names"].append(file.name)
            continue

        # Проверка необходимости обновления
        if get_local_hash(local_file) != get_remote_hash(
                y, remote_file
        ):
            y.upload(local_file, remote_file, overwrite=True)
            results["updated"]["count"] += 1
            results["updated"]["names"].append(file.name)

        cloud_names.discard(file.name)

    # Удаляем отсутствующие в локальной папке файлы на Яндекс.диске
    for filename in cloud_names:
        y.remove(f"{cloud_path}/{filename}")
        results["deleted"]["count"] += 1
        results["deleted"]["names"].append(filename)
    return results


if __name__ == "__main__":
    pprint(scan_and_synchronize(DIRECTORY_PATH, CLOUD_DIRECTORY))
