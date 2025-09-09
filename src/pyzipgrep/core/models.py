import statistics
import sys
import tarfile
import zipfile
from dataclasses import (
    asdict,
    dataclass,
    field,
    is_dataclass,
)
from datetime import datetime
from typing import (
    Any,
    ClassVar,
    Literal,
    Optional
)

from ..utils.common import (
    PathLike,
    calculate_days_since_created,
    calculate_ratio,
    regex_escape,
    fromtimestamp,
    get_posix_name,
    to_posix,
)


class CoreZip:
    ZipFile: ClassVar[type[zipfile.ZipFile]] = zipfile.ZipFile
    is_zipfile: staticmethod = staticmethod(zipfile.is_zipfile)
    
    # TODO: Support for other file types? tar.bz2
    TarFile: ClassVar[type[tarfile.TarFile]] = tarfile.TarFile
    is_tarfile: ClassVar[staticmethod] = staticmethod(tarfile.is_tarfile)




class Serializable:
    is_dataclass: ClassVar[staticmethod] = staticmethod(is_dataclass)
    
    def asdict(self) -> dict[str, Any]:
        if self.is_dataclass(self):
            return asdict(self)
        return self.__dict__.copy()
    
    def astuple(self, data: dict=None) -> tuple[str, Any]:
        data = data or self.asdict()
        return tuple(data.items())
    
    def asjson(self, data: dict=None):
        import json
        data = data or self.asdict()
        return json.dumps(data, default=lambda o: str(o))




@dataclass(
    kw_only=True,
    unsafe_hash=True,
    slots=True,
    weakref_slot=True
)
class ArchiveMetadata(Serializable):
    archive_file: PathLike
    time_created: Optional[float | datetime] = None
    time_modified: Optional[float | datetime] = None
    size: Optional[int] = None
    total_files: Optional[int] = None
    total_uncompressed: Optional[int | float] = None
    total_compressed: Optional[int | float] = None
    
    ratio: int | float = field(default=None, init=False)
    time_created_dt: datetime = field(default=None, init=False, repr=False)
    time_modified_dt: datetime = field(default=None, init=False, repr=False)
    days_since_created: int = field(default=None, init=False, repr=False)
    days_since_modified: int = field(default=None, init=False, repr=False)
    
    def __post_init__(self) -> None:
        self.ratio = calculate_ratio(self.total_compressed, self.total_uncompressed)
        self.time_created_dt = fromtimestamp(self.time_created)
        self.days_since_created = calculate_days_since_created(self.time_created)
        self.time_modified_dt = fromtimestamp(self.time_modified)
        self.days_since_modified = calculate_days_since_created(self.time_modified)




