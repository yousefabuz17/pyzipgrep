import asyncio
from argparse import (
    ArgumentParser,
    ArgumentDefaultsHelpFormatter,
    RawTextHelpFormatter
)

from ..core.models import ArchiveMatch, ColorizeMatch
from ..filters.content_filters import ContentRegexFilter, ContentStringFilter
from ..filters.file_filters import FileNameFilter, FileExtensionFilter
from ..utils.common import get_logger, terminate
from ..pyzipgrep import pyzipgrep


logger = get_logger()


async def zipgrep_like(args):
    matches = 0
    return_code = 0
    
    # Content Predicate
    content_predicate = None
    if (pattern := args.pattern):
        case_sensitive = not args.ignore_case
        content_predicate_args = (pattern, case_sensitive)
        if args.string:
            content_predicate = ContentStringFilter(*content_predicate_args)
        else:
            content_predicate = ContentRegexFilter(*content_predicate_args)
    # ───────────────────────────────────────────────────────────────────────────
    
    
    
    
    # File Predicate
    file_predicate = None
    # if (extensions := args.extensions):
    #     pass
    # ───────────────────────────────────────────────────────────────────────────
    
    archives, max_workers, verbose = args.archives, args.max_workers, not args.quiet
    zipgrep_like_kwargs = {
        "chunk_size": args.chunk_size,
        "recursive": args.recursive,
        "content_predicate": content_predicate,
        "format_spec": args.format_spec,
        "color": args.color,
        "color_mode": args.color_mode,
        "scheme": args.scheme,
        
    }
    
    try:
        async with pyzipgrep(archives, max_workers, verbose) as pzgrep:
            async for match in pzgrep.zipgrep_like(**zipgrep_like_kwargs):
                logger.info(match)
    except Exception as e:
        return_code = 1
        if verbose:
            logger.exception(e, stack_info=True)
    
    if return_code == matches == 0:
        # If no matches were found
        # return code will be set to `2`
        return_code = 2
    
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
    # ───────────────────────────────────────────────
    
    arg_parser.add_argument(
        "-b", "--run-benchmark",
        type=int,
        help=""
    )
    arg_parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help=""
    )
    arg_parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help=""
    )
    arg_parser.add_argument(
        "-i", "--ignore-case",
        action="store_true",
        help=""
    )
    arg_parser.add_argument(
        "-l", "--list-only",
        action="store_true",
        help=""
    )
    arg_parser.add_argument(
        "--info-list-only",
        action="store_true",
        help=""
    )
    arg_parser.add_argument(
        "--string",
        action="store_true",
        help=""
    )
    
    arg_parser.add_argument(
        "-w", "--max-workers",
        type=int,
        help="",
    )
    arg_parser.add_argument(
        "--chunk-size",
        type=int,
        help="",
    )
    
    # ─────────────── ColorizeMatch Args ───────────────
    arg_parser.add_argument(
        "--color",
        choices=ColorizeMatch.available_colors(colors_only=True),
        help="",    # Mention its colors from 30-37 for ANSI
    )
    
    arg_parser.add_argument(
        "--color-mode",
        choices=ColorizeMatch.COLOR_MODES,
        help="",
    )
    
    arg_parser.add_argument(
        "--scheme",
        choices=ColorizeMatch.SCHEMES,
        help="",
    )
    arg_parser.add_argument(
        "--format-spec",
        choices=ArchiveMatch.FORMAT_SPEC_CHOICES,
        help="",
    )
    
    arg_parser.add_argument(
        "pattern",
        help="",
    )
    
    arg_parser.add_argument(
        "archives",
        nargs="+",
        help="",
    )
    
    args = arg_parser.parse_args()
    
    if args.run_benchmark:
        from ..tests.run_benchmark import run_benchmark
        asyncio.run(run_benchmark(num_runs=args.run_benchmark))
        terminate()
    
    archives = args.archives
    
    if any((
        (list_only := args.list_only),
        args.info_list_only
    )):
        [
            list_archive_files(a, list_files=list_only)
            for a in archives
        ]
        terminate()
    
    asyncio.run(zipgrep_like(args))