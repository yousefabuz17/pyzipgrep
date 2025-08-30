from typing import Iterable

from .base import BaseFileFiltering
from ..utils.common import (
    compiler,
    get_posix_name,
    is_string
)





class FileNameFilter(BaseFileFiltering):
    def __init__(self, pattern):
        self._pattern = pattern
    
    def __call__(self, file):
        file = get_posix_name(file)
        return bool(compiler(self._pattern).search(file))




class FileExtensionFilter(BaseFileFiltering):
    def __init__(
        self,
        extensions: Iterable[str]=None,
        exclude_extensions: Iterable[str]=None,
        ):
        self._extensions = extensions
        self._exclude_extensions = exclude_extensions
    
    @staticmethod
    def serialize_extension(extension) -> str:
        if not extension:
            return ""
        
        if not extension.startswith("."):
            extension = "." + extension
        
        # TODO (IMPORTANT):
        # Update later on to include case-sensitive
        return extension.lower()
    
    def __call__(self, file):
        """
        Decide whether a given file should be included based on the 
        allow/deny extension rules.

        Key rules and rationale:
        - If no filters are provided, all files are allowed 
          (useful default: unrestricted mode).
        
        - Files with no extension and hidden files like `.env` (with no true extension)
          are treated as a special case. They are only included or excluded
          if the empty string `""` appears in the corresponding rule set.
          This ensures they don’t slip through unintentionally when the user 
          applies extension-based filtering, while still allowing precise control 
          over whether files with no extensions are permitted.
        
        - Archive files (e.g., `.zip`) require explicit inclusion in the rule set.  
          This means that files inside an archive are only processed if the archive 
          itself passes the filter. For example, if `.zip` is not listed in the 
          `extensions` set, no files within a `.zip` archive will be discovered.  
          This design enforces intentional handling of container formats to avoid 
          unwrapping archives the user did not explicitly allow.
        
        - If both include (`extensions`) and exclude (`exclude_extensions`) sets exist,
          a file must match the include list and must not match the exclude list.
          This gives explicit control when overlaps occur.
        """
        
        exts = self._extensions or []
        xexts = self._exclude_extensions or []
        
        # If no filters are provided → allow everything
        if not any((exts, xexts)):
            return True
        
        if is_string(exts):
            exts = [exts]
        
        if is_string(xexts):
            xexts = [xexts]
        
        exts = set(self.serialize_extension(e) for e in exts)
        xexts = set(self.serialize_extension(x) for x in xexts)
        file = get_posix_name(file)
        is_hidden_file = file.startswith(".") and file.count(".") == 1
        
        # Rationale: files with no suffix
        # or hidden dotfiles (like `.env`) often have no extension
        # are ONLY allowed if user explicitly
        # included "" in the extension set. This enforces clarity in filtering.
        if "." not in file or is_hidden_file:
            return "" in exts
        
        file_suffix = self.serialize_extension(file.split(".")[-1])
        
        if all((exts, xexts)):
            return file_suffix in exts and file_suffix not in xexts
        
        if exts and not xexts:
            return file_suffix in exts
        return file_suffix not in xexts