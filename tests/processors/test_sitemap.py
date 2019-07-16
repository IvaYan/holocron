"""Sitemap processor test suite."""

import collections.abc
import datetime
import gzip
import itertools
import os
import unittest.mock

import pytest
import xmltodict

from holocron import core
from holocron.processors import sitemap


class _pytest_xmlasdict:
    """Assert that a given XML has the same semantic meaning."""

    def __init__(self, expected, ungzip=False):
        self._expected = expected
        self._ungzip = ungzip

    def __eq__(self, actual):
        if self._ungzip:
            actual = gzip.decompress(actual)
        actual = xmltodict.parse(actual, "UTF-8")
        return self._expected == actual

    def __repr__(self):
        return self._expected


@pytest.fixture(scope="function")
def testapp():
    return core.Application({"url": "https://yoda.ua"})


@pytest.mark.parametrize(
    ["filename", "escaped"],
    [
        pytest.param("s.html", "s.html"),
        pytest.param("ы.html", "%D1%8B.html"),
        pytest.param("a&b.html", "a%26b.html"),
        pytest.param("a<b.html", "a%3Cb.html"),
        pytest.param("a>b.html", "a%3Eb.html"),
        pytest.param('a"b.html', "a%22b.html"),
        pytest.param("a'b.html", "a%27b.html"),
    ],
)
def test_item(testapp, filename, escaped):
    """Sitemap processor has to work!"""

    timepoint = datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc)
    stream = sitemap.process(
        testapp,
        [
            core.WebSiteItem(
                {
                    "destination": filename,
                    "updated": timepoint,
                    "baseurl": testapp.metadata["url"],
                }
            )
        ],
    )

    assert isinstance(stream, collections.abc.Iterable)
    assert list(stream) == [
        core.WebSiteItem(
            {
                "destination": filename,
                "updated": timepoint,
                "baseurl": testapp.metadata["url"],
            }
        ),
        core.WebSiteItem(
            {
                "source": "sitemap://sitemap.xml",
                "destination": "sitemap.xml",
                "content": _pytest_xmlasdict(
                    {
                        "urlset": {
                            "@xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9",
                            "url": {
                                "loc": "https://yoda.ua/" + escaped,
                                "lastmod": "1970-01-01T00:00:00+00:00",
                            },
                        }
                    }
                ),
                "baseurl": testapp.metadata["url"],
            }
        ),
    ]


@pytest.mark.parametrize(
    ["amount"],
    [
        # pytest.param(0),
        # pytest.param(1),
        pytest.param(2),
        pytest.param(5),
        pytest.param(10),
    ],
)
def test_item_many(testapp, amount):
    """Sitemap processor has to work with stream."""

    timepoint = datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc)
    stream = sitemap.process(
        testapp,
        [
            core.WebSiteItem(
                {
                    "destination": str(i),
                    "updated": timepoint,
                    "baseurl": testapp.metadata["url"],
                }
            )
            for i in range(amount)
        ],
    )

    assert isinstance(stream, collections.abc.Iterable)
    assert list(stream) == list(
        itertools.chain(
            [
                core.WebSiteItem(
                    {
                        "destination": str(i),
                        "updated": timepoint,
                        "baseurl": testapp.metadata["url"],
                    }
                )
                for i in range(amount)
            ],
            [
                core.WebSiteItem(
                    {
                        "source": "sitemap://sitemap.xml",
                        "destination": "sitemap.xml",
                        "content": _pytest_xmlasdict(
                            {
                                "urlset": {
                                    "@xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9",
                                    "url": [
                                        {
                                            "loc": "https://yoda.ua/%d" % i,
                                            "lastmod": "1970-01-01T00:00:00+00:00",
                                        }
                                        for i in range(amount)
                                    ],
                                }
                            }
                        ),
                        "baseurl": testapp.metadata["url"],
                    }
                )
            ],
        )
    )


def test_param_gzip(testapp):
    """Sitemap processor has to respect gzip parameter."""

    timepoint = datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc)
    stream = sitemap.process(
        testapp,
        [
            core.WebSiteItem(
                {
                    "destination": "1.html",
                    "updated": timepoint,
                    "baseurl": testapp.metadata["url"],
                }
            )
        ],
        gzip=True,
    )

    assert isinstance(stream, collections.abc.Iterable)
    assert list(stream) == [
        core.WebSiteItem(
            {
                "destination": "1.html",
                "updated": timepoint,
                "baseurl": testapp.metadata["url"],
            }
        ),
        core.WebSiteItem(
            {
                "source": "sitemap://sitemap.xml.gz",
                "destination": "sitemap.xml.gz",
                "content": _pytest_xmlasdict(
                    {
                        "urlset": {
                            "@xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9",
                            "url": {
                                "loc": "https://yoda.ua/1.html",
                                "lastmod": "1970-01-01T00:00:00+00:00",
                            },
                        }
                    },
                    ungzip=True,
                ),
                "baseurl": testapp.metadata["url"],
            }
        ),
    ]


