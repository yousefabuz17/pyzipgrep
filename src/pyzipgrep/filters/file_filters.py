from typing import Iterable

from .base import PZGFileFiltering
from ..utils.common import (
    has_values,
    get_posix_name,
    is_string,
    regex_search,
    to_posix
)




class BasePathFilter(PZGFileFiltering):
    def __init__(self, pattern, use_regex=False, name_only=False, case_sensitive=True):
        self._pattern = pattern
        self._use_regex = use_regex
        self._name_only = name_only
        self._case_sensitive = case_sensitive
    
    def __call__(self, file, **kwargs):
        if self._name_only:
            file = get_posix_name(file)
        else:
            file = to_posix(file)
        
        case_sensitive = self._case_sensitive
        
        if self._use_regex:
            return regex_search(
                self._pattern, file,
                case_sensitive=case_sensitive
                )
        
        if not case_sensitive:
            file = file.lower()
        
        return self._pattern == file




class FileNameFilter(BasePathFilter):
    def __init__(self, pattern, use_regex=False, case_sensitive=True):
        super().__init__(pattern, use_regex, case_sensitive=case_sensitive, name_only=True)




class FileExtensionFilter(PZGFileFiltering):
    def __init__(
        self,
        extensions: Iterable[str]=None,
        exclude_extensions: Iterable[str]=None,
        case_sensitive=True
        ):
        self._extensions = extensions
        self._exclude_extensions = exclude_extensions
        self._case_sensitive = case_sensitive
    
    def serialize_extension(self, extension) -> str:
        if extension is None:
            return
        
        if extension == "":
            return ""
        
        if not extension.startswith("."):
            extension = "." + extension
        
        if not self._case_sensitive:
            extension = extension.lower()
        return extension
    
    def __call__(self, file, **kwargs):
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
        
        - If both include (`extensions`) and exclude (`exclude_extensions`) sets exist,
          a file must match the include list and must not match the exclude list.
          This gives explicit control when overlaps occur.
        """
        
        exts = self._extensions or []
        xexts = self._exclude_extensions or []

        # If no filters are provided → allow everything
        if not has_values((exts, xexts)):
            return True
        
        if is_string(exts):
            exts = [exts]
        
        if is_string(xexts):
            xexts = [xexts]
        
        exts = set(se for e in exts if (se := self.serialize_extension(e)) is not None)
        xexts = set(xse for x in xexts if (xse := self.serialize_extension(x)) is not None)
        file = get_posix_name(file)
        
        # Rationale: files with no suffix
        # or hidden dotfiles (like `.env`) often have no extension
        # are ONLY allowed if user explicitly
        # included "" in the extension set. This enforces clarity in filtering.
        is_hidden_file = file.startswith(".") and file.count(".") == 1
        no_extension_file = "." not in file
        
        if any((
            no_extension_file,
            is_hidden_file,
            allow_no_extension_files := "" in exts,
            "" in xexts,
        )):
            exclude_no_extension_files = "" not in xexts
            
            if all((exts, xexts)):
                return allow_no_extension_files and exclude_no_extension_files
            
            if exts and not xexts:
                return allow_no_extension_files
            
            return exclude_no_extension_files
        
        file_suffix = self.serialize_extension(file.split(".")[-1])
        
        if all((exts, xexts)):
            return file_suffix in exts and file_suffix not in xexts
        
        if exts and not xexts:
            return file_suffix in exts
        return file_suffix not in xexts