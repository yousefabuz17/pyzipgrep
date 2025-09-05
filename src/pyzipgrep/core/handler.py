from .models import ArchiveMatch



class ContentController:
    def __init__(
        self,
        archive_file,
        inner_file,
        content,
        *,
        content_predicate=None,
        chunk_size=None,
        count=None,
        context_before=None,
        context_after=None,
        ):
        self._archive_file = archive_file
        self._inner_file = inner_file
        self._content = content
        self._content_predicate = content_predicate
        self._chunk_size = chunk_size
    
    def _not_implemented_idx(self, idx):
        if self._chunk_size is not None:
            idx = str(idx) + "?"
        return idx
    
    def _context_handler(self, contents):
        content_predicate = self._content_predicate
        for idx, line in enumerate(contents.splitlines(), start=1):
            if content_predicate and not content_predicate(line):
                continue
            
            yield ArchiveMatch(
                self._archive_file,
                self._inner_file,
                self._not_implemented_idx(idx),
                match_text=line,
            )
    
    async def handle(self):
        for inner_file_content in self._content:
            for match in self._context_handler(inner_file_content):
                yield match