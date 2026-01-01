# odkcore - Ontology Development Kit Core
# Copyright © 2025 ODK Developers
#
# This file is part of the ODK Core project and distributed under the
# terms of a 3-clause BSD license. See the LICENSE file in that project
# for the detailed conditions.

import logging
import os
from bz2 import BZ2File
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from gzip import GzipFile
from hashlib import sha256
from io import BufferedIOBase, BytesIO
from pathlib import Path
from time import sleep
from typing import Dict, Iterator, Optional, Union
from urllib.parse import urlparse

import requests

RFC5322_DATE_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"
# Those are the HTTP errors that Curl considers as "transient" and
# eligible for retrying when the --retry option is used.
RETRIABLE_HTTP_ERRORS = (408, 429, 500, 502, 503, 504)


class Compression(Enum):
    NONE = (0, None)
    GZIP = (1, ".gz")
    BZIP2 = (2, ".bz2")

    extension: Optional[str]

    def __new__(cls, value: int, extension: Optional[str] = None):
        self = object.__new__(cls)
        self._value_ = value
        self.extension = extension
        return self

    @classmethod
    def from_extension(cls, path: Path) -> "Compression":
        for v in Compression:
            if v.extension is not None and v.extension == path.suffix:
                return v
        return Compression.NONE


class DownloadError(Exception):
    pass


@dataclass
class RemoteFileInfo:
    """Informations about a downloaded file.

    This class is a simple structure holding the informations we need in
    order to decide whether to update a file that has already been
    downloaded previously.
    """

    sha256: Optional[str] = None
    """The SHA-256 checksum of the downloaded file."""

    etag: Optional[str] = None
    """The tag returned by the server for the file."""

    time: Optional[datetime] = None
    """The time the file was last downloaded."""

    def to_file(self, dest: Path) -> None:
        """Writes the information to a cache file."""
        with dest.open("w") as fd:
            if self.sha256 is not None:
                fd.write(f"sha256: {self.sha256}\n")
            if self.etag is not None:
                fd.write(f"etag: {self.etag}\n")
            if self.time is not None:
                fd.write(f"time: {self.time.strftime(RFC5322_DATE_FORMAT)}\n")

    def from_cache_file(self, source: Path) -> "RemoteFileInfo":
        """Reads the information from a cache file."""
        if source.exists():
            with source.open("r") as fd:
                for line in fd:
                    if line.startswith("#"):
                        continue
                    items = line.strip().split(": ", maxsplit=1)
                    if len(items) != 2:
                        continue
                    if items[0] == "sha256":
                        self.sha256 = items[1]
                    elif items[0] == "etag":
                        self.etag = items[1]
                    elif items[0] == "time":
                        self.time = datetime.strptime(items[1], RFC5322_DATE_FORMAT)
        return self

    @classmethod
    def from_file(cls, source: Path) -> "RemoteFileInfo":
        """Gets the information from an existing file."""
        info = RemoteFileInfo()
        if source.exists():
            info.time = datetime.fromtimestamp(source.stat().st_mtime, UTC)
            h = sha256()
            with source.open("rb") as fd:
                while True:
                    chunk = fd.read(512)
                    if not chunk:
                        break
                    h.update(chunk)
            info.sha256 = h.hexdigest()
        return info


