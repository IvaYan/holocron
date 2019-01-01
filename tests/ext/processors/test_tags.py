"""Tags processor test suite."""

import os
import datetime

import pytest

from holocron import app, content
from holocron.ext.processors import tags


def _get_document(**kwargs):
    document = content.Document(app.Holocron({}))
    document.update(kwargs)
    return document


@pytest.fixture(scope='function')
def testapp():
    instance = app.Holocron({})
    return instance


def test_document(testapp):
    """Tags processor has to work!"""

    documents = tags.process(
        testapp,
        [
            _get_document(
                title='the way of the Force',
                destination=os.path.join('posts', '1.html'),
                published=datetime.date(2017, 10, 4),
                tags=['kenobi', 'skywalker']),
        ])

    assert len(documents) == 3

    assert documents[0]['title'] == 'the way of the Force'
    assert documents[0]['destination'] == os.path.join('posts', '1.html')
    assert documents[0]['published'] == datetime.date(2017, 10, 4)

    assert documents[1]['source'] == 'virtual://tags/kenobi'
    assert documents[1]['destination'] == 'tags/kenobi.html'
    assert documents[1]['template'] == 'index.j2'
    assert documents[1]['documents'] == [documents[0]]

    assert documents[2]['source'] == 'virtual://tags/skywalker'
    assert documents[2]['destination'] == 'tags/skywalker.html'
    assert documents[2]['template'] == 'index.j2'
    assert documents[2]['documents'] == [documents[0]]


def test_documents_cross_tags(testapp):
    """Tags processor has to group tags"""

    documents = tags.process(
        testapp,
        [
            _get_document(
                title='the way of the Force #1',
                destination=os.path.join('posts', '1.html'),
                published=datetime.date(2017, 10, 1),
                tags=['kenobi', 'skywalker']),
            _get_document(
                title='the way of the Force #2',
                destination=os.path.join('posts', '2.html'),
                published=datetime.date(2017, 10, 2),
                tags=['yoda', 'skywalker']),
        ])

    assert len(documents) == 5

    assert documents[0]['title'] == 'the way of the Force #1'
    assert documents[0]['destination'] == os.path.join('posts', '1.html')
    assert documents[0]['published'] == datetime.date(2017, 10, 1)

    assert documents[1]['title'] == 'the way of the Force #2'
    assert documents[1]['destination'] == os.path.join('posts', '2.html')
    assert documents[1]['published'] == datetime.date(2017, 10, 2)

    assert documents[2]['source'] == 'virtual://tags/kenobi'
    assert documents[2]['destination'] == 'tags/kenobi.html'
    assert documents[2]['template'] == 'index.j2'
    assert documents[2]['documents'] == [documents[0]]

    assert documents[3]['source'] == 'virtual://tags/skywalker'
    assert documents[3]['destination'] == 'tags/skywalker.html'
    assert documents[3]['template'] == 'index.j2'
    assert documents[3]['documents'] == [documents[0], documents[1]]

    assert documents[4]['source'] == 'virtual://tags/yoda'
    assert documents[4]['destination'] == 'tags/yoda.html'
    assert documents[4]['template'] == 'index.j2'
    assert documents[4]['documents'] == [documents[1]]


def test_param_template(testapp):
    """Tags processor has to respect template parameter."""

    documents = tags.process(
        testapp,
        [
            _get_document(
                title='the way of the Force',
                destination=os.path.join('posts', '1.html'),
                published=datetime.date(2017, 10, 4),
                tags=['kenobi']),
        ],
        template='foobar.txt')

    assert len(documents) == 2

    assert documents[0]['title'] == 'the way of the Force'
    assert documents[0]['destination'] == os.path.join('posts', '1.html')
    assert documents[0]['published'] == datetime.date(2017, 10, 4)

    assert documents[1]['source'] == 'virtual://tags/kenobi'
    assert documents[1]['destination'] == 'tags/kenobi.html'
    assert documents[1]['template'] == 'foobar.txt'
    assert documents[1]['documents'] == [documents[0]]


def test_param_output(testapp):
    """Tags processor has to respect output parameter."""

    documents = tags.process(
        testapp,
        [
            _get_document(
                title='the way of the Force',
                destination=os.path.join('posts', '1.html'),
                published=datetime.date(2017, 10, 4),
                tags=['kenobi', 'skywalker']),
        ],
        output='mytags/{tag}/index.html')

    assert len(documents) == 3

    assert documents[0]['title'] == 'the way of the Force'
    assert documents[0]['destination'] == os.path.join('posts', '1.html')
    assert documents[0]['published'] == datetime.date(2017, 10, 4)

    assert documents[1]['source'] == 'virtual://tags/kenobi'
    assert documents[1]['destination'] == 'mytags/kenobi/index.html'
    assert documents[1]['template'] == 'index.j2'
    assert documents[1]['documents'] == [documents[0]]

    assert documents[2]['source'] == 'virtual://tags/skywalker'
    assert documents[2]['destination'] == 'mytags/skywalker/index.html'
    assert documents[2]['template'] == 'index.j2'
    assert documents[2]['documents'] == [documents[0]]


def test_param_when(testapp):
    """Tags processor has to ignore non-relevant documents."""

    documents = tags.process(
        testapp,
        [
            _get_document(
                title='the way of the Force #1',
                source=os.path.join('posts', '1.md'),
                destination=os.path.join('posts', '1.html'),
                published=datetime.date(2017, 10, 1),
                tags=['kenobi']),
            _get_document(
                title='the way of the Force #2',
                source=os.path.join('pages', '2.md'),
                destination=os.path.join('pages', '2.html'),
                published=datetime.date(2017, 10, 2),
                tags=['kenobi']),
            _get_document(
                title='the way of the Force #3',
                source=os.path.join('posts', '3.md'),
                destination=os.path.join('posts', '3.html'),
                published=datetime.date(2017, 10, 3),
                tags=['kenobi']),
            _get_document(
                title='the way of the Force #4',
                source=os.path.join('pages', '4.md'),
                destination=os.path.join('pages', '4.html'),
                published=datetime.date(2017, 10, 4),
                tags=['kenobi']),
        ],
        when=[
            {
                'operator': 'match',
                'attribute': 'source',
                'pattern': r'^posts.*$',
            },
        ])

    assert len(documents) == 5

    for i, document in enumerate(documents[:-1]):
        assert document['source'].endswith('%d.md' % (i + 1))
        assert document['title'] == 'the way of the Force #%d' % (i + 1)
        assert document['published'] == datetime.date(2017, 10, i + 1)

    assert documents[-1]['source'] == 'virtual://tags/kenobi'
    assert documents[-1]['destination'] == 'tags/kenobi.html'
    assert documents[-1]['template'] == 'index.j2'
    assert documents[-1]['documents'] == [documents[0], documents[2]]


@pytest.mark.parametrize('params, error', [
    ({'when': 42}, 'when: unsupported value'),
    ({'template': 42}, "template: 42 should be instance of 'str'"),
    ({'output': 42}, "output: 42 should be instance of 'str'"),
])
def test_param_bad_value(testapp, params, error):
    """Tags processor has to validate input parameters."""

    with pytest.raises(ValueError, match=error):
        tags.process(testapp, [], **params)
