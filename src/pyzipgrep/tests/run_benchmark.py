import asyncio
import time
import statistics
import subprocess
import re
from pathlib import Path
from typing import List

from pyzipgrep import pyzipgrep
from pyzipgrep.utils.common import get_logger, quiet_logger



logger = get_logger()



def run_process(cmd):
    return subprocess.run(cmd, capture_output=True, check=True)

def to_ms(number):
    return number * 1000



async def benchmark_pyzipgrep(archive_file: str, pattern: str, num_runs: int) -> List[float]:
    """Benchmark pyzipgrep implementation."""
    regex = re.compile(pattern)
    timings = []
    
    async def run_search():
        async with pyzipgrep([archive_file]) as pzgrep:
            async for _ in pzgrep.zipgrep_like(
                content_predicate=lambda x: bool(regex.search(x))
            ):
                pass
    
    # Warmup
    await run_search()
    
    for _ in range(num_runs):
        start = time.perf_counter()
        await run_search()
        end = time.perf_counter()
        timings.append(end - start)
    
    return timings


def benchmark_zipgrep(archive_file: str, pattern: str, num_runs: int) -> List[float]:
    """Benchmark zipgrep implementation."""
    timings = []
    
    # Warmup
    cmd = ["zipgrep", pattern, archive_file]
    run_process(cmd)
    
    for _ in range(num_runs):
        start = time.perf_counter()
        run_process(cmd)
        end = time.perf_counter()
        timings.append(end - start)
    
    return timings



def log_results(name: str, timings: List[float]):
    """Print formatted results."""
    mean = to_ms(statistics.mean(timings))
    stdev = to_ms(statistics.stdev(timings)) if len(timings) > 1 else 0
    min_timings = to_ms(min(timings))
    max_timings = to_ms(max(timings))
    duration = to_ms(timings[0])
    
    logger.info(
        f"""
{name.upper()}:
  ~~> Mean: {mean:.2f} ms
  ~~> Std:  {stdev:.2f} ms
  ~~> Min:  {min_timings:.2f} ms
  ~~> Max:  {max_timings:.2f} ms
  ~~> Cold Start:  {duration:.2f} ms
""")


async def run_benchmark(num_runs=10):
    test_archive_file = Path(__file__).parent / "test_files/good.zip"
    pattern = " "
    
    logger.info(f"\nBenchmark started [RUNS={num_runs}]")
    
    # Benchmark pyzipgrep
    py_times = await benchmark_pyzipgrep(test_archive_file, pattern, num_runs)
    
    # Benchmark zipgrep
    zip_times = benchmark_zipgrep(test_archive_file, pattern, num_runs)
    
    # Verbose Results
    log_results("pyzipgrep", py_times)
    log_results("zipgrep", zip_times)
    
    # Calculate speedup
    py_mean = statistics.mean(py_times)
    zip_mean = statistics.mean(zip_times)
    py_speedup = zip_mean / py_mean
    zip_speedup = py_mean / zip_mean
    speed_str = "slower" if py_speedup <= zip_speedup else "faster"
    
    logger.info(f"pyzipgrep is {py_speedup:.2f}x {speed_str} than zipgrep")


if __name__ == "__main__":
    asyncio.run(run_benchmark())