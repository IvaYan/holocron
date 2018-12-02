"""Source processor test suite."""

import os
import datetime

import pytest

from holocron import app, content
from holocron.ext.processors import source


@pytest.fixture(scope='function')
def testapp():
    instance = app.Holocron({})
    return instance


@pytest.mark.parametrize('path, cls', [
    (['about', 'cv.pdf'], content.Document),
    (['2017', '09', '17', 'cv.pdf'], content.Document),
])
def test_document(testapp, tmpdir, path, cls):
    """Source processor has to work."""

    tmpdir.ensure(*path).write_text('text', encoding='utf-8')

    preserved = content.Document(testapp)
    preserved['source'] = os.path.join('images', 'me.png')
    preserved['destination'] = os.path.join('images', 'me.png')

    documents = source.process(
        testapp,
        [
            preserved,
        ],
        path=tmpdir.strpath)

    assert len(documents) == 2

    assert documents[0]['source'] == os.path.join('images', 'me.png')
    assert documents[0]['destination'] == os.path.join('images', 'me.png')

    assert isinstance(documents[1], cls)
    assert documents[1]['source'] == os.path.join(*path)
    assert documents[1]['destination'] == os.path.join(*path)
    assert documents[1]['created'].timestamp() \
        == pytest.approx(tmpdir.join(*path).stat().ctime, 0.00001)
    assert documents[1]['updated'].timestamp() \
        == pytest.approx(tmpdir.join(*path).stat().mtime, 0.00001)
    assert documents[1]['content'] == 'text'

    if path[0] == '2017':
        assert documents[1]['published'] == datetime.date(2017, 9, 17)

        if path[3].endswith('.md'):
            assert isinstance(documents[1], content.Post)


@pytest.mark.parametrize('data, cls', [
    (u'text', str),
    (b'\xf1', bytes),
])
def test_document_content_types(testapp, tmpdir, data, cls):
    """Source processor has to properly read documents' content."""

    localpath = tmpdir.ensure('cv.md')

    if isinstance(data, bytes):
        localpath.write_binary(data)
    else:
        localpath.write_text(data, encoding='utf-8')

    documents = source.process(testapp, [], path=tmpdir.strpath)
    assert documents[0]['content'] == data
    assert isinstance(documents[0]['content'], cls)


@pytest.mark.parametrize('timezone, tznames', [
    ('UTC', ['UTC']),
    ('Europe/Kiev', ['EET', 'EEST']),
])
def test_timezone(testapp, tmpdir, timezone, tznames):
    tmpdir.ensure('cv.md').write_text('text', encoding='utf-8')

    documents = source.process(
        testapp,
        [],
        path=tmpdir.strpath,
        timezone=timezone)

    created = documents[0]['created']
    updated = documents[0]['updated']

    assert created.tzinfo.tzname(created) in tznames
    assert updated.tzinfo.tzname(updated) in tznames


def test_timezone_in_action(testapp, tmpdir):
    tmpdir.ensure('cv.md').write_text('text', encoding='utf-8')

    created_utc = source.process(
        testapp, [], path=tmpdir.strpath, timezone='UTC')[0]['created']
    created_kie = source.process(
        testapp, [], path=tmpdir.strpath, timezone='Europe/Kiev')[0]['created']

    assert created_kie.tzinfo.utcoffset(created_kie) \
        >= created_utc.tzinfo.utcoffset(created_utc)
    assert created_kie.isoformat() > created_utc.isoformat()
    assert created_kie.isoformat().split('+')[-1] in ('02:00', '03:00')


def test_documents(testapp, tmpdir):
    """Source processor has to ignore non-matched documents."""

    structure = sorted([
        ['2017', '09', '20', 'the-force.md'],
        ['2017', '09', '20', 'yoda.jpg'],
        ['about', 'index.md'],
        ['about', 'me.png'],
        ['cv.pdf'],
    ])

    for path in structure:
        tmpdir.ensure(*path)
    tmpdir.ensure('_config.yml')

    documents = source.process(
        testapp,
        [],
        path=tmpdir.strpath,
        when=[
            {
                'operator': 'match',
                'attribute': 'source',
                'pattern': r'^(?!_).*$',
            },
        ])
    documents = sorted(documents, key=lambda document: document['source'])

    for document, path in zip(documents, structure):
        assert document['source'] == os.path.join(*path)
        assert document['destination'] == os.path.join(*path)
        assert document['created'].timestamp() \
            == pytest.approx(tmpdir.join(*path).stat().ctime, 0.00001)
        assert document['updated'].timestamp() \
            == pytest.approx(tmpdir.join(*path).stat().mtime, 0.00001)


@pytest.mark.parametrize('options, error', [
    ({'path': 42}, "path: 42 should be instance of 'str'"),
    ({'when': 42}, 'when: unsupported value'),
    ({'encoding': 'UTF-42'}, 'encoding: unsupported encoding'),
    ({'timezone': 'Europe/Kharkiv'}, 'timezone: unsupported timezone'),
])
def test_parameters_schema(testapp, options, error):
    with pytest.raises(ValueError, match=error):
        source.process(testapp, [], **options)
