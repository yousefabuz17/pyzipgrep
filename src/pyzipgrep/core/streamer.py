from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential
)

from .reader import ArchiveReader
from ..utils.common import (
    DEFAULT_CHUNK_SIZE,
    bytes_to_str,
    validate_chunk_size
)



class ArchiveStreamer(ArchiveReader):
    def __init__(self, archive_file, max_workers=None):
        super().__init__(archive_file)
        self._max_workers = max_workers or 8

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def stream_file_from_archive(
        self,
        inner_file,
        text=True,
        chunk_size=DEFAULT_CHUNK_SIZE
    ):
        """Yield chunks from a single file inside this archive."""
        chunk_size = validate_chunk_size(chunk_size)
        
        with self.open_file_path(inner_file) as f:
            while (chunk := f.read(chunk_size)):
                yield bytes_to_str(chunk) if text else chunk

    def iter_files_from_archive(self):
        """Yield all file names inside this archive."""
        yield from self.namelist()

    def find_file_within_archive(self, file_predicate=None):
        """Yield file names inside this archive matching predicate."""
        for inner_file in self.iter_files_from_archive():
            if file_predicate and not file_predicate(inner_file):
                continue
            yield inner_file

    @property
    def archive_file(self):
        return self._archive_file