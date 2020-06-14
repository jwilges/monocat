from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar, Optional, Pattern

import urllib3.response


@dataclass(frozen=True)
class ContentType:
    '''An HTTP Content Type based on the RFC 1521 definition in Section 4: The Content-Type Header Field

    See: <https://tools.ietf.org/html/rfc1521#page-9>'''
    FORMAT: ClassVar[Pattern] = re.compile(r'^(?P<type>[^/\s]+)/(?P<subtype>[^;\s]+)(?:\s*;\s*(?P<attribute>[^=]+)=(?P<value>.+))?$')

    type: str
    subtype: str
    attribute: Optional[str] = None
    value: Optional[str] = None

    def __str__(self) -> str:
        mime_type = f'{self.type}/{self.subtype}'
        if self.attribute or self.value:
            return f'{mime_type}; {"=".join((self.attribute, self.value))}'
        return mime_type

    def charset(self, default: str = 'UTF-8') -> str:
        return self.value if self.attribute and self.attribute.lower() == 'charset' and self.value else default.upper()

    def is_json(self) -> bool:
        return f'{self.type}/{self.subtype}'.lower() == 'application/json'

    @classmethod
    def from_response(cls, response: urllib3.response.HTTPResponse) -> ContentType:
        content_type = response.getheader('Content-Type', '')
        content_type_match = cls.FORMAT.match(content_type)
        if not content_type_match:
            return ContentType(type='text', subtype='plain')
        return ContentType(**content_type_match.groupdict())
