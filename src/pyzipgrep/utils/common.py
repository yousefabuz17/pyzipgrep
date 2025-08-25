from os import PathLike as _PathLike
from itertools import tee
from typing import Union


DEFAULT_CHUNK_SIZE = 1024   # 1KB


PathLike = Union[str, _PathLike]


def get_logger():
    import logging
    
    root_logger = logging.getLogger()
    
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    level = logging.INFO

    formatter = logging.Formatter(
        fmt="[%(asctime)s]--%(message)s",
        datefmt="%Y-%m-%dT%I:%M:%S%p",
    )
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    
    return root_logger


logger = get_logger()



def bytes_to_str(obj):
    if isinstance(obj, bytes):
        obj = obj.decode("utf-8", errors="ignore")
    return obj



def unpack_error(e):
    return str(e.args[0] if e.args else e)


def has_attribute(obj, attr, check_value=True):
    items = (obj, attr)
    has_attr = hasattr(*items)
    if check_value:
        return all((has_attr, getattr(*items, None)))
    return has_attr


def type_name(obj) -> str:
    if not isinstance(obj, type):
        obj = type(obj)

    def _gattr(n):
        return getattr(obj, n, None)

    return _gattr("__name__") or _gattr("__qualname__") or repr(obj)


def is_pathlike(fp):
    return isinstance(fp, PathLike)



def calculate_days_since_created(time_created):
    from datetime import datetime
    
    if is_float(time_created):
        time_created = datetime.fromtimestamp(time_created)
    return (datetime.now() - time_created).days


def get_posix_name(fp):
    if is_pathlike(fp) and hasattr(fp, "name"):
        fp = fp.name
    return fp


def log_exception(msg, error):
    error = unpack_error(error)
    logger.exception(f"{msg}\nError: {error}")


def validate_chunk_size(chunk_size=None):
    if chunk_size is None:
        return
    
    if not is_numeric(chunk_size):
        chunk_size = DEFAULT_CHUNK_SIZE
    return chunk_size


def is_int(obj):
    return isinstance(obj, int)


def is_float(obj):
    return isinstance(obj, float)


def is_numeric(obj):
    return any((is_int(obj), is_float(obj)))


def calculate_ratio(
    compressed_size: int | float,
    uncompressed_size: int | float
    ):
    ratio = (1 - compressed_size / uncompressed_size) * 100
    return round(ratio, 2)


def make_clones(obj, n=2, as_iter=True):
    obj = tee(obj, n)
    if as_iter:
        obj = iter(obj)
    return obj