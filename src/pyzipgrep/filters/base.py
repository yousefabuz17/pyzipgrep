from abc import ABC, abstractmethod
from typing import Iterable, Protocol



# NOTE: Main difference between archive and inner file will be upon its attributes
#   - ArchiveFiltering will filter based on its archive metadata
#   - InnerFileFiltering will simply only filter based its str representation



class BaseFilter(ABC):
    @abstractmethod
    def __call__(self, *args, **kwargs) -> bool: ...



class FilterProtocol(Protocol):
    def __call__(self, *args, **kwargs) -> bool: ...



class BaseFileFiltering(BaseFilter):
    @abstractmethod
    def __call__(self, archive_or_inner_file):
        return super().__call__(archive_or_inner_file)



class ProcessFileFilters:
    def __init__(self, filters: Iterable[FilterProtocol]):
        self._filters = filters
    
    def __call__(self, *args, **kwargs) -> bool:
        # TODO: Allow all or any filter to pass??? Let user decide??
        # Implement arg called 'flexible_filtering'? for any filer to pass through
        # E.g, If file has ext of ... (and|or) file name == ...
        return all(func(*args, **kwargs) for func in self._filters)