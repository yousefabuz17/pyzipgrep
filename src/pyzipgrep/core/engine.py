import asyncio
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed


from ..utils.common import (
    DEFAULT_CHUNK_SIZE,
    ClassProperty,
    default_max_workers,
    get_logger,
    get_posix_name,
    is_pathlike,
    make_clones,
    terminate,
    unpack_error,
    validate_chunk_size,
    validate_predicate,
)
from .models import ArchiveMatch
from .streamer import ArchiveStreamer

logger = get_logger()




class ArchiveEngine:
    NESTED_COUNT = 0
    
    def __init__(self, archives, max_workers=None, recursive=False):
        self._archives = archives
        self._max_workers = max_workers or default_max_workers()
        self._recursive = recursive
        self.__bad_archives = set()
        self.__good_archives = set()
        self.__skipped_archives = set()
        self.__len_bad_archives = None
        self.__len_good_archives = None
    
    def __check_archives(self, archive_predicate=None):
        validate_predicate(archive_predicate, "Archive Predicate")
        archives = self._archives
        
        if is_pathlike(archives):
            archives = [archives]
        else:
            archives = next(make_clones(archives))
        
        for archive in archives:
            if not ArchiveStreamer.is_zipfile(archive):
                self.__bad_archives.add(archive)
                continue
            
            s_archive = ArchiveStreamer(archive)
            
            if archive_predicate and not archive_predicate(s_archive):
                continue
            
            self.__good_archives.add(s_archive)
        
        self.__len_bad_archives = len(self.__bad_archives)
        self.__len_good_archives = len(self.__good_archives)
        
        if self.__len_bad_archives > 0:
            logger.warning(
                "The following archives were skipped because they were invalid or corrupted: "
                f"{self.__bad_archives}"
            )
        
        if self.__len_good_archives == 0:
            if archive_predicate:
                msg = "No archives satisfied the specified criteria."
            else:
                msg = "No archives were detected in the provided path(s)."
            
            logger.error(msg)
            terminate(1)

    def iter_through_archives(self, archive_predicate=None, file_predicate=None):
        """Yield (archive, inner_file) pairs across all archives in parallel."""
        
        self.__check_archives(archive_predicate)
        validate_predicate(file_predicate, "File Predicate")
        
        max_workers = min(self._max_workers, self.__len_good_archives)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    list, archive.find_file_within_archive()
                ): archive
                for archive in self.__good_archives
            }
            
            for future in as_completed(futures):
                archive: ArchiveStreamer = futures[future]
                
                try:
                    namelist = future.result()
                    for inner_file in namelist:
                        if file_predicate and not file_predicate(inner_file):
                            continue
                        yield archive, inner_file
                except Exception as e:
                    error = unpack_error(e)
                    logger.error(
                        f"An error occured for archive {get_posix_name(archive)!r}",
                        f"\nError: {error}",
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
        chunk_size=None,
        lines_before=None,
        lines_after=None
    ):
        """Yield ArchiveMatch objects when predicate matches."""
        chunk_size = validate_chunk_size(chunk_size)
        validate_predicate(chunk_predicate, "Chunk Predicate")
        
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            for archive, inner_file in self.find_file_from_archives(
                archive_predicate, file_predicate
            ):
                
                archive_file = archive.archive_file
                
                if inner_file.endswith(".zip"):
                    if not ArchiveStreamer.is_zipfile(inner_file):
                        logger.warning(
                            f"Invalid nested archive detected: {inner_file!r} in parent archive {archive_file!r}. "
                            f"This embedded file will be skipped due to corruption or invalid format."
                        )
                        continue
                    else:
                        # NOTE: Recursing nested archives seems to be working perfectly
                        # TODO:
                        #   - (IMPORTANT) Must try with large archives for testing !!!!
                        #   - Add an arg to set whether to decide to parse nested archives?
                        #   - Add recursive jump count for limitations?
                        nested_archive = ArchiveEngine(inner_file)
                        nested_archive_contents = nested_archive.find_file_contents(
                                                        chunk_predicate,
                                                        archive_predicate=archive_predicate,
                                                        file_predicate=file_predicate,
                                                        chunk_size=chunk_size
                                                        )
                        
                        async for _ in nested_archive_contents:
                            yield _
                            await asyncio.sleep(0)
                        
                        ArchiveEngine.NESTED_COUNT += 1
                        continue
                
                loop = asyncio.get_running_loop()
                
                def _fetch_file_contents(archive=archive, inner_file=inner_file):
                    return archive.stream_file_from_archive(
                        inner_file, chunk_size=chunk_size
                        )
                
                inner_file_contents = await loop.run_in_executor(executor, _fetch_file_contents)
                
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
                                archive_file, inner_file, None, inner_file_content
                            )

    async def zipgrep_like(self, *args, **kwargs):
        # kwargs["chunk_size"] = kwargs.get("chunk_size", DEFAULT_CHUNK_SIZE)
        # kwargs["chunk_size"] = DEFAULT_CHUNK_SIZE
        async for archive_match in self.find_file_contents(*args, **kwargs):
            # TODO: Use __format__(*...) instead
            yield archive_match.__str__()
    
    @ClassProperty
    def nested_count(cls):
        return cls.NESTED_COUNT



# TODO: Implement a class to retrieve the lines before/after a matched text

# class ChunkController:
#     def __init__(
#         self,
#         chunk,
#         chunk_predicate=None,
#         lines_before=None,
#         lines_after=None
#         ):
#         self._chunk = chunk
#         self._chunk_predicate = chunk_predicate
#         self._lines_before = lines_before
#         self._lines_after = lines_after