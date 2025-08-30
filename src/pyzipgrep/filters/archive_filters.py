import datetime as dt
from datetime import datetime


from ..core.models import ArchiveMetadata
from ..utils.common import fromtimestamp
from .base import BaseFileFiltering



# TODO:
# ** Create a `create_filters` method?
#   - Retrieve all provided arguments
#       - Pass them into the method
#       - Returns an iterable of custom made filters
#           - Filters for 3 categories?
#               - ArchiveFiltering
#               - InnerFileFiltering
#               - FileContentFiltering
#               - UserDefinedFilters?


# NOTE: Archive name filtering will be derives from .file_filters




def _any(iterable, use_any=True) -> bool:
    method = all if not use_any else any
    return method(i is not None for i in iterable)

def _all(iterable) -> bool:
    return _any(iterable, use_any=False)



class TimeFilter(BaseFileFiltering):
    def __init__(self, before=None, after=None, based_on_time_created: bool = True):
        self._before = before
        self._after = after
        self._based_on_time_created = based_on_time_created
    
    def __call__(self, archive_file: ArchiveMetadata):
        before = self._serialize_time(self._before)
        after = self._serialize_time(self._after, upper_bound=True)
        
        file_ts = getattr(
            archive_file,
            "time_modified_dt" if not self._based_on_time_created 
            else "time_created_dt",
            )
        
        if not _any((before, after, file_ts)):
            return True
        
        if _all((before, after)):
            return before >= file_ts >= after
        
        return any((
            before and file_ts < before,
            after and file_ts < after
        ))
    
    def _serialize_time(self, arg, upper_bound: bool=False):
        if arg is not None:
            if isinstance(arg, datetime):
                return arg
            
            if isinstance(arg, float):
                return fromtimestamp(arg)
            
            if isinstance(arg, dt.date):
                return datetime.combine(
                    arg,
                    dt.time.max if upper_bound else dt.time.min
                )
            
            if upper_bound:
                dt_time = (23, 59, 59, 999999)
            else:
                dt_time = (1, 0, 0, 0)
            
            if isinstance(arg, (int, str)) and len(str(arg)) == 4:
                year = int(arg)
                return (
                    datetime(year, 12, 31, *dt_time)
                    if upper_bound else
                    datetime(year, 1, 1, *dt_time)
                )
            
            if isinstance(arg, tuple):
                if len(arg) == 2:
                    year, month = arg
                    if upper_bound:
                        anchor_date = datetime(year, month, 28) + dt.timedelta(days=4)
                        end_of_month = (anchor_date - dt.timedelta(anchor_date.day))
                        day = end_of_month.day
                    else:
                        day = 1
                elif len(arg) == 3:
                    year, month, day = arg
                else:
                    year, month, day, *dt_time = arg
                    if isinstance(dt_time, int):
                        dt_time = [dt_time]
                return datetime(year, month, day, *dt_time)




class RangeFilter(BaseFileFiltering):
    def __init__(
        self,
        min_arg: int | float=None,
        max_arg: int | float=None,
        *,
        metadata_attr: str=None
        ) -> None:
        self._min_arg = min_arg
        self._max_arg = max_arg
        self._attr = metadata_attr
    
    def __call__(self, archive_file: ArchiveMetadata):
        min_arg = self._min_arg
        max_arg = self._max_arg
        metadata_value = getattr(archive_file, self._attr)
        
        if not _any((min_arg, max_arg, metadata_value)):
            return True
        
        if _all((min_arg, max_arg)):
            return min_arg <= metadata_value < max_arg
        
        if min_arg is not None:
            return metadata_value >= min_arg
        
        if max_arg is not None:
            return metadata_value < max_arg


class SizeFilter(RangeFilter):
    def __init__(self, min_size=None, max_size=None):
        super().__init__(min_size, max_size, metadata_attr="size")



class TotalFilesFilter(RangeFilter):
    def __init__(self, min_size=None, max_size=None):
        super().__init__(min_size, max_size, metadata_attr="total_files")



class TotalCompressedFilter(RangeFilter):
    def __init__(self, min_size=None, max_size=None):
        super().__init__(min_size, max_size, metadata_attr="total_compressed")



class TotalUncompressedFilter(RangeFilter):
    def __init__(self, min_size=None, max_size=None):
        super().__init__(min_size, max_size, metadata_attr="total_uncompressed")



class RatioFilter(RangeFilter):
    def __init__(self, min_size=None, max_size=None):
        super().__init__(min_size, max_size, metadata_attr="ratio")