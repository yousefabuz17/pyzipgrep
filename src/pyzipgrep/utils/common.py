import os
import logging
import re
from itertools import tee
from datetime import datetime
from typing import Union

from .exceptions import InvalidChunkSize, InvalidPredicate




DEFAULT_CHUNK_SIZE = 1024   # 1KB


PathLike = Union[str, os.PathLike]



class ClassProperty:
    def __init__(self, fget):
        self.fget = fget
    
    def __get__(self, instance, owner):
        return self.fget(owner)



def get_logger():
    root_logger = logging.getLogger()
    
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    level = logging.INFO

    formatter = logging.Formatter(
        fmt="[%(asctime)s-%(levelname)s]--%(message)s",
        datefmt="%Y-%m-%dT%I:%M:%S%p",
    )
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    
    return root_logger


def default_max_workers():
    return min(32, (os.cpu_count() or 1) + 4)


def fn_matcher(name, pat):
    from fnmatch import fnmatch, fnmatchcase
    from functools import partial
    from pathlib import Path
    from re import Pattern
    
    def _fnmatcher(n, p):
        return any((
            Path(n).match(p),
            fnmatch(n, p),
            fnmatchcase(n, p)
            ))
    
    if not isinstance(pat, (str, Pattern)):
        return any(map(partial(_fnmatcher, name), pat))
    return _fnmatcher(name, pat)



def bytes_to_str(obj):
    if isinstance(obj, bytes):
        obj = obj.decode("utf-8", errors="ignore")
    return obj


def validate_predicate(predicate, predicate_name):
    import inspect
    
    if predicate is None:
        return
    
    predicate_params = [
        k for k in inspect.signature(predicate).parameters
        if k not in ("args", "kwargs")
        ]
    len_params = len(predicate_params)
    valid_predicate = all((
        (is_callable := callable(predicate)),
        len_params == 1
    ))
    
    if not valid_predicate:
        raise InvalidPredicate(
            f"Invalid predicate {predicate_name!r}: must be callable AND accept exactly 1 argument."
            f"\nReturned {is_callable = } and {len_params = }."
        )


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


def fromtimestamp(time_created: float | datetime):
    if not is_numeric(time_created):
        return
    return datetime.fromtimestamp(time_created)


def calculate_date_since_created(time_created):
    time_created = fromtimestamp(time_created)

    if time_created is None:
        return
    
    current_age = datetime.now() - time_created
    return current_age


def calculate_days_since_created(time_created):
    time_created = calculate_date_since_created(time_created)
    if time_created:
        return time_created.days


def get_posix_name(fp):
    if is_pathlike(fp) and hasattr(fp, "name"):
        fp = fp.name
    elif has_attribute(fp, "archive_file"):
        fp = get_posix_name(fp.archive_file)
    return fp



def to_posix(fp):
    if is_pathlike(fp) and hasattr(fp, "as_posix"):
        fp = fp.as_posix()
    elif has_attribute(fp, "archive_file"):
        fp = to_posix(fp.archive_file)
    return fp



def validate_chunk_size(chunk_size=None):
    if chunk_size is None:
        return
    
    if not is_numeric(chunk_size):
        chunk_size = DEFAULT_CHUNK_SIZE
    
    if chunk_size == 0:
        raise InvalidChunkSize(
            f"Invalid chunk size: {chunk_size!r}. "
            "Chunk size must be either `None` (to read the entire file) "
            "or a positive integer. Any other chunk size of <0 will be ignored."
        )
    return chunk_size


def is_numeric(obj):
    from math import isnan
    return not isnan(obj)


def is_string(string):
    return isinstance(string, str)


def terminate(status):
    import sys
    sys.exit(status)


def calculate_ratio(
    compressed_size: int | float,
    uncompressed_size: int | float
    ):
    if not any(map(is_numeric, (compressed_size, uncompressed_size))):
        return
    
    if uncompressed_size == 0:
        return
    ratio = (1 - compressed_size / uncompressed_size) * 100
    return round(ratio, 2)


def make_clones(obj, n=2, as_iter=True):
    obj = tee(obj, n)
    if as_iter:
        obj = iter(obj)
    return obj



def compiler(pattern, case_sensitive=False):
    if not case_sensitive:
        flags = re.IGNORECASE
    else:
        flags = 0
    return re.compile(pattern, flags=flags)


def regex_escape(s):
    return re.escape(s)