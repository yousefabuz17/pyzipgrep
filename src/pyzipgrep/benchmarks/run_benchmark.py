import asyncio
import subprocess
import sys
import time
from pathlib import Path

from pyzipgrep import pyzipgrep
from pyzipgrep.core.models import Benchmarks, ColorizeMatch
from pyzipgrep.filters.content_filters import ContentRegexFilter
from pyzipgrep.utils.common import PathLike, get_logger



logger = get_logger()
ZIPGREP = "zipgrep"
UGREP = "ugrep"
PYZIPGREP = "py" + ZIPGREP
DEFAULT_TOTAL_RUNS = 1


if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys.argv[0]).resolve().parent
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]



async def benchmark_pyzipgrep(archive_file: PathLike, pattern: str, num_runs: int) -> Benchmarks:
    timings = []
    
    async def time_process():
        start = time.perf_counter()
        async with pyzipgrep(archive_file, verbose=False, allow_hidden_paths=True) as pzgrep:
            async for _ in pzgrep.zipgrep_like(
                # content_predicate=ContentRegexFilter(pattern),
            ):
                pass
        return time.perf_counter() - start
    
    # Warmup (Cold-start)
    timings.append(await time_process())
    
    for _ in range(num_runs):
        timings.append(await time_process())
    
    return Benchmarks(PYZIPGREP, timings)


def benchmark_modules(module: str, archive_file: PathLike, pattern: str, num_runs: int) -> Benchmarks:
    timings = []
    cmd = [module, pattern, archive_file]
    
    if module == UGREP:
        cmd.insert(1, "-z")
    
    def time_process():
        start = time.perf_counter()
        subprocess.run(cmd, capture_output=True)
        return time.perf_counter() - start
    
    # Warmup (Cold-start)
    timings.append(time_process())
    
    for _ in range(num_runs):
        timings.append(time_process())
    
    return Benchmarks(module, timings)


def benchmark_zipgrep(archive_file: PathLike, pattern: str, num_runs: int) -> Benchmarks:
    return benchmark_modules(ZIPGREP, archive_file, pattern, num_runs)


def benchmark_ugrep(archive_file: PathLike, pattern: str, num_runs: int) -> Benchmarks:
    return benchmark_modules(UGREP, archive_file, pattern, num_runs)


async def run_benchmarks(num_runs=DEFAULT_TOTAL_RUNS):
    # test_archive_file = Path(__file__).parent / "test_files/good.zip"
    test_archive_file = PROJECT_ROOT / "tests/test_files/full_dir.zip"
    pattern = r" "
    
    logger.info(f"\nBenchmark started [RUNS={num_runs}]")
    
    benchmark_args = (test_archive_file, pattern, num_runs)
    
    # Benchmark pyzipgrep
    pyz_benchmarks: Benchmarks = await benchmark_pyzipgrep(*benchmark_args)
    
    # Benchmark zipgrep
    # zipgrep_benchmarks: Benchmarks = benchmark_zipgrep(*benchmark_args)
    zipgrep_benchmarks: Benchmarks = Benchmarks.dummy_benchmark(ZIPGREP)
    
    # Benchmark ugrep
    ugrep_benchmarks: Benchmarks = benchmark_ugrep(*benchmark_args)
    
    # Calculate Performance Index
    def calculate_performance_index(target: Benchmarks):
        fastest_mean = min(pyz_benchmarks.mean, target.mean)
        performance_index_pyz = fastest_mean / pyz_benchmarks
        performance_index_target = fastest_mean / target
        pyz_benchmarks.performance_index = performance_index_pyz
        return performance_index_target
    
    # Calculate speedup
    def calculate_speed(target: Benchmarks):
        if pyz_benchmarks.is_faster(target):
            label = "faster"
            color = "green"
            speed_up = target / pyz_benchmarks
        else:
            label = "slower"
            color = "red"
            speed_up = pyz_benchmarks / target
        
        speed_up_str = "{:.2f}x {}".format(speed_up, label.upper())
        return ColorizeMatch.colorize_text(speed_up_str, color=color)
    
    zipgrep_benchmarks.performance_index = calculate_performance_index(zipgrep_benchmarks)
    ugrep_benchmarks.performance_index = calculate_performance_index(ugrep_benchmarks)
    
    py_speedup_zip = calculate_speed(zipgrep_benchmarks)
    py_speedup_ugrep = calculate_speed(ugrep_benchmarks)
    
    # Verbose Results
    all_benchmarks = (pyz_benchmarks, zipgrep_benchmarks, ugrep_benchmarks)
    logger.info("".join(map(repr, all_benchmarks)))
    logger.info(
        f"{PYZIPGREP} is {py_speedup_zip} than {ZIPGREP}"
        f"\n{PYZIPGREP} is {py_speedup_ugrep} than {UGREP}"
    )


if __name__ == "__main__":
    asyncio.run(run_benchmarks())