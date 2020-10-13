import re
from dataclasses import dataclass
from typing import ClassVar, List, Mapping, Optional, Pattern

import urllib3.response


@dataclass(frozen=True)
class ContentType:
    """An HTTP Content Type based on the RFC 1521 definition in Section 4: The Content-Type Header Field

    See: <https://tools.ietf.org/html/rfc1521#page-9>"""
    FORMAT: ClassVar[Pattern] = re.compile(
        r'^(?P<type>[^/\s]+)/(?P<subtype>[^;\s]+)(?:\s*;\s*(?P<attribute>[^=]+)=(?P<value>.+))?$'
    )

    type: str
    subtype: str
    attribute: Optional[str] = None
    value: Optional[str] = None

    def __str__(self) -> str:
        mime_type = f'{self.type}/{self.subtype}'
        if self.attribute or self.value:
            return f'{mime_type}; {"=".join(operand for operand in (self.attribute, self.value) if operand)}'
        return mime_type

    def charset(self, default: str = 'UTF-8') -> str:
        return (
            self.value if self.attribute and self.attribute.lower() == 'charset' and self.value else
            default.upper()
        )

    def is_json(self) -> bool:
        return f'{self.type}/{self.subtype}'.lower() == 'application/json'

    @classmethod
    def from_response(cls, response: urllib3.response.HTTPResponse):
        content_type = response.getheader('Content-Type', '')
        content_type_match = cls.FORMAT.match(content_type)
        if not content_type_match:
            return ContentType(type='text', subtype='plain')
        return ContentType(**content_type_match.groupdict())


@dataclass
class WebLink:
    url: str
    params: Mapping[str, str]


@dataclass
class WebLinkHeader:
    """An HTTP web links parser based on the RFC 5988 definition.

    See: <https://tools.ietf.org/html/rfc5988>;
         <https://tools.ietf.org/html/rfc8288#section-3>"""
    links: List[WebLink]

    def __len__(self) -> int:
        return len(self.links)

    def __getitem__(self, key: int) -> WebLink:
        return self.links[key]

    def rel(self, value: str) -> Optional[WebLink]:
        for link in reversed(self.links):
            if link.params.get('rel') == value:
                return link
        return None

    @classmethod
    def from_value(cls, value: str):
        links = []
        link_matches = list(re.finditer(r'(?:, *)?<(?P<url>[^>]+)>(?:; *)?', value))
        last_link_match = len(link_matches) - 1
        for i, link_match in enumerate(link_matches):
            next_link_match = link_matches[i + 1] if i < last_link_match else None
            params = value[link_match.end():next_link_match.start() if next_link_match else None]
            params_matches = re.finditer(
                r'(?:; *)?(?P<key>[^=]+)=(?P<value>(?:\"[^\"]+\"|[^;]+)?)', params
            )
            link = WebLink(
                url=link_match['url'],
                params={
                    param['key']: param['value'].strip(' "')
                    for param in params_matches if param
                }
            )

            links.append(link)

        return WebLinkHeader(links=links)

    @classmethod
    def from_response(cls, response: urllib3.response.HTTPResponse):
        return cls.from_value(response.headers.get('Link'))
