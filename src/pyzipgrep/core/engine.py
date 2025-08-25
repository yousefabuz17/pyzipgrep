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
    is_pathlike,
    log_exception,
    make_clones,
    validate_chunk_size
    )




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
        
        if self.__len_good_archives == 0:
            raise Exception("")

    def iter_through_archives(self, archive_predicate=None, file_predicate=None):
        """Yield (archive, inner_file) pairs across all archives in parallel."""
        
        self.__check_archives()
        
        max_workers = min(self._max_workers, self.__len_good_archives)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    list, archive.find_file_within_archive(file_predicate)
                ): archive
                for archive in self.__good_archives
            }
            # print(futures)
            for future in as_completed(futures):
                archive = futures[future]
                try:
                    namelist = future.result()
                    for inner_file in namelist:
                        if archive_predicate and not archive_predicate(archive):
                            continue
                        yield archive, inner_file
                except Exception as e:
                    log_exception(
                        f"Error processing {archive.archive_file.name}",
                        e
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
    ):
        """Yield ArchiveMatch objects when predicate matches."""
        chunk_size = validate_chunk_size(chunk_size)

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            for archive, inner_file in self.find_file_from_archives(
                archive_predicate, file_predicate
            ):
                loop = asyncio.get_running_loop()
                
                func = lambda: list(
                    archive.stream_file_from_archive(
                    inner_file, text=text, chunk_size=chunk_size
                    ))
                
                inner_file_contents = loop.run_in_executor(executor, func)
                
                for inner_file_content in await inner_file_contents:
                    if chunk_size is None:
                        for idx, c in enumerate(inner_file_content.splitlines(), start=1):
                            if chunk_predicate(c):
                                yield ArchiveMatch(
                                    archive.archive_file,
                                    inner_file,
                                    idx,
                                    c,
                                )
                                # break
                            # else:
                            #     preserved_idx += idx + 1
                    # else:
                    #     if chunk_predicate(inner_file_content):
                    #         # yields the whole contents for now.
                    #         # TODO: Do what with it? Nothing?
                    #         # Highlight all the areas where a match is found?
                    #         #   - Not all predicates will involve matching,
                    #         #       could be based on len() as well.
                    #         yield ArchiveMatch(
                    #             archive.archive_file, inner_file, None, inner_file_content
                    #         )

    async def zipgrep_like(self, *args, **kwargs):
        kwargs["chunk_size"] = kwargs.get("chunk_size", DEFAULT_CHUNK_SIZE)
        # kwargs["chunk_size"] = DEFAULT_CHUNK_SIZE
        async for archive_match in self.find_file_contents(*args, **kwargs):
            yield archive_match.__str__()