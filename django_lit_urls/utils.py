import logging
import re
import warnings
from typing import Any, Dict, Iterable, Optional, Set, Tuple, Union

from django.urls import LocalePrefixPattern, URLPattern, URLResolver, get_resolver
from django.urls.resolvers import RegexPattern, RoutePattern

logger = logging.getLogger(__name__)

MaybeResolver = Optional[Union[URLPattern, URLResolver]]
Url = str
JsFunction = str
Namespace = str
Params = Tuple[str, ...]

url_arg_re = re.compile(r"(\(.*?\))")
url_kwarg_re = re.compile(r"(\(\?P\<(.*?)\>.*?\))")
url_optional_char_re = re.compile(r"(?:\w|/)(?:\?|\*)")
url_optional_group_re = re.compile(r"\(\?\:.*\)(?:\?|\*)")
url_path_re = re.compile(r"(\<.*?\>)")


def _parse_resolver(
    resolver: Optional[URLResolver] = None,
    current_namespace: Optional[str] = None,
    url_parts: Tuple[str, ...] = ("/",),
    include_all: bool = True,
    include_namespaces: Set[str] = set(),
    exclude_namespaces: Set[str] = {
        "admin",
    },
    js_vars: Params = (),
    url_lookup: str = "",
) -> Iterable[Dict[str, Any]]:

    resolver = resolver or get_resolver()

    # Determine the effective namespace based on the
    # curent namespace and the resolver
    if current_namespace and resolver.namespace:
        ns = f"{current_namespace}:{resolver.namespace}"
    elif resolver.namespace:
        ns = f"{resolver.namespace}"
    elif current_namespace:
        ns = f"{current_namespace}"
    else:
        ns = ""

    if not (
        include_all
        and (include_namespaces is not None and ns not in include_namespaces)
        or (exclude_namespaces is not None and ns in exclude_namespaces)
    ):
        logger.debug(f"Skipping namespace {ns}")
        return

    for url_pattern in resolver.url_patterns:
        # url_part_or_full is a url with variables replaced by "Javascript" type literal vars
        # js_vars is the list of named variables in the function
        try:
            logger.debug(f"parsing {url_pattern}")
            standardise_url: str = _url_from_pattern(url_pattern)  # type: ignore
            url_part_or_full, extra_js_vars = _url_to_js_func(standardise_url)
            logger.debug(f"parsed {standardise_url}: {url_part_or_full} {extra_js_vars}")
        except Exception as E:
            warnings.warn(f"{E}")
            continue

        if isinstance(url_pattern, URLResolver):
            yield from _parse_resolver(
                url_pattern,
                current_namespace=ns,
                url_parts=(*url_parts, url_part_or_full),
                include_all=include_all,
                js_vars=(*js_vars, *extra_js_vars),
            )

        elif isinstance(url_pattern, URLPattern) and url_pattern.name:
            yield dict(
                pattern_name=url_pattern.name,
                namespace=ns,
                url_parts=(*url_parts, url_part_or_full),
                js_vars=(*js_vars, *extra_js_vars),
                url_lookup=f"{url_pattern.lookup_str}",
            )


def _url_from_pattern(url_pattern: Union[URLPattern, URLResolver]) -> str:
    """
    "Standardise" the different types of URL
    we might encounter to a simple string
    """

    pattern: Union[LocalePrefixPattern, RegexPattern, RoutePattern] = url_pattern.pattern
    url: Optional[str] = None

    if isinstance(pattern, LocalePrefixPattern):
        url = pattern.language_prefix
    elif isinstance(pattern, RegexPattern):
        url = pattern._regex  # type: ignore
    elif isinstance(pattern, RoutePattern):
        url = pattern._route  # type: ignore
    else:
        raise NotImplementedError(f"Unrecognized URL pattern type: {url_pattern} {type(pattern)}")
    if url is None:
        raise NotImplementedError(f"Unrecognized URL pattern type: {url_pattern} {type(pattern)}")
    return url.replace("^", "").replace("$", "")


def _url_to_js_func(url: Url) -> Tuple[JsFunction, Params]:
    js_vars = []
    new_url = f"{url}"
    for str_replace, js_var_name, js_var_pos in _url_js_replacements(url):
        logger.debug(f"{str_replace} -> {js_var_name} ({js_var_pos})")
        if js_var_name:
            new_url = new_url.replace(str_replace, f"${{{js_var_name}}}")
        else:
            # Assign an "anonymous" positional var
            js_var_name = f"v_{js_var_pos}"
            new_url = new_url.replace(str_replace, f"${{{js_var_name}}}")
        js_vars.append(js_var_name)
    return new_url, tuple(js_vars)


def _url_js_replacements(url: str) -> Iterable[Tuple[str, Optional[str], int]]:
    """
    Returns tuples of the strings to be replaced in a given URL
    """
    pos = 0
    logger.debug(url)
    # Removes optional groups from the URL pattern.
    if optional_group_matches := url_optional_group_re.findall(url):
        for el in optional_group_matches:
            pos += 1
            logger.debug(f"opt group matches {el} ({pos})")
            url = url.replace(el, "")
            yield el, None, pos

    # Removes optional characters from the URL pattern.
    if optional_char_matches := url_optional_char_re.findall(url):
        for el in optional_char_matches:
            pos += 1
            logger.debug(f"opt char matches {el} ({pos})")
            url = url.replace(el, "")
            yield el, None, pos

    # Identifies named URL arguments inside the URL pattern.
    # A "named URL argument" has the form `(?P<year>[0-9]{4})`
    if kwarg_matches := url_kwarg_re.findall(url):
        for el in kwarg_matches:
            pos += 1
            logger.debug(f"kwarg matches {el[0]} ({pos})")
            url = url.replace(el[0], "")
            yield el[0], el[1], pos

    # Identifies unnamed URL arguments inside the URL pattern.
    if args_matches := url_arg_re.findall(url):
        for el in args_matches:
            pos += 1
            logger.debug(f"arg matches {el} ({pos})")
            url = url.replace(el, "")
            yield el, None, pos

    # Identifies path expression and associated converters inside the URL pattern.
    # A "path  URL argument" has an optional converter type and parameter name.
    # Such as `<int:year>`
    if path_matches := url_path_re.findall(url):
        for el in path_matches:
            pos += 1
            replace_in_path = el.split(":")[-1].replace(":", "").replace("<", "").replace(">", "")
            logger.debug(f"path matches {el} ({pos})")
            yield el, replace_in_path, pos
