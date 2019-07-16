"""Jinja2 processor test suite."""

import collections.abc
import os
import textwrap
import unittest.mock

import pytest
import bs4

from holocron import core
from holocron.processors import jinja2


@pytest.fixture(scope="function")
def testapp():
    return core.Application({"url": "https://yoda.ua"})


def test_item(testapp):
    """Jinja2 processor has to work!"""

    stream = jinja2.process(
        testapp,
        [core.Item({"title": "History of the Force", "content": "the Force"})],
    )
    assert isinstance(stream, collections.abc.Iterable)

    items = list(stream)
    assert items[:1] == [
        core.Item(
            {"title": "History of the Force", "content": unittest.mock.ANY}
        )
    ]

    soup = bs4.BeautifulSoup(items[0]["content"], "html.parser")
    assert soup.meta["charset"] == "UTF-8"
    assert soup.article.header.h1.string == "History of the Force"
    assert list(soup.article.stripped_strings)[1] == "the Force"

    # Since we don't know in which order statics are discovered, we sort them
    # so we can avoid possible flakes.
    static = sorted(items[1:], key=lambda d: d["source"])
    assert static[0]["source"] == os.path.join("static", "logo.svg")
    assert static[0]["destination"] == static[0]["source"]
    assert static[1]["source"] == os.path.join("static", "pygments.css")
    assert static[1]["destination"] == static[1]["source"]
    assert static[2]["source"] == os.path.join("static", "style.css")
    assert static[2]["destination"] == static[2]["source"]
    assert len(static) == 3


def test_item_template(testapp, tmpdir):
    """Jinja2 processor has to respect item suggested template."""

    tmpdir.ensure("theme_a", "templates", "holiday.j2").write_text(
        textwrap.dedent(
            """\
            template: my super template
            rendered: {{ item.title }}
        """
        ),
        encoding="UTF-8",
    )

    stream = jinja2.process(
        testapp,
        [
            core.Item(
                {
                    "title": "History of the Force",
                    "content": "the Force",
                    "template": "holiday.j2",
                }
            )
        ],
        themes=[tmpdir.join("theme_a").strpath],
    )

    assert isinstance(stream, collections.abc.Iterable)
    assert list(stream) == [
        core.Item(
            {
                "title": "History of the Force",
                "template": "holiday.j2",
                "content": textwrap.dedent(
                    """\
                    template: my super template
                    rendered: History of the Force"""
                ),
            }
        )
    ]


@pytest.mark.parametrize(
    ["amount"],
    [
        pytest.param(0),
        pytest.param(1),
        pytest.param(2),
        pytest.param(5),
        pytest.param(10),
    ],
)
def test_item_many(testapp, tmpdir, amount):
    """Jinja2 processor has to work with stream."""

    stream = jinja2.process(
        testapp,
        [
            core.Item(
                {
                    "title": "History of the Force",
                    "content": "the Force #%d" % i,
                }
            )
            for i in range(amount)
        ],
    )
    assert isinstance(stream, collections.abc.Iterable)
    items = list(stream)

    assert (
        items[:amount]
        == [
            core.Item(
                {"title": "History of the Force", "content": unittest.mock.ANY}
            )
        ]
        * amount
    )

    for i, item in enumerate(items[:amount]):
        soup = bs4.BeautifulSoup(item["content"], "html.parser")
        assert soup.meta["charset"] == "UTF-8"
        assert soup.article.header.h1.string == "History of the Force"
        assert list(soup.article.stripped_strings)[1] == "the Force #%d" % i

    # Since we don't know in which order statics are discovered, we sort them
    # so we can avoid possible flakes.
    static = sorted(items[amount:], key=lambda d: d["source"])
    assert static[0]["source"] == os.path.join("static", "logo.svg")
    assert static[0]["destination"] == static[0]["source"]
    assert static[1]["source"] == os.path.join("static", "pygments.css")
    assert static[1]["destination"] == static[1]["source"]
    assert static[2]["source"] == os.path.join("static", "style.css")
    assert static[2]["destination"] == static[2]["source"]
    assert len(static) == 3


