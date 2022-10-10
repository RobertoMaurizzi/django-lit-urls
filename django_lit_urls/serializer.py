import logging
from functools import lru_cache, reduce
from io import StringIO
from re import sub
from typing import Iterable, Optional, Sequence, Tuple, Union
from urllib.parse import urljoin

from pydantic import BaseModel

from django_lit_urls.utils import _parse_resolver

logger = logging.getLogger(__name__)


def camel_case(s: str) -> str:
    s = sub(r"(_|-)+", " ", s).title().replace(" ", "")
    return "".join([s[0].lower(), s[1:]])


class UrlModel(BaseModel):
    pattern_name: str
    namespace: str
    url_parts: Tuple[str, ...]
    js_vars: Tuple[str, ...]
    url_lookup: str
    is_alternative: bool = False  # Flag whether this is an "extra" pattern name,

    class Config:
        frozen = True

    def matches(self, name: str, params: Optional[Tuple[str]] = None) -> bool:
        """
        Check whether the name and optional parameter names passed
        """
        return self.pattern_name == name and self.js_vars == params if params else self.pattern_name == name

    @property
    def js_func_name(self):
        return camel_case(self.pattern_name)

    @property
    def url(self):
        """
        Return a string literal for
        the current URL incorporating the "js_vars" placeholders
        """
        return reduce(urljoin, self.url_parts)

    @property
    def js_literal(self):
        """
        Returns a JS string literal if there are variables, otherwise a string
        """
        return f"`{self.url}`" if self.js_vars else f'"{self.url}"'

    @property
    def as_function(self):
        """
        Return the template string
        as a standalone function
        """
        return f"function {self.js_func_name}({', '.join(self.js_vars)}){{ return {self.js_literal} }}"

    @property
    def as_class_prop(self):
        """
        Return the template string
        as a standalone function
        """
        return f"{self.js_func_name} ({', '.join(self.js_vars)}) {{ return {self.js_literal} }}"

    @property
    def as_arrow_func(self):
        return f"{self.js_func_name} = ({', '.join(self.js_vars)}) => {self.js_literal};"

    @property
    def as_arrow_func_property(self):
        return f"{self.js_func_name}: ({', '.join(self.js_vars)}) => {self.js_literal}"

    @property
    def as_map_setter(self):
        return f"\"{self.js_func_name}\", ({', '.join(self.js_vars)}) => new URL({self.js_literal}, location.origin))"


class UrlModels(BaseModel):
    urls: Sequence[UrlModel]
    param_name: str = "urls"

    def __post_init__(self):
        """
        If URLS was not defined initially, make it all the
        available URLS
        """
        if len(self.urls) == 0:
            self.urls = [UrlModel(**_r) for _r in _parse_resolver()]

    def filtered_by_name(self, matches: Iterable[Union[str, Tuple[str, Tuple[str]]]] = []):
        """
        Returns a new UrlModels instance
        where the URL names and optionally parameters match the
        given 'match' strings / tuples
        """
        return self.__class__(
            urls=set(
                [
                    um
                    for um in self.urls
                    for match in matches
                    if (isinstance(match, str) and um.matches(match))
                    or (not isinstance(match, str) and um.matches(*match))
                ]
            )
        )

    @property
    def as_map(self):
        """
        Returns Javascript to generate a mapping
        representing how to generate URLs
        """
        indent = 4
        map_ = StringIO()
        map_.write(f"const {self.param_name} = new Map(\n")
        map_.writelines(
            (
                f"""{' '*indent}["{u.js_func_name}", ({', '.join(u.js_vars)}) => new URL({u.js_literal}, location.origin)]"""
                for u in self.urls
            )
        )
        map_.write("\n)")
        map_.seek(0)
        return map_.read()


@lru_cache()
def all_urls() -> UrlModels:
    return UrlModels(urls=[UrlModel(**_r) for _r in _parse_resolver()])
