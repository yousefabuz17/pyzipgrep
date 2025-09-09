from abc import ABC, abstractmethod
from typing import Iterable



FILTER_ALL = all
FILTER_ANY = any
FILTER_NONE = lambda results: not any(results)



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
        self._method = method or FILTER_ALL
    
    def __call__(self, archive_or_inner_file, **kwargs):
        case_sensitive = self._case_sensitive
        filtered = super().__call__(archive_or_inner_file, case_sensitive=case_sensitive)
        return self._method(filtered)


class PZGAndFilter(LogicalFilter):
    def __init__(self, *args):
        super().__init__(*args, method=FILTER_ALL)


class PZGOrFilter(LogicalFilter):
    def __init__(self, *args):
        super().__init__(*args, method=FILTER_ANY)


class PZGNotFilter(LogicalFilter):
    def __init__(self, *args):
        super().__init__(*args, method=FILTER_NONE)




class ProcessFilters(LogicalFilter):
    def __init__(
        self,
        filters: Iterable[PZGFilter],
        require_all=True,
        require_none=False
        ) -> None:
        
        method = FILTER_ANY if not require_all else FILTER_ALL
        if require_none:
            method = PZGNotFilter.negate
        super().__init__(filters, method=method)