@dataclass(
    unsafe_hash=True,
    slots=True,
    weakref_slot=True
)
class ColorizeMatch(Serializable):
    color: Optional[str] = None # Color will be only be shown for scheme `focus`
    color_mode: Optional[Literal["auto", "always", "never"]] = "auto"
    scheme: Optional[Literal["dark", "light", "focus"]] = None
    objects: Optional[list | tuple] = None
    
    tty_support: bool = field(default_factory=sys.stdout.isatty, init=False)
    SCHEMES: ClassVar[tuple] = ("dark", "light", "focus")
    COLOR_MODES: ClassVar[tuple] = ("auto", "always", "never")
    USE_COLORS: ClassVar[bool] = False
    STRING_FORMAT: ClassVar[str] = "{}{}:{}:{}"
    
    def __post_init__(self):
        match self.color_mode:
            case "never":
                ColorizeMatch.USE_COLORS = False
            case "always":
                ColorizeMatch.USE_COLORS = True
            case _:
                self.color_mode = "auto"
                ColorizeMatch.USE_COLORS = self.tty_support

        if ColorizeMatch.USE_COLORS and any((self.color, self.color_mode, self.scheme)):
            # NOTE: If no attributes are set
            #   - "auto" will be automatically assigned with "focus"
            #   - color usage: red
            
            if self.scheme not in ("dark", "light", "focus"):
                self.scheme = "focus"
    
    def __format__(self, format_spec=None):
        if format_spec is None:
            format_spec = self.color_mode
        
        archive, inner, line_no, matched_text = self.objects
        
        if ColorizeMatch.USE_COLORS:
            archive = self.colorize_object(f"[{archive}]", "archive")
            inner = self.colorize_object(inner, "inner")
            line_no = self.colorize_object(line_no, "line_no")
            matched_text = self.colorize_object(matched_text, "matched_text")
        
        return self.STRING_FORMAT.format(
            archive, inner,
            line_no, matched_text
        )
    
    @staticmethod
    def available_colors(colors_only=False):
        colors = {
            "black": "30m", "red": "31m",
            "green": "32m", "yellow": "33m",
            "blue": "34m", "magenta": "35m",
            "cyan": "36m", "white": "37m",
            "reset": "\033[0m"
        }
        if colors_only:
            colors = tuple(colors)
        return colors
    
    @classmethod
    def get_color(cls, color: str):
        colors = cls.available_colors()
        return colors.get(color, colors["red"])
    
    @classmethod
    def colorize_text(cls, text, color="green", bold=True):
        colors = cls.available_colors()
        color = cls.get_color(color)
        reset = colors["reset"]
        bold_ = "" if not bold else "1;"
        return f"\033[{bold_}{color}{text}{reset}"
    
    def colorize_object(self, obj, object_type):
        # TODO: Shorten this if possible?
        schemes = {
            "dark": {
                "archive": "\033[1;34m",        # bright blue
                "inner": "\033[36m",            # cyan
                "line_no": "\033[33m",          # yellow
                "matched_text": "\033[1;31m",   # bright red
            },
            "light": {
                "archive": "\033[1;35m",        # magenta
                "inner": "\033[34m",            # blue
                "line_no": "\033[90m",          # gray
                "matched_text": "\033[1;32m",   # green
            },
            "focus": {
                "archive": "",
                "inner": "",
                "line_no": "",
                "matched_text": f"\033[1;{self.get_color(self.color)}",
            },
            "": {
                "archive": "",
                "inner": "",
                "line_no": "",
                "matched_text": "",
            },
        }

        object_scheme_type = schemes.get(self.scheme, schemes[""])
        object_color = object_scheme_type[object_type]
        reset = self.get_color("reset")
        return f"{object_color}{obj}{reset}"



@dataclass(
    unsafe_hash=True,
    slots=True,
    weakref_slot=True
)
class ArchiveMatch(Serializable):
    archive: PathLike
    
    # Path of the file inside the archive where the match occurred.
    # Always stored as a string (not PathLike) for consistency,
    # since archive internals often use POSIX-style paths regardless of OS.
    inner_file: str
    
    # Line number of the match within the file.
    # Optional because if chunk_size=None or reading binary chunks,
    # line numbers may not be available.
    line_no: Optional[int] = None
    
    match_text: Optional[str] = None
    
    # TODO: Attempt to extract context around matched text again.
    context_before: Optional[list[str]] = None
    context_after: Optional[list[str]] = None
    
    FORMAT_SPEC_CHOICES: ClassVar[tuple] = (
        "str", "json", "md", "markdown", "dict", "compact", "tuple", "csv", "list"
    )
    
    def __format__(
        self,
        format_spec=None,
        color=None,
        color_mode=None,
        scheme=None,
        ):
        
        objects = [
            self.archive,
            self.inner_file,
            self.line_no,
            self.match_text,
        ]
        
        format_spec = format_spec or "str"
        
        match format_spec:
            case "str" | "compact" | "md" | "markdown":
                af = self.archive.absolute() if format_spec=="compact" else get_posix_name(self.archive)
                objects[0] = af
                color_compat = format_spec in ("str", "compact") or any((color, color_mode, scheme))

                if color_compat:
                    colorize = ColorizeMatch(color, color_mode, scheme, objects)
                    return colorize.__format__()
                
                string_format = ColorizeMatch.STRING_FORMAT
                objects[0] = f"[{af}]"
                if format_spec in ("md", "markdown"):
                    string_format = f"`{string_format}`"
                return string_format.format(*objects)
            case "dict" | "json":
                data = {
                    k: v for k,v in super(ArchiveMatch, self).asdict().items()
                    # NOTE: Context lines currently only compatible with 'git-diff' format-spec
                    if not k.startswith("context")
                }
                if format_spec == "json":
                    data = super(ArchiveMatch, self).asjson(data=data)
                return data
            case "tuple":
                return tuple(objects)
            case "list":
                return objects
            case "csv":
                match_text = regex_escape(self.match_text)
                objects = (
                    to_posix(self.archive),
                    self.inner_file,
                    str(self.line_no),
                    match_text
                )
                return ",".join(objects)
            # case "git-diff":
            # NOTE: To be used with matched context text.
            #     af = get_posix_name(self.archive)
            #     objects = (
            #         af,
            #         self.inner_file,
            #         self.line_no,
            #         self.context_before,
            #         self.context_after
            #     )
            #     string = "[{}]{}:"
            #     return string.format(*objects[:2])
            case _:
                return self.__str__()
    
    def __str__(self) -> str:
        # Human-readable string for CLI output, similar to zipgrep.
        # Format: [archive]inner_file:line_no:match_text
        return self.__format__("str")




