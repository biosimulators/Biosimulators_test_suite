from  typing import Union, Dict, List

_JSONValue = Union[str, int, float, bool, Dict[str, '_JSONValue'], List['_JSONValue'], None ]
JSONType = Dict[str, '_JSONValue']