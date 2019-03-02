"""Core factories test suite."""

import holocron.core


def test_create_app_processors_discover():
    """Processors must be discovered and setup."""

    testapp = holocron.core.create_app({})

    assert set(testapp._processors) == {
        "archive",
        "commit",
        "feed",
        "frontmatter",
        "jinja2",
        "markdown",
        "metadata",
        "pipe",
        "prettyuri",
        "restructuredtext",
        "sitemap",
        "source",
        "todatetime",
        "when",
    }


def test_create_app_processors_pass(caplog):
    """Passed processors must be setup."""

    marker = None

    def processor(app, items):
        nonlocal marker
        marker = 13
        yield from items

    testapp = holocron.core.create_app({}, processors={"test": processor})

    for _ in testapp.invoke([{"name": "test"}], []):
        pass

    assert marker == 13


def test_create_app_processors_pass_precedence(caplog):
    """Passed processors must have greater precedence."""

    marker = None
    name = "archive"

    def processor(app, items):
        nonlocal marker
        marker = 13
        yield from items

    testapp = holocron.core.create_app({}, processors={name: processor})
    assert name in testapp._processors

    for _ in testapp.invoke([{"name": "archive"}], []):
        pass

    assert marker == 13

    # Ensure a processor has indeed been overridden. Otherwise, the test cannot
    # be used to prove that passed processors have greater precedence.
    assert len(caplog.records) == 1
    assert caplog.records[0].message == "processor override: '%s'" % name


def test_create_app_pipes_discover():
    """Pipes must be discovered and setup."""

    testapp = holocron.core.create_app({})

    assert set(testapp._pipes) == set()


def test_create_app_pipes_pass():
    """Passed pipes must be setup."""

    pipe = [{"name": "markdown"}]
    item = holocron.core.Item(content="**text**", destination="1.md")

    testapp = holocron.core.create_app({}, pipes={"test": pipe})

    for processed in testapp.invoke("test", [item]):
        assert processed["content"] == "<p><strong>text</strong></p>"
        assert processed["destination"] == "1.html"
