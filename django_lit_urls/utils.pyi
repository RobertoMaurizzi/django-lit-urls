from typing import Optional, Tuple, Union

from django.urls import URLPattern, URLResolver

from _typeshed import Incomplete as Incomplete

logger: Incomplete
MaybeResolver = Optional[Union[URLPattern, URLResolver]]
Url = str
JsFunction = str
Namespace = str
Params = Tuple[str, ...]
url_arg_re: Incomplete
url_kwarg_re: Incomplete
url_optional_char_re: Incomplete
url_optional_group_re: Incomplete
url_path_re: Incomplete
