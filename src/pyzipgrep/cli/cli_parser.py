import asyncio
import sys
from argparse import (
    ArgumentParser,
    ArgumentDefaultsHelpFormatter,
    RawTextHelpFormatter
)

from ..benchmarks.run_benchmark import DEFAULT_TOTAL_RUNS, run_benchmarks
from ..core.models import ArchiveMatch, ColorizeMatch
from ..filters.base import ProcessFilters
from ..filters.content_filters import ContentLengthFilter, ContentRegexFilter, ContentStringFilter
from ..filters.file_filters import FileNameFilter, FileExtensionFilter
from ..utils.common import get_logger, terminate, unpack_error
from ..utils.exceptions import (
    ErrorCodes,
    ArchiveKeyError,
    FilterException,
    InvalidChunkSize,
    InvalidPredicate,
    NoValidArchives
)
from ..pyzipgrep import pyzipgrep


logger = get_logger()


def get_content_predicate(args):
    filters = []
    content_predicate = None
    
    if (pattern := args.pattern) is not None:
        case_sensitive = not args.ignore_case
        content_predicate_args = (pattern, case_sensitive)
        
        if (char_length := args.char_length):
            filters.append(ContentLengthFilter(char_length))
        
        if args.regex:
            filters.append(ContentRegexFilter(*content_predicate_args))
        else:
            filters.append(ContentStringFilter(*content_predicate_args))
    
    if filters:
        content_predicate = ProcessFilters(filters)
    return content_predicate



def get_file_predicate(args):
    filters = []
    file_predicate = None
    case_sensitive = not args.ignore_case
    
    if any((
        extensions := args.extensions,
        exclude_extensions := args.exclude_extensions
    )):
        file_predicate = FileExtensionFilter(
            extensions,
            exclude_extensions,
            case_sensitive
        )
    
    if (file := args.file):
        filters.append(FileNameFilter(file, case_sensitive=case_sensitive))
    
    if (file_regex := args.file_regex):
        filters.append(FileNameFilter(
            file_regex,
            use_regex=True,
            case_sensitive=case_sensitive
        ))
    
    if filters:
        file_predicate = ProcessFilters(filters)
    
    return file_predicate



async def zipgrep_like(args):
    return_code = ErrorCodes.SUCCESS
    error_msg = None
    total_matches = None
    
    content_predicate = get_content_predicate(args)
    file_predicate = get_file_predicate(args)
    # ───────────────────────────────────────────────────────────────────────────
    
    archives, max_workers, verbose = (
        args.archives, args.max_workers, not args.quiet
        )
    zipgrep_like_kwargs = {
        "content_predicate": content_predicate,
        "file_predicate": file_predicate,
        "chunk_size": args.chunk_size,
        "recursive": args.recursive,
        "format_spec": args.format_spec,
        "color": args.color,
        "color_mode": args.color_mode,
        "scheme": args.scheme,
    }
    
    if len(archives) == 1:
        archives = archives[0]
        
    try:
        async with pyzipgrep(archives, max_workers, verbose) as pzgrep:
            if args.list_archives:
                logger.info(pzgrep.archives)
                terminate(return_code)
            
            if args.list_corrupted_archives:
                logger.info(pzgrep.corrupted_archives)
                terminate(return_code)
            
            async for match in pzgrep.zipgrep_like(**zipgrep_like_kwargs):
                logger.info(match)
            
            total_matches = pzgrep.total_matches
            
    except ArchiveKeyError as ke:
        error_msg = ke
        return_code = ErrorCodes.NO_ARCHIVES_ERROR
    except FilterException as fe:
        error_msg = fe
        return_code = ErrorCodes.FILTER_ERROR
    except InvalidChunkSize as cs:
        error_msg = cs
        return_code = ErrorCodes.CHUNK_SIZE_ERROR
    except InvalidPredicate as ip:
        error_msg = ip
        return_code = ErrorCodes.PREDICATE_ERROR
    except NoValidArchives as va:
        error_msg = va
        return_code = ErrorCodes.NO_ARCHIVES_ERROR
    except Exception as e:
        error_msg = e
        return_code = ErrorCodes.EXCEPTION
    
    if error_msg is not None:
        assert return_code != ErrorCodes.SUCCESS
        
        if verbose:
            logger.error(unpack_error(error_msg))
    
    if return_code == total_matches == ErrorCodes.SUCCESS:
        return_code = ErrorCodes.NO_MATCHES
    
    terminate(return_code)