def download_file(
    url: str,
    output: Path,
    info: RemoteFileInfo,
    max_retry: int = 0,
    compression: Compression = Compression.NONE,
) -> int:
    """Downloads a remote file.

    This function will avoid needlessly downloading the file if the
    remote server can tell us that the remote file has not changed since
    the last time it was downloaded. In addition, even if the file is
    downloaded, if it is found to be identical to the locally available
    version, the existing file is not touched at all.

    :param url: The URL to download the file from.
    :param output: Where the downloaded file should be written.
    :param info: Informations about the last time the file was
        downloaded. If the fields of that structure are set to None,
        this means there is no local version of the file, and the
        remote file should always be downloaded. If the download is
        successful, the structure will be updated with informations from
        the newly downloaded file.
    :param max_retry: Number of download attempts to perform.
    :param compression: How the remote file is compressed (if at all).
        The file will be automatically uncompressed after being
        downloaded.

    :returns: The HTTP status code.
    """
    headers: Dict[str, str] = {}
    if info.time:
        headers["If-Modified-Since"] = info.time.strftime(RFC5322_DATE_FORMAT)
    if info.etag:
        headers["If-None-Match"] = info.etag

    n_try = 0
    hostname = urlparse(url).hostname
    while True:
        try:
            response = requests.get(url, timeout=5, headers=headers)
            if response.status_code == 200:
                return _handle_successful_download(response, output, info, compression)
            elif response.status_code == 304:
                logging.info(f"{output.name}: Not modified at {url}")
                return 304
            elif response.status_code == 404:
                logging.warn(f"{output.name}: Not found at {url}")
                return 404
            elif response.status_code in RETRIABLE_HTTP_ERRORS and n_try < max_retry:
                n_try += 1
                logging.warn(
                    f"{output.name}: Transient HTTP error, retrying ({n_try}/{max_retry}"
                )
                sleep(1)
            else:
                response.raise_for_status()
        except requests.exceptions.ConnectTimeout:
            # `curl --retry` retries on timeout errors, and so do we
            if n_try < max_retry:
                n_try += 1
                logging.warn(
                    f"{output.name}: Timeout when connecting to {hostname}, retrying ({n_try}/{max_retry})"
                )
                sleep(1)
            else:
                raise DownloadError(f"Timeout when connecting to {hostname}")
        except requests.exceptions.ConnectionError:
            raise DownloadError(f"Cannot connect to {hostname}")
        except requests.exceptions.HTTPError:
            raise DownloadError(f"HTTP error when downloading {url}")
        except requests.exceptions.ReadTimeout:
            raise DownloadError(f"Timeout when downloading {url}")


def _handle_successful_download(
    response: requests.Response,
    output: Path,
    info: RemoteFileInfo,
    comp: Compression,
) -> int:
    h = sha256()

    # We download into a temporary file so that we do not touch the
    # output file until (1) the download is complete and (2) we have
    # verified that the downloaded file is different from the output
    # file, if it already exists
    tmpfile = output.with_suffix(output.suffix + ".tmp")
    with tmpfile.open("wb") as fd:
        for chunk in _ResponseWrapper.maybe_wrap(response, comp).iter_content(512):
            h.update(chunk)
            fd.write(chunk)
    checksum = h.hexdigest()
    if info.sha256 == checksum:
        logging.info(
            f"{output.name}: File newly downloaded is identical to previously downloaded file"
        )
        # Remove the file we just downloaded, and report to caller as a
        # 304 Not-Modified status
        tmpfile.unlink()
        return 304
    else:
        logging.info(f"{output.name}: Download OK, file is new")
        os.replace(tmpfile, output)
        info.sha256 = checksum
        info.time = datetime.now(tz=UTC)
        info.etag = response.headers.get("ETag", None)
        return 200


class _ResponseWrapper:
    """Helper class to handle compressed files.

    This class allows to use the same `iter_content` method (as found on
    a requests.Response object) to get the content of a downloaded file,
    regardless of how the file has been compressed (if at all).
    """

    _stream: BufferedIOBase

    def __init__(self, stream: BufferedIOBase):
        self._stream = stream

    def iter_content(self, size: int = 512) -> Iterator[bytes]:
        while True:
            chunk = self._stream.read(size)
            if not chunk:
                break
            yield chunk
        self._stream.close()

    @classmethod
    def maybe_wrap(
        cls, response: requests.Response, compression: Compression
    ) -> Union[requests.Response, "_ResponseWrapper"]:
        if compression == Compression.GZIP:
            return _ResponseWrapper(GzipFile(fileobj=BytesIO(response.content)))
        elif compression == Compression.BZIP2:
            return _ResponseWrapper(BZ2File(BytesIO(response.content)))
        else:
            return response
