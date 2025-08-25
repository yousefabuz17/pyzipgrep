import asyncio
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed
)

from .core.engine import ArchiveEngine
from .utils.common import (
    get_logger,
    )



# TODO: Class of functions for predicate filtering methods
#   - filter by metadata like (size >= 1MB)
#   - file creation time >= <num>
#   - support for zip and tar files @due
#   - support for multiple filters


logger = get_logger()




class pyzipgrep(ArchiveEngine):
    def __init__(self, glob_zips, max_workers=None):
        super().__init__(glob_zips, max_workers)





class ChunkController:
    def __init__(
        self,
        chunk,
        chunk_predicate=None,
        lines_before=None,
        lines_after=None
        ):
        self._chunk = chunk
        self._chunk_predicate = chunk_predicate
        self._lines_before = lines_before
        self._lines_after = lines_after