def list_archive_files(archive, list_files=True):
    streamer = pyzipgrep.archive_streamer(archive)
    
    if not list_files:
        archives_namelist = streamer.infolist()
    else:
        archives_namelist = streamer.iter_files_from_archive()
    
    logger.info(tuple(archives_namelist))




def cli_parser():
    # ─────────────── Main ArgParser ───────────────
    formatter_class = type(
        "CliFormatter",
        (RawTextHelpFormatter, ArgumentDefaultsHelpFormatter),
        {}
    )
    arg_parser = ArgumentParser(
        description="",
        formatter_class=formatter_class
    )
    subparsers = arg_parser.add_subparsers(dest="command")
    # ───────────────────────────────────────────────
    
    
    
    # ─────────────── Benchmarks ────────────────────
    benchmark_parser = subparsers.add_parser("run_benchmarks")
    benchmark_parser.add_argument(
        "-n", "--number-runs",
        type=int,
        default=DEFAULT_TOTAL_RUNS,
        help=""
    )
    
    
    
    # ─────────────── Search Args (root parser, no subcommand) ───────────────
    search_parser = subparsers.add_parser("search", aliases=(s_aliases := ("query", "find")))
    search_parser.add_argument("-q", "--quiet", action="store_true", help="Suppress all warning/raised exceptions.")
    search_parser.add_argument("-r", "--recursive", action="store_true", help="Allow recursion for nested archives.")
    search_parser.add_argument("-i", "--ignore-case", action="store_true", help="Ignore case sensitive.")
    search_parser.add_argument("-l", "--list-only", action="store_true", help="List all files within the given archive(s).")
    search_parser.add_argument("--info-list-only", action="store_true", help="")
    search_parser.add_argument("--list-archives", action="store_true", help="")
    search_parser.add_argument("--list-corrupted-archives", action="store_true", help="")
    
    # ─────────────── Content Predicate Filtering Arg ─────────────────────────
    search_parser.add_argument("--regex", action="store_true", help="")
    
    
    # ─────────────── File Predicate Filtering Args ─────────────────────────
    search_parser.add_argument("--extensions", nargs="*", help="")
    search_parser.add_argument("--exclude-extensions", nargs="*", help="")
    search_parser.add_argument("--file", nargs="*", help="")
    search_parser.add_argument("--file-regex", nargs="?", help="")
    
    
    # ─────────────── Other Args ───────────────────────
    search_parser.add_argument("-n", "--max-workers", type=int, help="")
    search_parser.add_argument("--chunk-size", type=int, help="")
    search_parser.add_argument("--char-length", help="")
    
    # ─────────────── ColorizeMatch Args ───────────────
    search_parser.add_argument(
        "--color",
        choices=ColorizeMatch.available_colors(colors_only=True),
        help="Colors from 30–37 for ANSI"
    )
    search_parser.add_argument("--color-mode", choices=ColorizeMatch.COLOR_MODES, help="")
    search_parser.add_argument("--scheme", choices=ColorizeMatch.SCHEMES, help="")
    search_parser.add_argument(
        "--format-spec",
        choices=ArchiveMatch.FORMAT_SPEC_CHOICES,
        help=""
    )
    
    # ─────────────── Positionals for search mode ───────────────
    search_parser.add_argument("pattern", nargs="?", help="")
    search_parser.add_argument("archives", nargs="*", help="")
    sys_args = sys.argv[1:]
    
    if not sys_args:
        logger.error("A pattern and an iterable of archives is required.")
        terminate(ErrorCodes.EXCEPTION)
    
    command = sys_args[0]
    
    search_args = None
    if command != "run_benchmarks":
        # This is a normal search without subcommand
        # Reconstruct arguments as if they were passed to search subcommand
        if command in (*s_aliases, "search"):
            sys_args = sys_args[1:]
        search_args = ['query', *sys_args]
    
    args = arg_parser.parse_args(search_args)
    
    if args.command == "run_benchmarks":
        asyncio.run(run_benchmarks(num_runs=args.number_runs))
        terminate()
    
    archives = args.archives
    
    if any((
        list_only := args.list_only,
        args.info_list_only
    )):
        [
            list_archive_files(a, list_files=list_only)
            for a in archives
        ]
        terminate()
    
    asyncio.run(zipgrep_like(args))