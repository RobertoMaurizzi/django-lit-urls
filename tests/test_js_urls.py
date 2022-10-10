import unittest

from django_lit_urls.serializer import UrlModel, UrlModels
from django_lit_urls.utils import _url_to_js_func


class UrlParserTestCase(unittest.TestCase):
    def test_url_patterns(self):
        """
        Check that "URL patterns" resolve correctly into a
        string-literal-compatible string and descriptive variable names
        """

        # A URL with no params
        self.assertEqual(_url_to_js_func("en/"), ("en/", ()))

        # A URL with a newer style 'path' param
        self.assertEqual(
            _url_to_js_func(r"editor/activity-manager/<slug:org_id>/"),
            (r"editor/activity-manager/${org_id}/", ("org_id",)),
        )
        self.assertEqual(_url_to_js_func(r"<path:object_id>/"), (r"${object_id}/", ("object_id",)))

        # Older `url` style params
        self.assertEqual(_url_to_js_func(r"media/(?P<path>.*)"), (r"media/${path}", ("path",)))
        self.assertEqual(
            _url_to_js_func(r"password/reset/confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>.+)/"),
            (r"password/reset/confirm/${uidb64}/${token}/", ("uidb64", "token")),
        )
        self.assertEqual(
            _url_to_js_func(r"activity/(?P<activity_pk>[\w-]+)/endorsement/(?P<org_pk>[\/\&\|\?]+)/"),
            (
                r"activity/${activity_pk}/endorsement/${org_pk}/",
                ("activity_pk", "org_pk"),
            ),
        )

        # Positional arguments are replaced with `v_x`
        self.assertEqual(
            _url_to_js_func(r"activity/(?:[\w-]*\/{0,1})api/"),
            (r"activity/${v_1}api/", ("v_1",)),
        )


class UrlModelTestCase(unittest.TestCase):
    def test_url_model(self):
        """
        Check that the various rendering properties
        work correctly on a UrlModel instance
        """

        test_case = UrlModel(
            pattern_name="village-court-detail",
            namespace="",
            url_parts=("/", "en/", "dims/", r"village-court/${pk}/"),
            js_vars=("pk",),
            url_lookup="location_profile.views.VillageCourtViewSet",
            is_alternative=False,
        )

        self.assertEqual(test_case.js_func_name, "villageCourtDetail")
        self.assertEqual(
            test_case.as_class_prop,
            "villageCourtDetail (pk) { return `/en/dims/village-court/${pk}/` }",
        )
        self.assertEqual(
            test_case.as_arrow_func,
            "villageCourtDetail = (pk) => `/en/dims/village-court/${pk}/`;",
        )
        self.assertEqual(
            test_case.as_arrow_func_property,
            "villageCourtDetail: (pk) => `/en/dims/village-court/${pk}/`",
        )
        self.assertEqual(
            test_case.as_function,
            "function villageCourtDetail(pk){ return `/en/dims/village-court/${pk}/` }",
        )

        self.assertEqual(
            test_case.as_map_setter,
            '"villageCourtDetail", (pk) => new URL(`/en/dims/village-court/${pk}/`, location.origin))',
        )


class UrlModelsTestCase(unittest.TestCase):
    """
    Tests the functions representing a group of UrlModels
    """

    def setUp(self) -> None:
        self.test_case = UrlModels(
            urls=[
                UrlModel(
                    pattern_name="village-court-detail",
                    namespace="",
                    url_parts=("/", "en/", "dims/", r"village-court/${pk}/"),
                    js_vars=("pk",),
                    url_lookup="location_profile.views.VillageCourtViewSet",
                    is_alternative=False,
                )
            ]
        )
        return super().setUp()

    def test_map(self):
        self.assertEqual(
            self.test_case.as_map,
            'const urls = new Map(\n    ["villageCourtDetail", (pk) => new URL(`/en/dims/village-court/${pk}/`, location.origin)]\n)',
        )
