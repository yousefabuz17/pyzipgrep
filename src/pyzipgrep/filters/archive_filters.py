import datetime as dt
from datetime import datetime


from ..core.models import ArchiveMetadata
from ..utils.common import fromtimestamp, all_values, has_values
from ..utils.exceptions import ErrorCodes
from .base import PZGFileFiltering




class TimeFilter(PZGFileFiltering):
    def __init__(
        self,
        before=None,
        after=None,
        based_on_time_created: bool=True,
        ):
        self._before = before
        self._after = after
        self._based_on_time_created = based_on_time_created
    
    def __call__(self, archive_file: ArchiveMetadata, **kwargs):
        before = self._serialize_time(self._before)
        after = self._serialize_time(self._after, upper_bound=True)
        
        file_ts = getattr(
            archive_file,
            "time_modified_dt" if not self._based_on_time_created 
            else "time_created_dt",
            )
        
        if not has_values((before, after, file_ts)):
            return True
        
        if all_values((before, after)):
            if after > before:
                raise ErrorCodes.raise_error(
                    ErrorCodes.FILTER_ERROR,
                    f"Invalid timestamp sequence: After time '{after}' cannot be greater than before time '{before}'."
                )
            return after <= file_ts <= before
        
        return any((
            before is not None and file_ts <= before,
            after is not None and file_ts >= after
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




class RangeFilter(PZGFileFiltering):
    def __init__(
        self,
        min_arg: int | float=0,
        max_arg: int | float=None,
        *,
        metadata_attr: str=None,
        ) -> None:
        self._min_arg = min_arg
        self._max_arg = max_arg
        self._attr = metadata_attr
    
    def __call__(self, archive_file: ArchiveMetadata, **kwargs):
        min_arg = self._min_arg
        max_arg = self._max_arg
        metadata_value = getattr(archive_file, self._attr)
        
        if not has_values((min_arg, max_arg, metadata_value)):
            return True
        
        if all_values((min_arg, max_arg)):
            if max_arg < min_arg:
                raise ErrorCodes.raise_error(
                    ErrorCodes.FILTER_ERROR,
                    f"Max arg ({max_arg}) cannot be less than min arg ({min_arg})"
                )
            return min_arg <= metadata_value <= max_arg
        
        return any((
            min_arg is not None and metadata_value >= min_arg,
            max_arg is not None and metadata_value <= max_arg
        ))



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



class AgeCreatedFilter(RangeFilter):
    def __init__(self, min_age=None, max_age=None):
        super().__init__(min_age, max_age, metadata_attr="days_since_created")



class AgeModifiedFilter(RangeFilter):
    def __init__(self, min_age=None, max_age=None):
        super().__init__(min_age, max_age, metadata_attr="days_since_modified")