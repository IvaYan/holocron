"""Metadata processor test suite."""

import os

import pytest

from holocron import app, content
from holocron.ext.processors import metadata


def _get_document(cls=content.Document, **kwargs):
    document = cls(app.Holocron({}))
    document.update(kwargs)
    return document


@pytest.fixture(scope='function')
def testapp():
    return app.Holocron({})


def test_document(testapp):
    """Metadata processor has to work!"""

    documents = metadata.process(
        testapp,
        [
            _get_document(content='the Force', author='skywalker'),
        ],
        metadata={
            'author': 'yoda',
            'type': 'memoire',
        })

    assert len(documents) == 1

    assert documents[0]['content'] == 'the Force'
    assert documents[0]['author'] == 'yoda'
    assert documents[0]['type'] == 'memoire'


def test_document_untouched(testapp):
    """Metadata processor has to ignore documents if metadata isn't passed."""

    documents = metadata.process(
        testapp,
        [
            _get_document(content='the Force', author='skywalker'),
        ])

    assert len(documents) == 1

    assert documents[0]['content'] == 'the Force'
    assert documents[0]['author'] == 'skywalker'


@pytest.mark.parametrize('overwrite, author', [
    (True, 'yoda'),
    (False, 'skywalker'),
])
def test_document_overwrite(testapp, overwrite, author):
    """Metadata processor has to respect overwrite option."""

    documents = metadata.process(
        testapp,
        [
            _get_document(content='the Force', author='skywalker'),
        ],
        metadata={
            'author': 'yoda',
            'type': 'memoire',
        },
        overwrite=overwrite)

    assert len(documents) == 1

    assert documents[0]['content'] == 'the Force'
    assert documents[0]['author'] == author
    assert documents[0]['type'] == 'memoire'


def test_documents(testapp):
    """Metadata processor has to ignore non-targeted documents."""

    documents = metadata.process(
        testapp,
        [
            _get_document(
                content='the way of the Force #1',
                source=os.path.join('posts', '1.md')),
            _get_document(
                content='the way of the Force #2',
                source=os.path.join('pages', '2.md')),
            _get_document(
                content='the way of the Force #3',
                source=os.path.join('posts', '3.md')),
            _get_document(
                content='the way of the Force #4',
                source=os.path.join('pages', '4.md')),
        ],
        metadata={
            'author': 'kenobi',
        },
        when=[
            {
                'operator': 'match',
                'attribute': 'source',
                'pattern': r'^posts.*$',
            },
        ])

    assert len(documents) == 4

    assert documents[0]['content'] == 'the way of the Force #1'
    assert documents[0]['source'] == os.path.join('posts', '1.md')
    assert documents[0]['author'] == 'kenobi'

    assert documents[1]['content'] == 'the way of the Force #2'
    assert documents[1]['source'] == os.path.join('pages', '2.md')
    assert 'author' not in documents[1]

    assert documents[2]['content'] == 'the way of the Force #3'
    assert documents[2]['source'] == os.path.join('posts', '3.md')
    assert documents[2]['author'] == 'kenobi'

    assert documents[3]['content'] == 'the way of the Force #4'
    assert documents[3]['source'] == os.path.join('pages', '4.md')
    assert 'author' not in documents[3]
