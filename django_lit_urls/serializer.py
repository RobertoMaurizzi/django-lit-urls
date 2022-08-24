import logging
from functools import lru_cache, reduce
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


class UrlModels(BaseModel):
    urls: Sequence[UrlModel]

    def filtered_by_name(self, match=Iterable[Union[str, Tuple[str, Tuple[str]]]]):
        """
        Returns a new UrlModels instance
        where the URL names and optionally parameters match the
        """
        return self.__class__(
            urls=(
                um
                for um in self.urls
                if (isinstance(match, str) and um.matches(match))
                or (not isinstance(match, str) and um.matches(*match))
            )
        )

    @classmethod
    def all_urls(cls):
        return cls(urls=[UrlModel(**_r) for _r in _parse_resolver()])


@lru_cache()
def all_urls():
    return UrlModels.all_urls()
