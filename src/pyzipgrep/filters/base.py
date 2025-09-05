from abc import ABC, abstractmethod
from typing import Iterable

from ..utils.common import compiler


# NOTE: Main difference between archive and inner file will be upon its attributes
#   - ArchiveFiltering will filter based on its archive metadata
#   - InnerFileFiltering will simply only filter based its str representation


def regex_compiler(pattern, obj, *, case_sensitive=True):
    return bool(compiler(pattern, case_sensitive).search(obj))



class PZGFilter(ABC):
    @abstractmethod
    def __call__(self, *args, **kwargs) -> bool:
        raise NotImplementedError
    
    def __and__(self, other): return PZGAndFilter([self, other])
    def __or__(self, other): return PZGOrFilter([self, other])
    def __invert__(self): return PZGNotFilter([self])




class PZGFileFiltering(PZGFilter):
    def __init__(self, filters: Iterable[PZGFilter], case_sensitive=True):
        self._filters = filters
        self._case_sensitive = case_sensitive
    
    def __call__(self, archive_or_inner_file, **kwargs):
        case_sensitive = self._case_sensitive
        return [
            func(archive_or_inner_file, case_sensitive=case_sensitive)
            for func in self._filters
        ]



class LogicalFilter(PZGFileFiltering):
    def __init__(self, filters, method=None):
        super().__init__(filters)
        self._method = method or all
    
    def __call__(self, archive_or_inner_file, **kwargs):
        case_sensitive = self._case_sensitive
        filtered = super().__call__(archive_or_inner_file, case_sensitive=case_sensitive)
        return self._method(filtered)


class PZGAndFilter(LogicalFilter):
    def __init__(self, *args):
        super().__init__(*args, method=all)


class PZGOrFilter(LogicalFilter):
    def __init__(self, *args):
        super().__init__(*args, method=any)


class PZGNotFilter(LogicalFilter):
    def __init__(self, *args):
        super().__init__(*args, method=PZGNotFilter.negate)
    
    @staticmethod
    def negate(results):
        return not any(results)




class ProcessFilters(LogicalFilter):
    def __init__(
        self,
        filters: Iterable[PZGFilter],
        case_sensitive=True,
        require_all=True,
        require_none=False
        ) -> None:
        
        method = any if not require_all else all
        if require_none:
            method = PZGNotFilter.negate
        super().__init__(filters, case_sensitive=case_sensitive, method=method)