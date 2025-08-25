from functools import wraps
from pathlib import Path

from ..core.models import CoreZip, ArchiveMetadata
from ..utils.common import has_attribute



class ArchiveReader(ArchiveMetadata, CoreZip):
    def __init__(self, archive_file):
        self._archive_file = Path(archive_file).expanduser()
        super().__init__(**self.get_metadata() or {"file": self._archive_file})
    
    def __must_exist(default=None):
        def decorator(func):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                if (self._archive_file
                    and self._archive_file.exists()
                    and self.is_zipfile(self._archive_file)):
                    return func(self, *args, **kwargs)
                return default
            return wrapper
        return decorator
    
    @staticmethod
    def serialize_archive(archive_file):
        return ArchiveReader(archive_file)
    
    @__must_exist()
    def read_zip(self):
        return super().ZipFile(self._archive_file, mode="r")
    
    @__must_exist()
    def open_file_path(self, file_path):
        try:
            return self.read_zip().open(file_path)
        except KeyError:
            raise KeyError(
                f"There is no item named {file_path!r} in the archive {self._archive_file!r}"
            )
    
    @__must_exist()
    def is_valid_zipfile(self) -> bool:
        return super().is_zipfile(self._archive_file)
    
    @__must_exist()
    def __len__(self):
        return len(self.infolist())

    @__must_exist(default=[])
    def infolist(self):
        return self.read_zip().infolist()
    
    @__must_exist(default=[])
    def namelist(self):
        return self.read_zip().namelist()
    
    @__must_exist(default={})
    def get_metadata(self):
        def _get_stat(attr):
            return sum(getattr(i, attr) for i in infolist)
        
        infolist = self.infolist()
        
        if not infolist:
            return
        
        archive = self._archive_file
        archive_stat = archive.stat()
        
        if has_attribute(archive_stat, "st_birthtime"):
            time_created = archive_stat.st_birthtime
        else:
            time_created = archive_stat.st_ctime
        
        time_modified = archive_stat.st_mtime
        size = archive_stat.st_size
        total_uncompressed = _get_stat("file_size")
        total_compressed = _get_stat("compress_size")
        
        return {
            "file": archive,
            "time_created": time_created,
            "time_modified": time_modified,
            "size": size,
            "total_files": self.__len__(),
            "total_uncompressed": total_uncompressed,
            "total_compressed": total_compressed
        }