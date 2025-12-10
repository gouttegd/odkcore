# odkcore - Ontology Development Kit Core
# Copyright © 2025 ODK Developers
#
# This file is part of the ODK Core project and distributed under the
# terms of a 3-clause BSD license. See the LICENSE file in that project
# for the detailed conditions.

from __future__ import annotations

import logging
import platform
import tarfile
from os.path import basename
from pathlib import Path
from shutil import which
from typing import Optional, Union
from zipfile import ZipFile

import requests
from jinja2 import Template

ROBOT_SOURCE = "https://github.com/ontodev/robot/releases/download/v1.9.8/robot.jar"
DICER_SOURCE = "https://github.com/gouttegd/dicer/releases/download/dicer-0.2.1/dicer-cli-0.2.1.jar"
SSSOM_SOURCE = "https://github.com/gouttegd/sssom-java/releases/download/sssom-java-1.9.0/sssom-cli-1.9.0.jar"
DOSDP_SOURCE = "https://github.com/INCATools/dosdp-tools/releases/download/v0.19.3/dosdp-tools-0.19.3.tgz"
RELGR_SOURCE = "https://github.com/INCATools/relation-graph/releases/download/v2.3.3/relation-graph-cli-2.3.3.tgz"
ODK_PLUGIN_SOURCE = "https://github.com/INCATools/odk-robot-plugin/releases/download/odk-robot-plugin-0.2.0/odk.jar"
SSSOM_PLUGIN_SOURCE = "https://github.com/gouttegd/sssom-java/releases/download/sssom-java-1.9.0/sssom-robot-plugin-1.9.0.jar"
OBO_EPM_SOURCE = "https://raw.githubusercontent.com/biopragmatics/bioregistry/main/exports/contexts/obo.epm.json"

ACTIVATION_TEMPLATE = Path(__file__).parent.resolve() / "activate.jinja2"


class File(object):
    """Base class for a file to be installed in a ODK environment."""

    name: str

    def __init__(self, name: str):
        """Creates a new instance.

        :param str: The name of the file to be installed.
        """
        self.name = name

    def install(self, target: ODKEnvironment) -> None:
        """Installs the file in an environment.

        :param target: The environment where the file must be installed.
        """
        pass

    def is_available(self, target: ODKEnvironment) -> bool:
        """Checks whether the file is already available.

        :param target: The environment to check for availability of the file.
        """
        return self.get_final_location(target).exists()

    def get_final_location(self, target: ODKEnvironment) -> Path:
        """Gets the location of the file once installed.

        This should be overriden in subclasses so that each different
        type of files gets its own location right.

        :param target: The environment in which to install the file.

        :returns: The final location of the file.
        """
        return target.root / self.name


class DownloadableFile(File):
    """A file that must be installed from an online source."""

    source: str

    def __init__(self, name: str, url: str):
        """Creates a new instance:

        :param name: The name of the file to be installed.
        :param url: The URL to download the file from.
        """
        File.__init__(self, name)
        self.source = url

    def install(self, target: ODKEnvironment) -> None:
        self.download(self.get_final_location(target))

    def download(self, target: Path, source: Optional[str] = None) -> None:
        """Downloads the file from its remote location.

        :param target: Where the downloaded file should be written.
        :param source: Where to download the file from (defaults to
            the source argument given to the constructor).
        """
        if source is None:
            source = self.source
        r = requests.get(source, stream=True)
        r.raise_for_status()
        with target.open("wb") as f:
            for chunk in r.iter_content(chunk_size=None):
                f.write(chunk)


class Tool(DownloadableFile):
    """A file that is an executable tool."""

    def is_available(self, target: ODKEnvironment) -> bool:
        if not self.get_final_location(target).exists():
            # Even if the tool is not in the environment, it is enough
            # for it to be reachable in the PATH
            return which(self.name) is not None
        return True

    def get_final_location(self, target: ODKEnvironment) -> Path:
        return target.bindir / self.name


