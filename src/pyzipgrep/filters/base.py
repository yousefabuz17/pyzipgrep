from abc import ABC, abstractmethod

from typing import Protocol



class BaseFilter(ABC):
    @abstractmethod
    def __call__(self, *args, **kwds) -> bool: ...



class ArchiveContentFiler(Protocol):
    def __init__(self, pattern: str):
        import re
        self.rx = re.compile(pattern)

    def __call__(self, content: str) -> bool:
        return bool(self.rx.search(content))