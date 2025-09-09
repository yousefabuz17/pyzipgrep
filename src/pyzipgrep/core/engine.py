import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from glob import glob


from ..utils.common import (
    default_max_workers,
    get_logger,
    quiet_logger,
    get_posix_name,
    is_exhaustible,
    is_pathlike,
    to_posix,
    make_clones,
    unpack_error,
    validate_chunk_size,
    validate_predicate,
)
from ..utils.exceptions import ErrorCodes
from .handler import ContentController
from .streamer import ArchiveStreamer




class ArchiveEngine:
    NESTED_COUNT = 0
    TOTAL_MATCHES = 0
    
    def __init__(self, archives, max_workers=None, verbose=True, allow_hidden_paths=False):
        self.__logger = quiet_logger() if not verbose else get_logger()
        
        self._archives = archives
        self._max_workers = max_workers or default_max_workers()
        self._allow_hidden_paths = allow_hidden_paths
        self.__bad_archives = None
        self.__good_archives = None
        self.__len_bad_archives = None
        self.__len_good_archives = None
    
    def __check_archives(self, archive_predicate=None):
        def convert_archives():
            archives = self._archives
            if is_pathlike(archives):
                archives = to_posix(archives)
                if "*" in archives:
                    archives = convert_archives(glob(archives))
                else:
                    archives = [archives]
            elif is_exhaustible(archives):
                archives = next(make_clones(archives))
            return (self.archive_streamer(a) for a in archives)
        
        validate_predicate(archive_predicate, "Archive Predicate")
        archives = convert_archives()
        
        if not archives:
            raise ErrorCodes.raise_error(ErrorCodes.NO_ARCHIVES_ERROR)
        
        if self.__bad_archives is None:
            self.__bad_archives = set()
        
        if self.__good_archives is None:
            self.__good_archives = set()
        
        for archive in archives:
            archive_file = archive.archive_file
            if not archive.is_valid_zipfile():
                self.__bad_archives.add(archive_file)
                continue
            
            if archive_predicate and not archive_predicate(archive_file):
                continue
            
            self.__good_archives.add(archive)
        
        self.__len_bad_archives = len(self.__bad_archives)
        self.__len_good_archives = len(self.__good_archives)
        
        if self.__len_bad_archives > 0:
            self.__logger.warning(
                "The following archives were skipped because they were invalid, corrupted, or does not exist: "
                f"{self.__bad_archives}"
            )
        
        if self.__len_good_archives == 0:
            if archive_predicate:
                msg = "No valid archives were detected with the specified criteria(s)."
            else:
                msg = "No valid archives were detected in the provided path(s)."
            raise ErrorCodes.raise_error(ErrorCodes.NO_ARCHIVES_ERROR, msg)
    
    @staticmethod
    def archive_streamer(archive_file):
        return ArchiveStreamer(archive_file)

    def iter_through_archives(self, archive_predicate=None, file_predicate=None):
        self.__check_archives(archive_predicate)
        validate_predicate(file_predicate, "File Predicate")
        
        max_workers = min(self._max_workers, self.__len_good_archives)
        
        def is_hidden_path(path):
            return any(i.startswith(".") for i in path.split("/"))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    list, archive.iter_files_from_archive()
                ): archive
                for archive in self.__good_archives
            }
            
            for future in as_completed(futures):
                archive: ArchiveStreamer = futures[future]
                
                try:
                    namelist = future.result()
                    for inner_file in namelist:
                        if not self._allow_hidden_paths and is_hidden_path(inner_file):
                            continue
                        if file_predicate and not file_predicate(inner_file):
                            continue
                        yield archive, inner_file
                except Exception as e:
                    error = unpack_error(e)
                    self.__logger.exception(
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
        *,
        content_predicate=None,
        archive_predicate=None,
        file_predicate=None,
        chunk_size=None,
        recursive=False,
        count=None,
        context_before=None,
        context_after=None
    ):
        chunk_size = validate_chunk_size(chunk_size)
        validate_predicate(content_predicate, "Content Predicate")
        
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            for archive, inner_file in self.find_file_from_archives(
                archive_predicate, file_predicate
            ):
                
                archive_file = archive.archive_file
                
                # Nested archive files
                if inner_file.endswith(".zip"):
                    if recursive:
                        if not ArchiveStreamer.is_zipfile(inner_file):
                            self.__logger.warning(
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
                            async for nested_archive_contents in nested_archive.find_file_contents(
                                                            content_predicate=content_predicate,
                                                            archive_predicate=archive_predicate,
                                                            file_predicate=file_predicate,
                                                            recursive=recursive,
                                                            chunk_size=chunk_size
                                                            ):
                                yield nested_archive_contents
                            
                            ArchiveEngine.NESTED_COUNT += 1
                            continue
                    else:
                        # If recursive is not enabled and a nested archive file
                        # is found, skip it.
                        # Otherwise, its bytes contents will be parsed and matched unexpectedly.
                        continue
                
                loop = asyncio.get_running_loop()
                
                def _fetch_file_contents(archive=archive, inner_file=inner_file):
                    return archive.stream_file_from_archive(
                        inner_file, chunk_size=chunk_size
                        )
                
                inner_file_contents = await loop.run_in_executor(executor, _fetch_file_contents)
                contents_control = ContentController(
                    archive_file,
                    inner_file,
                    inner_file_contents,
                    content_predicate=content_predicate,
                    chunk_size=chunk_size,
                )
                
                async for content in contents_control.handle():
                    yield content

    async def zipgrep_like(self, *args, **kwargs):
        format_spec = kwargs.pop("format_spec", "str")
        color, color_mode, scheme = (kwargs.pop(k, None) for k in ("color", "color_mode", "scheme"))

        async for archive_match in self.find_file_contents(*args, **kwargs):
            ArchiveEngine.TOTAL_MATCHES += 1
            yield archive_match.__format__(
                format_spec,
                color=color,
                color_mode=color_mode,
                scheme=scheme
                )
        
        if ArchiveEngine.TOTAL_MATCHES > 0:
            self.__logger.info(f"Total matches: {ArchiveEngine.TOTAL_MATCHES}")
        
    @property
    def nested_count(self) -> int:
        return ArchiveEngine.NESTED_COUNT
    
    @property
    def total_matches(self):
        return ArchiveEngine.TOTAL_MATCHES
    
    @property
    def archives(self) -> set:
        if self.__good_archives is None:
            self.__check_archives()
        return self.__good_archives
    
    @property
    def corrupted_archives(self) -> set:
        if self.__bad_archives is None:
            self.__check_archives()
        return self.__bad_archives