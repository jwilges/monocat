import json
import logging
import os
from base64 import b64encode
from datetime import datetime
from typing import List, Mapping, Optional
from urllib.parse import urlparse, ParseResult

import uritemplate
import urllib3
from pydantic import BaseModel, HttpUrl

import monocat.__metadata__
from monocat._http import ContentType


class AssetRequest(BaseModel):
    name: str
    label: Optional[str] = ''


class AssetResponse(BaseModel):
    url: HttpUrl
    browser_download_url: HttpUrl
    id: int
    node_id: str
    name: str
    label: str
    state: str
    content_type: str
    size: int
    download_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class ReleaseRequest(BaseModel):
    tag_name: str
    target_commitish: str
    name: str
    body: str
    draft: Optional[bool] = False
    prerelease: Optional[bool] = False


class ReleaseResponse(BaseModel):
    url: HttpUrl
    html_url: HttpUrl
    assets_url: HttpUrl
    upload_url: HttpUrl
    tarball_url: Optional[HttpUrl] = None
    zipball_url: Optional[HttpUrl] = None
    id: int
    tag_name: str
    target_commitish: str
    name: str
    body: str
    draft: bool
    prerelease: bool
    created_at: datetime
    published_at: Optional[datetime] = None


class GitHubClient:
    API_BASE_URL = os.environ.get('GITHUB_API', 'https://api.github.com')
    API_BODY_ENCODING = 'utf-8'
    _logger = logging.getLogger(__name__)

    def __init__(self, owner: str, repository: str, token: str = None):
        self.http = urllib3.PoolManager()
        self.token = token or os.environ.get('GITHUB_TOKEN')
        if not self.token:
            raise EnvironmentError('No GitHub token was specified.')

        self.owner = owner
        self.repository = repository
        self.base_headers = {
            'User-Agent': f'{monocat.__metadata__.__name__}/{monocat.__metadata__.__version__}',
            'Authorization': f'Basic {b64encode(self.token.encode()).decode()}',
            'Accept': 'application/json',
        }
        self._logger.debug('GitHub Authorization: %s', self.base_headers['Authorization'])

    def _resolve_url(self, url: str) -> str:
        parsed_url: ParseResult = urlparse(url)
        return url if parsed_url.scheme and parsed_url.netloc else f'{self.API_BASE_URL}{url}'

    def _request(self, method: str, url: str,
                 fields: Optional[Mapping[str, str]] = None,
                 headers: Mapping[str, str] = {},
                 body: Optional[bytes] = None):
        if method in ('PATCH', 'POST', 'PUT'):
            headers = {
                **self.base_headers,
                'Content-Type': f'application/json; charset={self.API_BODY_ENCODING.upper()}',
                **headers
            }
            body = body.encode(self.API_BODY_ENCODING) if body and hasattr(body, 'encode') else body
        else:
            headers = {**self.base_headers, **headers}

        response = self.http.request(method, self._resolve_url(url), headers=headers, body=body)
        content_type = ContentType.from_response(response)
        if content_type.is_json():
            return json.loads(response.data.decode(content_type.charset(default=self.API_BODY_ENCODING).lower()))
        else:
            return response.data.decode(content_type.charset(default=self.API_BODY_ENCODING).lower())

    def _get(self, url: str, fields: Optional[Mapping[str, str]] = None):
        return self._request('GET', url, fields=fields)

    def _patch(self, url: str, headers: Mapping[str, str] = {}, body: Optional[bytes] = None):
        return self._request('PATCH', url, headers=headers, body=body)

    def _post(self, url: str, headers: Mapping[str, str] = {}, body: Optional[bytes] = None):
        return self._request('POST', url, headers=headers, body=body)

    def list_releases(self) -> List[ReleaseResponse]:
        # See: <https://developer.github.com/v3/repos/releases/#list-releases>
        # GET /repos/:owner/:repo/releases
        releases = [ReleaseResponse.parse_obj(r) for r in self._get(f'/repos/{self.owner}/{self.repository}/releases')]
        self._logger.info('Releases: %s', releases)
        return releases

    def get_release_by_tag_name(self, tag: str) -> ReleaseResponse:
        # See: <https://developer.github.com/v3/repos/releases/#get-a-release-by-tag-name>
        # GET /repos/:owner/:repo/releases/tags/:tag
        release = ReleaseResponse.parse_obj(self._get(f'/repos/{self.owner}/{self.repository}/releases/tags/{tag}'))
        self._logger.info('Release: %s', release)
        return release

    def create_release(self, release: ReleaseRequest) -> ReleaseResponse:
        # See: <https://developer.github.com/v3/repos/releases/#create-a-release>
        # POST /repos/:owner/:repo/releases
        release = ReleaseResponse.parse_obj(
            self._post(f'/repos/{self.owner}/{self.repository}/releases',
                       body=release.json(exclude_unset=True)))
        self._logger.info('Created Release: %s', release)
        return release

    def update_release(self, release: ReleaseRequest) -> ReleaseResponse:
        # See: <https://developer.github.com/v3/repos/releases/#update-a-release>
        # PATCH /repos/:owner/:repo/releases/:release_id
        release_id = self.get_release_by_tag_name(release.tag_name).id
        release = ReleaseResponse.parse_obj(
            self._patch(f'/repos/{self.owner}/{self.repository}/releases/{release_id}',
                        body=release.json(exclude_unset=True)))
        self._logger.info('Updated Release: %s', release)

    def upload_asset(self, upload_url: str, release_id: int, asset: AssetRequest, body: bytes, content_type: str) -> AssetResponse:
        # See: <https://developer.github.com/v3/repos/releases/#upload-a-release-asset>
        # POST :server/repos/:owner/:repo/releases/:release_id/assets{?name,label}
        asset = AssetResponse.parse_obj(
            self._post(uritemplate.expand(upload_url, **asset.dict(exclude_unset=True)),
                       headers={'Content-Type': content_type},
                       body=body))
        self._logger.info('Created Asset: %s', asset)
        return asset