@pytest.mark.parametrize(
    ["save_as"],
    [
        pytest.param(os.path.join("posts", "skywalker.luke"), id="deep"),
        pytest.param(os.path.join("yoda.jedi"), id="flat"),
    ],
)
def test_param_save_as(testapp, save_as):
    """Sitemap processor has to respect save_as parameter."""

    timepoint = datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc)
    stream = sitemap.process(
        testapp,
        [
            core.WebSiteItem(
                {
                    "destination": os.path.join("posts", "1.html"),
                    "updated": timepoint,
                    "baseurl": testapp.metadata["url"],
                }
            )
        ],
        save_as=save_as,
    )

    assert isinstance(stream, collections.abc.Iterable)
    assert list(stream) == [
        core.WebSiteItem(
            {
                "destination": os.path.join("posts", "1.html"),
                "updated": timepoint,
                "baseurl": testapp.metadata["url"],
            }
        ),
        core.WebSiteItem(
            {
                "source": "sitemap://%s" % save_as,
                "destination": save_as,
                "content": unittest.mock.ANY,
                "baseurl": testapp.metadata["url"],
            }
        ),
    ]


@pytest.mark.parametrize(
    ["document_path", "sitemap_path"],
    [
        pytest.param(os.path.join("1.html"), os.path.join("b", "sitemap.xml")),
        pytest.param(
            os.path.join("a", "1.html"), os.path.join("b", "sitemap.xml")
        ),
        pytest.param(
            os.path.join("a", "1.html"), os.path.join("a", "c", "sitemap.xml")
        ),
        pytest.param(
            os.path.join("ab", "1.html"), os.path.join("a", "sitemap.xml")
        ),
    ],
)
def test_param_save_as_unsupported(testapp, document_path, sitemap_path):
    """Sitemap process has to check enlisted URLs for compatibility."""

    timepoint = datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc)
    stream = sitemap.process(
        testapp,
        [
            core.WebSiteItem(
                {
                    "destination": document_path,
                    "updated": timepoint,
                    "baseurl": testapp.metadata["url"],
                }
            )
        ],
        save_as=sitemap_path,
    )

    assert isinstance(stream, collections.abc.Iterable)

    with pytest.raises(ValueError) as excinfo:
        next(stream)

    excinfo.match(
        "The location of a Sitemap file determines the set of URLs "
        "that can be included in that Sitemap. A Sitemap file located "
        "at .* can include any URLs starting with .* but can not "
        "include .*."
    )


@pytest.mark.parametrize(
    ["pretty", "lines"], [pytest.param(False, 1), pytest.param(True, 7)]
)
def test_param_pretty(testapp, pretty, lines):
    """Sitemap processor has to respect pretty parameter."""

    timepoint = datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc)
    stream = sitemap.process(
        testapp,
        [
            core.WebSiteItem(
                {
                    "destination": "1.html",
                    "updated": timepoint,
                    "baseurl": testapp.metadata["url"],
                }
            )
        ],
        pretty=pretty,
    )

    assert isinstance(stream, collections.abc.Iterable)

    items = list(stream)
    assert items == [
        core.WebSiteItem(
            {
                "destination": "1.html",
                "updated": timepoint,
                "baseurl": testapp.metadata["url"],
            }
        ),
        core.WebSiteItem(
            {
                "source": "sitemap://sitemap.xml",
                "destination": "sitemap.xml",
                "content": unittest.mock.ANY,
                "baseurl": testapp.metadata["url"],
            }
        ),
    ]
    assert len(items[-1]["content"].splitlines()) == lines


@pytest.mark.parametrize(
    ["params", "error"],
    [
        pytest.param(
            {"gzip": "true"},
            "gzip: 'true' is not of type 'boolean'",
            id="gzip-str",
        ),
        pytest.param(
            {"save_as": 42},
            "save_as: 42 is not of type 'string'",
            id="save_as-int",
        ),
        pytest.param(
            {"pretty": "true"},
            "pretty: 'true' is not of type 'boolean'",
            id="pretty-str",
        ),
    ],
)
def test_param_bad_value(testapp, params, error):
    """Sitemap processor has to validate input parameters."""

    with pytest.raises(ValueError) as excinfo:
        next(sitemap.process(testapp, [], **params))
    assert str(excinfo.value) == error
