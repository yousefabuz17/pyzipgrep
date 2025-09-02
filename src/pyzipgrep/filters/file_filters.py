from functools import partial
from typing import Iterable

from .base import BaseFileFiltering, get_case_sensitive, regex_compiler
from ..utils.common import (
    get_posix_name,
    is_string,
    to_posix
)




class BasePathFilter(BaseFileFiltering):
    def __init__(self, pattern, use_regex=False, name_only=False):
        self._pattern = pattern
        self._use_regex = use_regex
        self._name_only = name_only
    
    def __call__(self, file, **kwargs):
        if self._name_only:
            file = get_posix_name(file)
        else:
            file = to_posix(file)
        
        case_sensitive = get_case_sensitive(**kwargs)
        if self._use_regex:
            return regex_compiler(
                self._pattern, file,
                case_sensitive=case_sensitive
                )
        
        if not case_sensitive:
            file = file.lower()
        return self._pattern in file




class FileNameFilter(BasePathFilter):
    def __init__(self, pattern, use_regex=False):
        super().__init__(pattern, use_regex, name_only=True)




class FileExtensionFilter(BaseFileFiltering):
    def __init__(
        self,
        extensions: Iterable[str]=None,
        exclude_extensions: Iterable[str]=None,
        ):
        self._extensions = extensions
        self._exclude_extensions = exclude_extensions
    
    @staticmethod
    def serialize_extension(extension, case_sensitive=True) -> str:
        if not extension:
            return ""
        
        if not extension.startswith("."):
            extension = "." + extension
        
        if not case_sensitive:
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
        case_sensitive = get_case_sensitive(**kwargs)
        
        # If no filters are provided → allow everything
        if not any((exts, xexts)):
            return True
        
        if is_string(exts):
            exts = [exts]
        
        if is_string(xexts):
            xexts = [xexts]
        
        serialize_extension = partial(
            self.serialize_extension,
            case_sensitive=case_sensitive
        )
        exts = set(serialize_extension(e) for e in exts)
        xexts = set(serialize_extension(x) for x in xexts)
        file = get_posix_name(file)
        is_hidden_file = file.startswith(".") and file.count(".") == 1
        
        # Rationale: files with no suffix
        # or hidden dotfiles (like `.env`) often have no extension
        # are ONLY allowed if user explicitly
        # included "" in the extension set. This enforces clarity in filtering.
        allow_no_extension_files = "" in exts
        
        if any((
            "." not in file,
            is_hidden_file,
            allow_no_extension_files
        )):
            return bool(allow_no_extension_files)
        
        file_suffix = serialize_extension(file.split(".")[-1])
        
        if all((exts, xexts)):
            return file_suffix in exts and file_suffix not in xexts
        
        if exts and not xexts:
            return file_suffix in exts
        return file_suffix not in xexts