@dataclass(
    unsafe_hash=True,
    slots=True,
    weakref_slot=True
)
class Benchmarks:
    package: str
    timings: list[float]
    performance_index: Optional[float] = float("-inf")
    mean: float = field(default=None, init=False)
    stdev: float = field(default=None, init=False)
    min_timings: float = field(default=None, init=False)
    max_timings: float = field(default=None, init=False)
    cold_start_duration: float = field(default=None, init=False)
    inverse_time: float = field(default=None, init=False)
    relative_speed: float = field(default=None, init=False)
    efficiency_score: float = field(default=None, init=False)
    
    def __post_init__(self):
        if self.timings and len(self.timings) >= 1:
            self.cold_start_duration = self.to_ms(self.timings.pop(0))
            self.mean = self.to_ms(statistics.mean(self.timings))
            self.stdev = self.to_ms(statistics.stdev(self.timings)) if len(self.timings) > 1 else 0
            self.min_timings = self.to_ms(min(self.timings))
            self.max_timings = self.to_ms(max(self.timings))
            self.inverse_time = 1 / self.mean
            self.relative_speed = 1000 / self.mean
            self.efficiency_score = 100000 / self.mean
    
    def __repr__(self):
        try:
            return f"""
{self.package.upper()}:
  ~~> Mean: {self.mean:.2f} ms
  ~~> Std:  {self.stdev:.2f} ms
  ~~> Min:  {self.min_timings:.2f} ms
  ~~> Max:  {self.max_timings:.2f} ms
  ~~> Cold Start:  {self.cold_start_duration:.2f} ms
  ~~> Inverse Time:  {self.inverse_time:.2f} ms
  ~~> Relative Throughput:  {self.relative_speed:.2f} searches/sec
  ~~> Efficiency Score:  {self.efficiency_score:.2f}
  ~~> Normalized Performance Index:  {self.performance_index:.3f}
"""
        except TypeError:
            return super(Benchmarks, self).__repr__()

    def __truediv__(self, other):
        if not isinstance(other, Benchmarks):
            return NotImplemented
        return self.mean / other.mean
    
    def __rtruediv__(self, other):
        if not isinstance(other, (int, float)):
            return NotImplemented
        return other / self.mean
    
    def __bool__(self):
        return bool(self.timings)
    
    def __eq__(self, other):
        if not isinstance(other, Benchmarks):
            return NotImplemented
        return self.mean == other.mean
    
    def is_faster(self, other):
        if not isinstance(other, Benchmarks):
            return NotImplemented
        
        return (other.mean / self.mean) >= (self.mean / other.mean)
    
    @staticmethod
    def to_ms(number):
        return number * 1000
    
    @classmethod
    def dummy_benchmark(cls, package):
        return cls(package, [10e-5]*3)