from setuptools import setup
from Cython.Build import cythonize

setup(
    ext_modules=cythonize(
        [
            "src/pyzipgrep/pyzipgrep.py",
            "src/pyzipgrep/cli/cli_parser.py",
            "src/pyzipgrep/core/engine.py",
            "src/pyzipgrep/core/handler.py",
            "src/pyzipgrep/core/reader.py",
            "src/pyzipgrep/core/streamer.py",
            "src/pyzipgrep/benchmarks/run_benchmark.py",
            "src/pyzipgrep/utils/common.py",
        ],
        compiler_directives={
            "language_level": "3",
            "boundscheck": False,
            "wraparound": False,
            "initializedcheck": False,
            "cdivision": True,
        },
    ),
)
