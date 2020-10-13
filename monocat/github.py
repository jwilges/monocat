import json
import logging
import mimetypes
import os
from base64 import b64encode
from datetime import datetime
from http import HTTPStatus
from typing import List, Mapping, Optional, Union
from urllib.parse import ParseResult, urlparse

import uritemplate
import urllib3
from pydantic import BaseModel, Field, HttpUrl

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
    target_commitish: Optional[str] = ''
    name: Optional[str] = ''
    body: Optional[str] = ''
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
    name: Optional[str] = None
    body: Optional[str] = None
    draft: bool
    prerelease: bool
    created_at: datetime
    published_at: Optional[datetime] = None
    assets: List[AssetResponse] = Field(default_factory=lambda: [])


class GitHubClientError(RuntimeError):
    http_status: HTTPStatus
    http_reason: str

    def __init__(self, http_status: HTTPStatus, http_reason: str, *args):
        super().__init__(*args)
        self.http_status = http_status
        self.http_reason = http_reason


class GitHubClient:
    # TODO: This client does not yet paginate responses from multiple-response GitHub API endpoints.
    #       However, the existing `monocat.WebLinkHeader` implementation may be used for pagination
    #       based on the content of the Link header.
    #       See: <https://developer.github.com/v3/#pagination>
    API_BASE_URL = os.environ.get('GITHUB_API', 'https://api.github.com')
    API_BODY_ENCODING = 'utf-8'
    _logger = logging.getLogger(__name__)

    def __init__(self, owner: str, repository: str, token: str = None):
        self.API_CONTENT_TYPE = f'application/vnd.github.v3+json; charset={self.API_BODY_ENCODING.upper()}'

        self.http = urllib3.PoolManager()
        self.token = token or os.environ.get('GITHUB_TOKEN')
        if not self.token:
            raise EnvironmentError('No GitHub token was specified.')

        self.owner = owner
        self.repository = repository
        self.base_headers = {
            'User-Agent': f'{monocat.__metadata__.NAME}/{monocat.__metadata__.VERSION}',
            'Authorization': f'Basic {b64encode(self.token.encode()).decode()}',
            'Accept': 'application/vnd.github.v3+json',
        }
        self._logger.debug('GitHub Authorization: %s', self.base_headers['Authorization'])

    def _resolve_url(self, url: str) -> str:
        parsed_url: ParseResult = urlparse(url)
        return url if parsed_url.scheme and parsed_url.netloc else f'{self.API_BASE_URL}{url}'

    def _request(
        self,
        method: str,
        url: str,
        fields: Optional[Mapping[str, str]] = None,
        headers: Mapping[str, str] = None,
        body: Union[bytes, str, None] = None
    ):
        headers = headers if headers else {}
        if method in ('PATCH', 'POST', 'PUT'):
            headers = {**self.base_headers, 'Content-Type': self.API_CONTENT_TYPE, **headers}
            body = body.encode(self.API_BODY_ENCODING) if isinstance(body, str) else body
        else:
            headers = {**self.base_headers, **headers}

        response = self.http.request(
            method, self._resolve_url(url), fields=fields, headers=headers, body=body
        )
        content_type = ContentType.from_response(response)

        if content_type.is_json():
            content = json.loads(
                response.data.decode(content_type.charset(default=self.API_BODY_ENCODING).lower())
            )
        else:
            content = response.data.decode(
                content_type.charset(default=self.API_BODY_ENCODING).lower()
            )

        self._logger.debug(
            'GitHub API request: %s <%s>\nGitHub API response (status: %s; content type: %s):\n%s',
            method, url, HTTPStatus(response.status), content_type, content
        )

        if response.status >= 400:
            raise GitHubClientError(response.status, response.reason, content)

        return content

    def _get(self, url: str, fields: Optional[Mapping[str, str]] = None):
        return self._request('GET', url, fields=fields)

    def _patch(
        self, url: str, headers: Mapping[str, str] = None, body: Union[bytes, str, None] = None
    ):
        return self._request('PATCH', url, headers=headers, body=body)

    def _post(
        self, url: str, headers: Mapping[str, str] = None, body: Union[bytes, str, None] = None
    ):
        return self._request('POST', url, headers=headers, body=body)

    def list_releases(self) -> List[ReleaseResponse]:
        # See: <https://docs.github.com/en/rest/reference/repos#list-releases>
        # GET /repos/{owner}/{repo}/releases
        responses = [
            ReleaseResponse.parse_obj(r)
            for r in self._get(f'/repos/{self.owner}/{self.repository}/releases')
        ]
        self._logger.debug('Releases: %s', responses)
        return responses

    def get_release(self, release_id: str) -> Optional[ReleaseResponse]:
        # See: <https://docs.github.com/en/rest/reference/repos#get-a-release>
        # GET /repos/{owner}/{repo}/releases/{release_id}
        response: Optional[ReleaseResponse]
        try:
            response = ReleaseResponse.parse_obj(
                self._get(f'/repos/{self.owner}/{self.repository}/releases/{release_id}')
            )
        except GitHubClientError as e:
            if e.http_status != HTTPStatus.NOT_FOUND:
                raise
            response = None
        return response

    def get_release_by_tag(self, tag: str) -> Optional[ReleaseResponse]:
        # See: <https://docs.github.com/en/rest/reference/repos#get-a-release-by-tag-name>
        # GET /repos/{owner}/{repo}/releases/tags/{tag}
        response: Optional[ReleaseResponse]
        try:
            response = ReleaseResponse.parse_obj(
                self._get(f'/repos/{self.owner}/{self.repository}/releases/tags/{tag}')
            )
        except GitHubClientError as e:
            if e.http_status != HTTPStatus.NOT_FOUND:
                raise
            response = None
        return response

    def create_release(self, release: ReleaseRequest) -> ReleaseResponse:
        # See: <https://docs.github.com/en/rest/reference/repos#create-a-release>
        # POST /repos/{owner}/{repo}/releases
        response = ReleaseResponse.parse_obj(
            self._post(
                f'/repos/{self.owner}/{self.repository}/releases',
                body=release.json(exclude_unset=True)
            )
        )
        self._logger.debug('Created Release: %s', response)
        return response

    def update_release(self, release: ReleaseRequest, release_id: int) -> ReleaseResponse:
        # See: <https://docs.github.com/en/rest/reference/repos#update-a-release>
        # PATCH /repos/{owner}/{repo}/releases/{release_id}
        response = ReleaseResponse.parse_obj(
            self._patch(
                f'/repos/{self.owner}/{self.repository}/releases/{release_id!s}',
                body=release.json(exclude_unset=True)
            )
        )
        self._logger.debug('Updated Release: %s', response)
        return response

    def list_assets(self, release: ReleaseResponse) -> List[AssetResponse]:
        # See: <https://docs.github.com/en/rest/reference/repos#list-release-assets>
        # GET /repos/{owner}/{repo}/releases/{release_id}/assets
        responses = [AssetResponse.parse_obj(r) for r in self._get(release.assets_url)]
        self._logger.debug('Assets: %s', responses)
        return responses

    def get_asset(self, release: ReleaseResponse, asset_id: int) -> AssetResponse:
        # See: <https://docs.github.com/en/rest/reference/repos#get-a-release-asset>
        # GET /repos/{owner}/{repo}/releases/{release_id}/assets
        response = AssetResponse.parse_obj(self._get(f'{release.assets_url}/{asset_id!s}'))
        self._logger.debug('Asset: %s', response)
        return response

    def update_asset(self, asset_id: int, asset: AssetRequest) -> AssetResponse:
        # See: <https://docs.github.com/en/rest/reference/repos#update-a-release-asset>
        # PATCH /repos/{owner}/{repo}/releases/assets/:asset_id
        response = AssetResponse.parse_obj(
            self._patch(
                f'/repos/{self.owner}/{self.repository}/releases/assets/{asset_id!s}',
                body=asset.json(exclude_unset=True)
            )
        )
        self._logger.debug('Updated Asset: %s', response)
        return response

    def upload_asset(
        self,
        upload_url: str,
        asset: AssetRequest,
        body: bytes,
        content_type: Optional[str] = None
    ) -> AssetResponse:
        # See: <https://docs.github.com/en/rest/reference/repos#upload-a-release-asset>
        # POST {upload_base_url}/repos/{owner}/{repo}/releases/{release_id}/assets{?name,label}
        if not content_type:
            content_type = mimetypes.guess_type(asset.name)[0] or 'application/octet-stream'
        response = AssetResponse.parse_obj(
            self._post(
                uritemplate.expand(upload_url, **asset.dict(exclude_unset=True)),
                headers={'Content-Type': content_type},
                body=body
            )
        )
        self._logger.debug('Created Asset: %s', response)
        return response
