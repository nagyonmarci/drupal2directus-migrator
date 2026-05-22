import logging
import os
from logging.handlers import RotatingFileHandler

_LOG_DIR = "logs"
_LOG_FILE = os.path.join(_LOG_DIR, "migration.log")
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_BACKUP_COUNT = 5

_initialized = False


def get_logger(name: str) -> logging.Logger:
    global _initialized
    if not _initialized:
        os.makedirs(_LOG_DIR, exist_ok=True)
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)

        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

        fh = RotatingFileHandler(_LOG_FILE, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)

        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(fmt)

        root.addHandler(fh)
        root.addHandler(ch)
        _initialized = True

    return logging.getLogger(name)
