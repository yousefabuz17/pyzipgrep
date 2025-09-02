from abc import ABC, abstractmethod
from typing import Iterable

from ..utils.common import compiler


# NOTE: Main difference between archive and inner file will be upon its attributes
#   - ArchiveFiltering will filter based on its archive metadata
#   - InnerFileFiltering will simply only filter based its str representation


def regex_compiler(pattern, obj, *, case_sensitive=True):
    return bool(compiler(pattern, case_sensitive).search(obj))


def get_case_sensitive(**kwargs):
    return kwargs.pop("case_sensitive", True)



class BaseFilter(ABC):
    @abstractmethod
    def __call__(self, *args, **kwargs) -> bool:
        raise NotImplementedError
    
    def __and__(self, other): return AndFilter([self, other])
    def __or__(self, other): return OrFilter([self, other])
    def __invert__(self): return NotFilter([self])




class BaseFileFiltering(BaseFilter):
    def __init__(self, filters: Iterable[BaseFilter]):
        self._filters = filters
    
    def __call__(self, archive_or_inner_file, **kwargs):
        case_sensitive = get_case_sensitive(**kwargs)
        return [
            func(archive_or_inner_file, case_sensitive=case_sensitive)
            for func in self._filters
        ]



class LogicalFilter(BaseFileFiltering):
    def __init__(self, filters, method=None):
        super().__init__(filters)
        self._method = method or all
    
    def __call__(self, archive_or_inner_file, **kwargs):
        case_sensitive = get_case_sensitive(**kwargs)
        filtered = super().__call__(archive_or_inner_file, case_sensitive=case_sensitive)
        return self._method(filtered)


class AndFilter(LogicalFilter):
    def __init__(self, *args):
        super().__init__(*args, method=all)


class OrFilter(LogicalFilter):
    def __init__(self, *args):
        super().__init__(*args, method=any)


class NotFilter(LogicalFilter):
    def __init__(self, *args):
        super().__init__(*args, method=NotFilter.negate)
    
    @staticmethod
    def negate(results):
        return not any(results)




class ProcessFilters(LogicalFilter):
    def __init__(
        self,
        filters: Iterable[BaseFilter],
        case_sensitive=False,
        require_all=True,
        require_none=False
        ) -> None:
        
        method = any if not require_all else all
        if require_none:
            method = NotFilter.negate
        super().__init__(filters, case_sensitive=case_sensitive, method=method)