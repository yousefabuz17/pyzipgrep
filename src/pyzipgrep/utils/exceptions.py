from enum import IntEnum, auto



class ErrorCodes(IntEnum):
    SUCCESS = 0
    NO_MATCHES = 1
    EXCEPTION = 2
    KEY_ERROR = auto()
    FILTER_ERROR = auto()
    CHUNK_SIZE_ERROR = auto()
    PREDICATE_ERROR = auto()
    NO_ARCHIVES_ERROR = auto()
    
    @classmethod
    def raise_error(cls, error_code=EXCEPTION, error_msg=""):
        return cls.get_error_class(error_code)(error_msg)
    
    @classmethod
    def get_error_class(cls, error_code: int):
        match error_code:
            case cls.KEY_ERROR:
                cls_error = ArchiveKeyError
            case cls.FILTER_ERROR:
                cls_error = FilterException
            case cls.CHUNK_SIZE_ERROR:
                cls_error = InvalidChunkSize
            case cls.PREDICATE_ERROR:
                cls_error = InvalidPredicate
            case cls.NO_ARCHIVES_ERROR:
                cls_error = NoValidArchives
            case _:
                cls_error = Exception
        return cls_error



class ArchiveKeyError(Exception):
    pass



class InvalidPredicate(Exception):
    pass



class InvalidChunkSize(Exception):
    pass



class NoValidArchives(Exception):
    pass



class FilterException(Exception):
    pass