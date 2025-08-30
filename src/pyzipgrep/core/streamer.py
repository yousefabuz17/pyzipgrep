from tenacity import retry, stop_after_attempt, wait_exponential

from ..utils.common import bytes_to_str, validate_chunk_size
from .reader import ArchiveReader


class ArchiveStreamer(ArchiveReader):
    def __init__(self, archive_file):
        super().__init__(archive_file)

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def stream_file_from_archive(
        self,
        inner_file,
        chunk_size=None
    ):
        """Yield chunks from a single file inside this archive."""
        chunk_size = validate_chunk_size(chunk_size)
        
        with self.open_file_path(inner_file) as f:
            while (chunk := f.read(chunk_size)):
                yield bytes_to_str(chunk)

    def iter_files_from_archive(self):
        """Yield all file names inside this archive."""
        yield from self.namelist()

    def find_file_within_archive(self):
        """Yield file names inside this archive matching predicate."""
        yield from self.iter_files_from_archive()