class SimpleJavaTool(Tool):
    """A tool that is self-contained in a single Jar archive."""

    def install(self, target: ODKEnvironment) -> None:
        jar = target.toolsdir / (self.name + ".jar")
        self.download(jar)
        launcher = self.get_final_location(target)
        with launcher.open("w") as f:
            f.write("#!/bin/sh\n")
            f.write(f'exec java $JAVA_OPTS -jar "{jar.absolute()}" "$@"\n')
        launcher.chmod(0o755)


class MultiJarJavaTool(SimpleJavaTool):
    """A tool that is provided as several Jar archives."""

    main_class: str

    def __init__(self, name: str, url: str, main_class: str):
        """Creates a new instance.

        :param command: The name of the tool, as it is invoked from the command line.
        :param url: The URL the tool must be downloaded from.
        :param main_class: The name of the Java class containing the entry point.
        """
        SimpleJavaTool.__init__(self, name, url)
        self.main_class = main_class

    def install(self, target: ODKEnvironment) -> None:
        libdir = target.toolsdir / self.name
        libdir.mkdir(parents=True, exist_ok=True)

        archive = target.root / (self.name + ".tar.gz")
        self.download(archive)

        jars = []
        with tarfile.open(archive) as f:
            for member in f.getmembers():
                if member.name.endswith(".jar"):
                    member.name = basename(member.name)
                    jars.append(member.name)
                    f.extract(member, path=libdir)
        archive.unlink()

        classpath = ":".join([str(libdir.absolute() / path) for path in jars])
        launcher = self.get_final_location(target)
        with launcher.open("w") as f:
            f.write("#!/bin/sh\n")
            f.write(f'exec java $JAVA_OPTS -cp "{classpath}" {self.main_class} "$@"\n')
        launcher.chmod(0o755)


class SqliteTool(Tool):
    """The sqlite3 tool."""

    version: str

    def __init__(self, version: str):
        Tool.__init__(self, "sqlite3", "https://sqlite.org/2025/")
        self.version = self._get_encoded_version(version)

    def install(self, target: ODKEnvironment) -> None:
        if target.system == "Linux" and target.machine == "x86_64":
            qualifier = "linux-x64"
        elif target.system == "Darwin" and target.machine == "x86_64":
            qualifier = "osx-x64"
        elif target.system == "Darwin" and target.machine == "arm64":
            qualifier = "osx-arm64"
        else:
            raise Exception(
                f"Unsupported system/machine {target.system}/{target.machine}"
            )

        archive_name = f"sqlite-tools-{qualifier}-{self.version}.zip"
        archive = target.root / archive_name
        self.download(archive, source=self.source + archive_name)

        with ZipFile(archive, "r") as f:
            f.extract("sqlite3", target.bindir)
        archive.unlink()
        self.get_final_location(target).chmod(0o755)

    def _get_encoded_version(self, version: str) -> str:
        parts = version.split(".")
        encoded = parts[0]
        for p in parts[1:]:
            n = int(p)
            encoded += f"{n:02d}"
        if len(parts) < 4:
            encoded += "00"
        return encoded


class GithubTool(Tool):
    """The Github CLI tool."""

    version: str

    def __init__(self, version: str):
        Tool.__init__(
            self, "gh", f"https://github.com/cli/cli/releases/download/v{version}/"
        )
        self.version = version

    def install(self, target: ODKEnvironment) -> None:
        if target.system == "Linux" and target.machine == "x86_64":
            qualifier = "linux_amd64"
            is_zip = False
        elif target.system == "Darwin" and target.machine == "x86_64":
            qualifier = "macOS_amd64"
            is_zip = True
        elif target.system == "Darwin" and target.machine == "arm64":
            qualifier = "macOS_arm64"
            is_zip = True
        else:
            raise Exception(
                f"Unsupported system/machine {target.system}/{target.machine}"
            )

        basename = f"gh_{self.version}_{qualifier}"
        if is_zip:
            archive_name = basename + ".zip"
        else:
            archive_name = basename + ".tar.gz"
        archive = target.root / archive_name
        self.download(archive, source=self.source + archive_name)

        srcfile = f"{basename}/bin/gh"
        dstfile = self.get_final_location(target)

        if is_zip:
            with ZipFile(archive, "r") as f:
                with dstfile.open("wb") as dst:
                    dst.write(f.read(srcfile))
        else:
            with tarfile.open(archive) as f:
                for member in f.getmembers():
                    if member.name == srcfile:
                        member.name = "gh"
                        f.extract(member, path=target.bindir)

        dstfile.chmod(0o755)


