"""Prettyuri processor test suite."""

import os

import pytest

from holocron import app, content
from holocron.ext.processors import prettyuri


def _get_document(**kwargs):
    document = content.Document(app.Holocron({}))
    document.update(kwargs)
    return document


@pytest.fixture(scope='function')
def testapp():
    return app.Holocron()


def test_document(testapp):
    """Prettyuri processor has to work!"""

    documents = prettyuri.process(
        testapp,
        [
            _get_document(destination='about/cv.html'),
        ])

    assert len(documents) == 1
    assert documents[0]['destination'] == 'about/cv/index.html'


@pytest.mark.parametrize('index', [
    'index.html',
    'index.htm',
])
def test_document_index(testapp, index):
    """Prettyuri processor has to ignore index documents."""

    documents = prettyuri.process(
        testapp,
        [
            _get_document(destination=os.path.join('about', 'cv', index)),
        ])

    assert len(documents) == 1
    assert documents[0]['destination'] == os.path.join('about', 'cv', index)


def test_param_when(testapp):
    """Prettyuri processor has to ignore non-targeted documents."""

    documents = prettyuri.process(
        testapp,
        [
            _get_document(source='0.txt', destination='0.txt'),
            _get_document(source='1.md', destination='1/index.html'),
            _get_document(source='2', destination='2.html'),
            _get_document(source='3.markdown', destination='3.html'),
        ],
        when=[
            {
                'operator': 'match',
                'attribute': 'source',
                'pattern': r'.*\.(markdown|mdown|mkd|mdwn|md)$',
            },
        ])

    assert len(documents) == 4
    assert documents[0]['destination'] == '0.txt'
    assert documents[1]['destination'] == '1/index.html'
    assert documents[2]['destination'] == '2.html'
    assert documents[3]['destination'] == '3/index.html'


@pytest.mark.parametrize('params, error', [
    ({'when': [42]}, 'when: unsupported value'),
])
def test_param_bad_value(testapp, params, error):
    """Prettyuri processor has to validate input parameters."""

    with pytest.raises(ValueError, match=error):
        prettyuri.process(testapp, [], **params)
