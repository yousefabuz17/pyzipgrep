import zipfile
import tarfile

from dataclasses import (
    asdict,
    dataclass,
    field,
    is_dataclass,
)
from datetime import datetime
from typing import Any, ClassVar, Optional


from ..utils.common import (
    PathLike,
    calculate_days_since_created,
    calculate_ratio,
    is_numeric,
    get_posix_name,
)




class CoreZip:
    ZipFile: ClassVar[type[zipfile.ZipFile]] = zipfile.ZipFile
    is_zipfile: ClassVar[staticmethod] = staticmethod(zipfile.is_zipfile)
    
    # TODO: Support for other file types? tar.bz2
    TarFile: ClassVar[type[tarfile.TarFile]] = tarfile.TarFile
    is_tarfile: ClassVar[staticmethod] = staticmethod(tarfile.is_tarfile)





class Serializable:
    is_dataclass = staticmethod(is_dataclass)
    
    def asdict(self) -> dict[str, Any]:
        if self.is_dataclass(self):
            return asdict(self)
        return self.__dict__.copy()
    
    def astuple(self) -> tuple[str, Any]:
        return tuple(self.asdict().items())
    
    def asjson(self):
        import json
        return json.dumps(self.asdict(), default=lambda o: str(o))
    
    def clean_kwargs(self, **kwargs):
        [
            kwargs.pop(k, None)
            for k,v in self.__dataclass_fields__.items()
            if not v.init
        ]
        return kwargs
    
    @property
    def has_set_attributes(self) -> bool:
        return any(map(bool, self.asdict().values()))






@dataclass(
    kw_only=True,
    unsafe_hash=True,
    slots=True,
    weakref_slot=True
)
class ArchiveMetadata(Serializable):
    file: PathLike
    time_created: Optional[float | datetime] = None
    time_modified: Optional[float | datetime] = None
    size: Optional[int] = None
    total_files: Optional[int] = None
    total_uncompressed: Optional[int | float] = None
    total_compressed: Optional[int | float] = None
    
    ratio: Optional[int | float] = field(default=None, init=False)
    time_created_dt: Optional[datetime] = field(default=None, init=False, repr=False)
    time_modified_dt: Optional[datetime] = field(default=None, init=False, repr=False)
    days_since_created: Optional[datetime] = field(default=None, init=False, repr=False)
    days_since_modified: Optional[datetime] = field(default=None, init=False, repr=False)
    
    def __post_init__(self) -> None:
        if all(map(is_numeric, (self.total_compressed, self.total_uncompressed))):
            self.ratio = calculate_ratio(self.total_compressed, self.total_uncompressed)
        
        if is_numeric(self.time_created):
            self.time_created_dt = datetime.fromtimestamp(self.time_created)
            self.days_since_created = calculate_days_since_created(self.time_created)
        
        if is_numeric(self.time_modified):
            self.time_modified_dt = datetime.fromtimestamp(self.time_modified)
            self.days_since_modified = calculate_days_since_created(self.time_modified)





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
    lines_before: Optional[list[str]] = None
    lines_after: Optional[list[str]] = None
    
    def __str__(self) -> str:
        # Human-readable string for CLI output, similar to zipgrep.
        # Format: [archive]inner_file:line_no:match_text
        return "[{}]{}:{}:{}".format(
            get_posix_name(self.archive),
            self.inner_file,
            self.line_no,
            self.match_text
        )