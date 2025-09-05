from .base import PZGFilter, regex_compiler





class ContentFilter(PZGFilter):
    def __init__(self, pattern, use_regex=False, case_sensitive=True):
        self._pattern = pattern
        self._use_regex = use_regex
        self._case_sensitive = case_sensitive
    
    def __call__(self, files_content, **kwargs):
        case_sensitive = self._case_sensitive
        
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
    def __init__(self, pattern, case_sensitive=True):
        super().__init__(pattern, case_sensitive=case_sensitive)





class ContentRegexFilter(ContentFilter):
    def __init__(self, pattern, case_sensitive=True):
        super().__init__(
            pattern,
            use_regex=True,
            case_sensitive=case_sensitive
        )