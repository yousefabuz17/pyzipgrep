import operator

from ..utils.common import is_numeric, regex_search
from .base import PZGFilter




class ContentFilter(PZGFilter):
    def __init__(self, pattern, use_regex=False, case_sensitive=True):
        self._pattern = pattern
        self._use_regex = use_regex
        self._case_sensitive = case_sensitive
    
    def __call__(self, files_content, **kwargs):
        case_sensitive = self._case_sensitive
        
        if self._use_regex:
            return regex_search(
                self._pattern,
                files_content,
                case_sensitive=case_sensitive
            )
        if not case_sensitive:
            files_content = files_content.lower()
        return self._pattern in files_content




class ContentStringFilter(ContentFilter):
    def __init__(self, pattern, case_sensitive=True):
        super().__init__(pattern, case_sensitive=case_sensitive)





class ContentRegexFilter(ContentFilter):
    def __init__(self, pattern, case_sensitive=True):
        super().__init__(
            pattern,
            use_regex=True,
            case_sensitive=case_sensitive
        )



class ContentLengthFilter(PZGFilter):
    def __init__(self, length: int | str):
        self._length = length
    
    def __call__(self, files_content, **kwargs):
        length = self._length
        op = operator.eq
        
        if is_numeric(length):
            length = int(length)
        else:
            if length.endswith(("-", "+")):
                symbol = length[-1]
                length = int(length[:-1])
                if symbol == "-":
                    op = operator.le
                else:
                    op = operator.ge
        return op(len(files_content), length)