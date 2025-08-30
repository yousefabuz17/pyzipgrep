from .core.engine import ArchiveEngine
from .utils.common import (
    get_logger,
)




# TODO: Implement a class or module encapsulating predicate-based filtering functionality
# Core filtering features:
#   - Enable combining multiple filters simultaneously for flexible querying
#   - Support syntax highlighting of matched text within inner files
#   - Support for `xfiles`: Dont include, already is done with archive_predicate
#       - Option to exclude specific archive files
#       - inner files too? maybe based on extension only as its represented as a string not path
#       - use mimetypes.types_map for all possible extensions?
#   - Preserve line information for matches when a chunk_size parameter is provided
#   - Filter archives and inner files based on ArchiveMetadata:
#       * File size (e.g., size >= 1MB)
#       * File creation/modification timestamps (e.g., created after/before a certain date)
#       * (Follow based on ArchiveMetadata attributes below)
#   - Support multiple archive formats:
#       * ZIP files
#       * TAR files
#       * (Possibly extendable to other compressed formats in the future)
#   - Add verbose? Only stream logs if its enabled? Might as well. (Disregard)
# TODO: Implement advanced CLI filtering mechanisms based on ArchiveMetadata attributes
# CLI-specific filtering mechanisms to implement:
#   - --created-before <date>                      Filter archives created before a specific date
#   - --created-after <date>                       Filter archives created after a specific date
#   - --size-greater <size>                        Filter archives exceeding a specified size threshold
#   - --size-less <size>                           Filter archives smaller than the specified size
#   - --total-files-greater <num>                  Filter archives containing more than <num> inner files (total_files)
#   - --total-files-less <num>                     Filter archives containing fewer than <num> inner files
#   - --compressed-ratio-greater <val>             Filter archives where compression ratio exceeds <val> (ratio)
#   - --compressed-ratio-less <val>                Filter archives where compression ratio is below <val>
#   - --total-compressed-greater <val>.            Filter based on total compressed size of archive (total_compressed)
#   - --total-compressed-less <val>                Filter based on total compressed size below <val>
#   - --total-uncompressed-greater <val>           Filter based on total uncompressed size (total_uncompressed)
#   - --total-uncompressed-less <val>              Filter based on total uncompressed size below <val>
#   - --days-since-created-greater <num>           Filter archives created more than <num> days ago (days_since_created)
#   - --days-since-created-less <num>              Filter archives created less than <num> days ago
#   - --days-since-modified-greater <num>          Filter archives modified more than <num> days ago (days_since_modified)
#   - --days-since-modified-less <num>             Filter archives modified less than <num> days ago
#   -   **      Allow custom user-defined filtering functions for advanced use cases    **
#
# Advanced / custom CLI filtering mechanisms:
#   - Allow combining multiple filters with logical AND/OR
#   - Provide support for user-defined Python filter functions
#   - Enable filtering based on regex matches within inner file contents
#   - Ensure consistent feedback when no archives match (warn instead of ignore?)
#   - Keep filters composable and reusable across synchronous and asynchronous workflows
#
# NOTE:
#   - All filters should be compatible with ArchiveMetadata attributes and handle Optional values gracefully
#   - Dates should support multiple input formats (timestamp, ISO strings, etc.)
#   - CLI filters should integrate seamlessly with programmatic APIs for batch processing
#
# TODO: Exception-Handling
#   Exceptions:
#       - If no valid archives are within the collection to search with
#           - Any invalid zip file will automatically be filtered out regardless
#       - If no valid files within an archive were found? Or just ignore??
#   ** For any other cases, it will most likely be ignored unless failed for unknown reasons





logger = get_logger()




class pyzipgrep(ArchiveEngine):
    def __init__(self, glob_zips, max_workers=None, recursive=False):
        super().__init__(glob_zips, max_workers, recursive)
    
    # TODO:
    # Once filtering mechanisms are fairly complete,
    # update content manager to accept them as a clean way for filtering
    # E.g,
    # async match in pyzipgrep.<>(
    #   run_archive_filters(predicates)         # Can be multiple predicates, based on its name, ext, metadata etc
    #   run_inner_file_filters(predicates)      # Can be based on its str representation
    #   run_file_content_filters(predicates)    # Can be based on anything like contains, length, specific text etc.
    # )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args, **kwargs):
        pass