class RobotPlugin(DownloadableFile):
    """A file that is a plugin for ROBOT."""

    def get_final_location(self, target: ODKEnvironment) -> Path:
        return target.pluginsdir / (self.name + ".jar")


class ResourceFile(DownloadableFile):
    """A file that is a generic resource file."""

    def get_final_location(self, target: ODKEnvironment) -> Path:
        return target.resourcesdir / self.name


class ActivationFile(File):
    """The activation file for an environment.

    That file may be sourced by the shell to activate the environment,
    that is to make the tools and resources it contains available for
    use.
    """

    def __init__(self):
        File.__init__(self, "activate-odk-environment.sh")

    def install(self, target: ODKEnvironment) -> None:
        env_file = self.get_final_location(target)
        with ACTIVATION_TEMPLATE.open("r") as fin:
            template = Template(fin.read())
            with env_file.open("w") as fout:
                fout.write(template.render(target_dir=target.root.absolute()))

    def get_final_location(self, target: ODKEnvironment) -> Path:
        return target.bindir / self.name


class ODKEnvironment(object):
    """Represents a local ODK environment.

    A "local ODK environment" is basically a directory containing the
    tools and resources needed by ODK workflows.
    """

    root: Path
    bindir: Path
    toolsdir: Path
    resourcesdir: Path
    pluginsdir: Path
    system: str
    machine: str
    files: list[File]

    def __init__(self, target: Union[Path, str]):
        """Creates a new instance.

        :param target: The root directory of the environment.
        """
        if isinstance(target, str):
            self.root = Path(target)
        else:
            self.root = target
        self.bindir = self.root / "bin"
        self.toolsdir = self.root / "tools"
        self.resourcesdir = self.root / "resources"
        self.pluginsdir = self.resourcesdir / "robot/plugins"
        self.system = platform.system()
        self.machine = platform.machine()
        self.files = [
            SimpleJavaTool("robot", ROBOT_SOURCE),
            SimpleJavaTool("dicer-cli", DICER_SOURCE),
            SimpleJavaTool("sssom-cli", SSSOM_SOURCE),
            MultiJarJavaTool(
                "dosdp-tools", DOSDP_SOURCE, "org.monarchinitiative.dosdp.cli.Main"
            ),
            MultiJarJavaTool(
                "relation-graph", RELGR_SOURCE, "org.renci.relationgraph.Main"
            ),
            SqliteTool("3.51.1"),
            GithubTool("2.83.1"),
            RobotPlugin("odk", ODK_PLUGIN_SOURCE),
            RobotPlugin("sssom", SSSOM_PLUGIN_SOURCE),
            ResourceFile("obo.epm.json", OBO_EPM_SOURCE),
            ActivationFile(),
        ]

    def install(self, force: bool = False) -> None:
        """Installs the environment.

        This creates the various directories as needed and installs all
        files and tools needed for the ODK workflows to function
        (excluding Python packages, which are supposed to be already
        available).

        :param force: If true, files are installed in the environment
            even if they are already available.
        """
        self.bindir.mkdir(parents=True, exist_ok=True)
        self.toolsdir.mkdir(parents=True, exist_ok=True)
        self.pluginsdir.mkdir(parents=True, exist_ok=True)

        for file in self.files:
            if not file.is_available(self) or force:
                logging.info(f"Installing {file.name}...")
                file.install(self)
