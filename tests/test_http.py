from dataclasses import dataclass
from unittest import TestCase
from unittest.mock import MagicMock

from monocat._http import ContentType, WebLink, WebLinkHeader


class TestContentType(TestCase):
    def test_from_response(self):
        @dataclass
        class SubTest:
            content_type: str
            expected: ContentType

        subtests = [
            SubTest('text/plain', ContentType(type='text', subtype='plain')),
            SubTest('application/json', ContentType(type='application', subtype='json')),
            SubTest('application/json; charset=UTF-8', ContentType(type='application', subtype='json', attribute='charset', value='UTF-8')),
        ]
        for subtest in subtests:
            with self.subTest(subtest=subtest):
                mock_response = MagicMock(getheader=MagicMock(return_value=subtest.content_type))
                assert ContentType.from_response(mock_response) == subtest.expected

    def test_str(self):
        @dataclass
        class SubTest:
            content_type: ContentType
            expected: str

        subtests = [
            SubTest(ContentType(type='text', subtype='plain'), 'text/plain'),
            SubTest(ContentType(type='application', subtype='json'), 'application/json'),
            SubTest(ContentType(type='application', subtype='json', attribute='charset', value='UTF-8'), 'application/json; charset=UTF-8'),
        ]
        for subtest in subtests:
            with self.subTest(subtest=subtest):
                assert str(subtest.content_type) == subtest.expected

    def test_charset(self):
        @dataclass
        class SubTest:
            content_type: ContentType
            default: str
            expected: str

        subtests = [
            # charset()
            SubTest(ContentType(type='text', subtype='plain', attribute='charset', value='utf-8'), default=None, expected='utf-8'),
            SubTest(ContentType(type='text', subtype='plain', attribute='charset', value='UTF-8'), default=None, expected='UTF-8'),
            SubTest(ContentType(type='text', subtype='plain', attribute='charset'), default=None, expected='UTF-8'),
            SubTest(ContentType(type='text', subtype='plain'), default=None, expected='UTF-8'),
            # charset(default=...)
            SubTest(ContentType(type='text', subtype='plain', attribute='charset', value='utf-8'), default='ascii', expected='utf-8'),
            SubTest(ContentType(type='text', subtype='plain', attribute='charset', value='UTF-8'), default='ascii', expected='UTF-8'),
            SubTest(ContentType(type='text', subtype='plain'), default='utf-8', expected='UTF-8'),
        ]
        for subtest in subtests:
            with self.subTest(subtest=subtest):
                if subtest.default:
                    assert subtest.content_type.charset(subtest.default) == subtest.expected
                else:
                    assert subtest.content_type.charset() == subtest.expected

    def test_is_json(self):
        @dataclass
        class SubTest:
            content_type: ContentType
            expected: bool

        subtests = [
            SubTest(ContentType(type='text', subtype='plain'), 'text/plain'),
            SubTest(ContentType(type='application', subtype='json'), 'application/json'),
            SubTest(ContentType(type='application', subtype='json', attribute='charset', value='UTF-8'), 'application/json; charset=UTF-8'),
        ]
        for subtest in subtests:
            with self.subTest(subtest=subtest):
                assert str(subtest.content_type) == subtest.expected


class TestWebLinkHeader(TestCase):
    def test_links(self):
        value = ('<https://api.github.com/repositories/251530846/releases?per_page=1&page=2>; rel="next", '
                 '<https://api.github.com/repositories/251530846/releases?per_page=1&page=4>; rel="last", '
                 '<http://localhost>; media="application/json;curveball"; anchor=unquoted')

        link_header = WebLinkHeader.from_value(value)

        assert len(link_header) == 3

        assert link_header[0].url == 'https://api.github.com/repositories/251530846/releases?per_page=1&page=2'
        assert link_header[0].params == {'rel': 'next'}
        assert link_header[1].url == 'https://api.github.com/repositories/251530846/releases?per_page=1&page=4'
        assert link_header[1].params == {'rel': 'last'}
        assert link_header[2].url == 'http://localhost'
        assert link_header[2].params == {'media': 'application/json;curveball', 'anchor': 'unquoted'}

        assert link_header.rel('next').url == 'https://api.github.com/repositories/251530846/releases?per_page=1&page=2'
        assert link_header.rel('last').url == 'https://api.github.com/repositories/251530846/releases?per_page=1&page=4'
