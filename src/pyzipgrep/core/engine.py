import asyncio
from collections import deque
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed
)


from .models import ArchiveMatch
from .streamer import ArchiveStreamer
from ..utils.common import (
    DEFAULT_CHUNK_SIZE,
    get_logger,
    get_posix_name,
    is_pathlike,
    make_clones,
    unpack_error,
    validate_chunk_size,
    validate_predicate,
)
from ..utils.exceptions import NoValidArchivesException



logger = get_logger()



class ArchiveEngine:
    def __init__(self, glob_zips, max_workers=None):
        if is_pathlike(glob_zips):
            glob_zips = [glob_zips]
        else:
            glob_zips = next(make_clones(glob_zips))

        self._archives = [ArchiveStreamer(p) for p in glob_zips]
        self._max_workers = max_workers or 32
        self.__bad_archives = set()
        self.__good_archives = set()
        self.__len_bad_archives = None
        self.__len_good_archives = None
    
    def __check_archives(self):
        deque(
            (
                self.__bad_archives.add(archive)
                if not archive.is_valid_zipfile()
                else self.__good_archives.add(archive)
                for archive in self._archives
            ),
            maxlen=0
        )
        
        self.__len_bad_archives = len(self.__bad_archives)
        self.__len_good_archives = len(self.__good_archives)
        
        if self.__len_bad_archives > 0:
            bad_archives = [archive.archive_file.as_posix() for archive in self.__bad_archives]
            logger.warning(
                "The following archives were skipped because they were invalid or corrupted:"
                f"\n{', '.join(bad_archives)!r}"
            )
        
        if self.__len_good_archives == 0:
            raise NoValidArchivesException(
                "No valid archives were found in the given path(s)."
            )

    def iter_through_archives(self, archive_predicate=None, file_predicate=None):
        """Yield (archive, inner_file) pairs across all archives in parallel."""
        
        self.__check_archives()
        validate_predicate(archive_predicate, "Archive Predicate")
        validate_predicate(file_predicate, "File Predicate")
        
        max_workers = min(self._max_workers, self.__len_good_archives)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    list, archive.find_file_within_archive(file_predicate)
                ): archive
                for archive in self.__good_archives
            }
            
            for future in as_completed(futures):
                archive = futures[future]
                try:
                    namelist = future.result()
                    for inner_file in namelist:
                        if archive_predicate and not archive_predicate(archive):
                            continue
                        yield archive, inner_file
                except Exception as e:
                    error = unpack_error(e)
                    logger.exception(
                        f"An error occured for archive {get_posix_name(archive)!r}",
                        f"\nError: {error}"
                    )
                    continue

    def find_file_from_archives(
        self,
        archive_predicate=None,
        file_predicate=None
    ):
        """Yield (archive, inner_file) pairs for matching files."""
        yield from self.iter_through_archives(
            archive_predicate=archive_predicate,
            file_predicate=file_predicate
        )

    async def find_file_contents(
        self,
        chunk_predicate,
        archive_predicate=None,
        file_predicate=None,
        text=True,
        chunk_size=DEFAULT_CHUNK_SIZE,
        lines_before=None,
        lines_after=None
    ):
        """Yield ArchiveMatch objects when predicate matches."""
        chunk_size = validate_chunk_size(chunk_size)
        print(chunk_size)
        validate_predicate(chunk_predicate, "Chunk Predicate")
        
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            for archive, inner_file in self.find_file_from_archives(
                archive_predicate, file_predicate
            ):
                archive_file = archive.archive_file
                loop = asyncio.get_running_loop()
                
                func = lambda: list(
                    archive.stream_file_from_archive(
                    inner_file, text=text, chunk_size=chunk_size
                    ))
                
                inner_file_contents = await loop.run_in_executor(executor, func)
                
                if not inner_file_contents:
                    logger.critical(f"No valid files were found inside the archive {archive_file!r}.")
                    continue
                
                if inner_file.endswith(".zip"):
                    if not ArchiveStreamer.is_zipfile(inner_file):
                        logger.warning(
                            f"An archive within archive {archive_file!r} is considered invalid or corrupt and will be skipped. "
                            f"Bad archive: {inner_file!r}."
                        )
                        continue
                    else:
                        # TODO: Recurse into archive files within archive files? 🤔
                        # Instead of skipping it?
                        continue
                
                for inner_file_content in inner_file_contents:
                    if chunk_size is None:
                        for idx, c in enumerate(inner_file_content.splitlines(), start=1):
                            if chunk_predicate(c):
                                yield ArchiveMatch(
                                    archive_file,
                                    inner_file,
                                    idx,
                                    c,
                                )
                                # TODO: break for first match?
                                # Let user decide on count?
                                # break
                            # else:
                            #     preserved_idx += idx + 1
                    else:
                        # TODO: Preserve line numbers for chunks !!!!
                        if chunk_predicate(inner_file_content):
                            # yields the whole contents for now.
                            # TODO: Do what with it? Nothing?
                            # Highlight all the areas where a match is found?
                            #   - Not all predicates will involve matching,
                            #       could be based on len() as well.
                            yield ArchiveMatch(
                                archive.archive_file, inner_file, None, inner_file_content
                            )

    async def zipgrep_like(self, *args, **kwargs):
        # kwargs["chunk_size"] = kwargs.get("chunk_size", DEFAULT_CHUNK_SIZE)
        # kwargs["chunk_size"] = DEFAULT_CHUNK_SIZE
        async for archive_match in self.find_file_contents(*args, **kwargs):
            yield archive_match.__str__()



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