def test_param_themes(testapp, tmpdir):
    """Jinja2 processor has to respect themes parameter."""

    tmpdir.ensure("theme_a", "templates", "item.j2").write_text(
        textwrap.dedent(
            """\
            template: my super template
            rendered: {{ item.title }}
        """
        ),
        encoding="UTF-8",
    )

    tmpdir.ensure("theme_a", "static", "style.css").write_text(
        "article { margin: 0 }", encoding="UTF-8"
    )

    stream = jinja2.process(
        testapp,
        [core.Item({"title": "History of the Force", "content": "the Force"})],
        themes=[tmpdir.join("theme_a").strpath],
    )

    assert isinstance(stream, collections.abc.Iterable)
    assert list(stream) == [
        core.Item(
            {
                "title": "History of the Force",
                "content": textwrap.dedent(
                    """\
                    template: my super template
                    rendered: History of the Force"""
                ),
            }
        ),
        core.WebSiteItem(
            {
                "content": "article { margin: 0 }",
                "source": os.path.join("static", "style.css"),
                "destination": os.path.join("static", "style.css"),
                "created": unittest.mock.ANY,
                "updated": unittest.mock.ANY,
                "baseurl": testapp.metadata["url"],
            }
        ),
    ]


def test_param_themes_two_themes(testapp, tmpdir):
    """Jinja2 processor has to respect themes parameter."""

    tmpdir.ensure("theme_a", "templates", "page.j2").write_text(
        textwrap.dedent(
            """\
            template: my super template from theme_a
            rendered: {{ item.title }}
        """
        ),
        encoding="UTF-8",
    )

    tmpdir.ensure("theme_b", "templates", "page.j2").write_text(
        textwrap.dedent(
            """\
            template: my super template from theme_b
            rendered: {{ item.title }}
        """
        ),
        encoding="UTF-8",
    )

    tmpdir.ensure("theme_b", "templates", "holiday.j2").write_text(
        textwrap.dedent(
            """\
            template: my holiday template from theme_b
            rendered: {{ item.title }}
        """
        ),
        encoding="UTF-8",
    )

    stream = jinja2.process(
        testapp,
        [
            core.Item(
                {
                    "title": "History of the Force",
                    "content": "the Force",
                    "template": "page.j2",
                }
            ),
            core.Item(
                {
                    "title": "History of the Force",
                    "content": "the Force",
                    "template": "holiday.j2",
                }
            ),
        ],
        themes=[
            tmpdir.join("theme_a").strpath,
            tmpdir.join("theme_b").strpath,
        ],
    )

    assert isinstance(stream, collections.abc.Iterable)
    assert list(stream) == [
        core.Item(
            {
                "title": "History of the Force",
                "template": "page.j2",
                "content": textwrap.dedent(
                    """\
                    template: my super template from theme_a
                    rendered: History of the Force"""
                ),
            }
        ),
        core.Item(
            {
                "title": "History of the Force",
                "template": "holiday.j2",
                "content": textwrap.dedent(
                    """\
                    template: my holiday template from theme_b
                    rendered: History of the Force"""
                ),
            }
        ),
    ]


@pytest.mark.parametrize(
    ["params", "error"],
    [
        pytest.param(
            {"template": 42},
            "template: 42 is not of type 'string'",
            id="template-int",
        ),
        pytest.param(
            {"context": 42},
            "context: 42 is not of type 'object'",
            id="context-int",
        ),
        pytest.param(
            {"themes": {"foo": 1}},
            "themes: {'foo': 1} is not of type 'array'",
            id="themes-dict",
        ),
    ],
)
def test_param_bad_value(testapp, params, error):
    """Commit processor has to validate input parameters."""

    with pytest.raises(ValueError) as excinfo:
        next(jinja2.process(testapp, [], **params))
    assert str(excinfo.value) == error
