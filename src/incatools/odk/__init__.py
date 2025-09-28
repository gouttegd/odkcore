# odkcore - Ontology Development Kit Core
# Copyright © 2025 ODK Developers
#
# This file is part of the ODK Core project and distributed under the
# terms of a 3-clause BSD license. See the LICENSE file in that project
# for the detailed conditions.

import importlib.metadata

try:
    __version__ = importlib.metadata.version("odk-core")
except importlib.metadata.PackageNotFoundError:
    # Not installed
    __version__ = "0.0.0"
