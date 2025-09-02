from .base import BaseFilter, regex_compiler





class ContentFilter(BaseFilter):
    def __init__(self, pattern, use_regex=False):
        self._pattern = pattern
        self._use_regex = use_regex
    
    def __call__(self, files_content, **kwargs):
        case_sensitive = kwargs.get("case_sensitive", True)
        if self._use_regex:
            return regex_compiler(
                self._pattern,
                files_content,
                case_sensitive=case_sensitive
            )
        if not case_sensitive:
            files_content = files_content.lower()
        return self._pattern in files_content




class ContentStringFilter(ContentFilter):
    def __init__(self, pattern):
        super().__init__(pattern, use_regex=False)





class ContentRegexFilter(ContentFilter):
    def __init__(self, pattern):
        super().__init__(pattern, use_regex=True)