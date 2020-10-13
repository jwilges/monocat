import urllib3


class ContentType:
    @classmethod
    def from_response(cls, response: urllib3.response.HTTPResponse) -> ContentType: ...


class WebLinkHeader:
    @classmethod
    def from_value(cls, value: str) -> WebLinkHeader: ...

    @classmethod
    def from_response(cls, response: urllib3.response.HTTPResponse) -> WebLinkHeader: ...
