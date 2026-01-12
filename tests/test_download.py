# odkcore - Ontology Development Kit Core
# Copyright © 2026 ODK Developers
#
# This file is part of the ODK Core project and distributed under the
# terms of a 3-clause BSD license. See the LICENSE file in that project
# for the detailed conditions.

import unittest
from pathlib import Path
from time import sleep

from incatools.odk.download import RemoteFileInfo, download_file


class TestDownload(unittest.TestCase):
    """A test case for the download function."""

    downloaded_file: Path
    url: str

    def setUp(self) -> None:
        self.downloaded_file = Path("xxx-downloaded_file.txt")
        self.url = "https://raw.githubusercontent.com/INCATools/odkcore/refs/heads/main/README.md"

    def tearDown(self) -> None:
        if self.downloaded_file.exists():
            self.downloaded_file.unlink()

    def test_download_once(self) -> None:
        """Test that we do not re-download a file needlessly."""

        ri = RemoteFileInfo()
        code = download_file(self.url, self.downloaded_file, ri, max_retry=5)
        if code != 200:
            self.skipTest(f"Could not download from {self.url}, cannot test")

        self.assertTrue(self.downloaded_file.exists())
        mtime = self.downloaded_file.stat().st_mtime

        sleep(1)
        code = download_file(self.url, self.downloaded_file, ri, max_retry=5)

        # Either the server told us the file had not been modified, or
        # the download function checked the newly downloaded file is the
        # same as the one downloaded just before. Either way, we should
        # get a 304, and the file should not have been touched.
        self.assertEqual(304, code)
        self.assertEqual(mtime, self.downloaded_file.stat().st_mtime)

    def test_no_overwrite_identical_file(self) -> None:
        """Test that a re-downloaded file is not overwritten needlessly."""

        ri = RemoteFileInfo()
        code = download_file(self.url, self.downloaded_file, ri, max_retry=5)
        if code != 200:
            self.skipTest(f"Could not download from {self.url}, cannot test")

        mtime = self.downloaded_file.stat().st_mtime

        # Remove server-side data from the RemoteFileInfo, so that the
        # server cannot tell us whether the file has been modified or
        # not, thereby forcing us to re-download the file.
        ri.etag = None
        ri.time = None

        sleep(1)
        code = download_file(self.url, self.downloaded_file, ri, max_retry=5)

        # Even if we have re-downloaded the file, the function should
        # still report that as a 304 and the previously downloaded file
        # should not have been touched.
        self.assertEqual(304, code)
        self.assertEqual(mtime, self.downloaded_file.stat().st_mtime)
