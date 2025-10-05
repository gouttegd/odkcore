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
from typing import Union

import requests

ROBOT_SOURCE = "https://github.com/ontodev/robot/releases/download/v1.9.8/robot.jar"
DICER_SOURCE = "https://github.com/gouttegd/dicer/releases/download/dicer-0.2.1/dicer-cli-0.2.1.jar"
SSSOM_SOURCE = "https://github.com/gouttegd/sssom-java/releases/download/sssom-java-1.9.0/sssom-cli-1.9.0.jar"
DOSDP_SOURCE = "https://github.com/INCATools/dosdp-tools/releases/download/v0.19.3/dosdp-tools-0.19.3.tgz"
RELGR_SOURCE = "https://github.com/INCATools/relation-graph/releases/download/v2.3.3/relation-graph-cli-2.3.3.tgz"
ODK_PLUGIN_SOURCE = "https://github.com/INCATools/odk-robot-plugin/releases/download/odk-robot-plugin-0.2.0/odk.jar"
SSSOM_PLUGIN_SOURCE = "https://github.com/gouttegd/sssom-java/releases/download/sssom-java-1.9.0/sssom-robot-plugin-1.9.0.jar"
OBO_EPM_SOURCE = "https://raw.githubusercontent.com/biopragmatics/bioregistry/main/exports/contexts/obo.epm.json"


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

    def download(self, target: Path) -> None:
        """Downloads the file from its remote location.

        :param target: Where the downloaded file should be written.
        """
        r = requests.get(self.source, stream=True)
        r.raise_for_status()
        with target.open("wb") as f:
            for chunk in r.iter_content(chunk_size=None):
                f.write(chunk)

    def get_final_location(self, target: ODKEnvironment) -> Path:
        """Gets the location of the file once installed.

        This should be overriden in subclasses so that each different
        type of file gets its own location right.

        :param target: The environment in which to install the file.

        :returns: The final location of the file.
        """
        return target.root / self.name


class Tool(DownloadableFile):
    """A file that is an executable tool."""

    def is_available(self) -> bool:
        """Checks whether the tool is present in the current environment."""
        return which(self.name) is not None


class SimpleJavaTool(Tool):
    """A tool that is self-contained in a single Jar archive."""

    def install(self, target: ODKEnvironment) -> None:
        jar = target.toolsdir / (self.name + ".jar")
        self.download(jar)
        launcher = target.bindir / self.name
        with launcher.open("w") as f:
            f.write("#!/bin/sh/\n")
            f.write(f'exec java -jar {jar.absolute()} "$@"\n')
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
        launcher = target.bindir / self.name
        with launcher.open("w") as f:
            f.write("#!/bin/sh\n")
            f.write(f'exec java -cp {classpath} {self.main_class} "$@"\n')
        launcher.chmod(0o755)


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
        env_file = target.bindir / self.name
        with env_file.open("w") as f:
            f.write("#!/bin/sh\n")
            f.write(f"PATH={target.bindir.absolute()}:$PATH\n")
            f.write(f"ODK_RESOURCES_DIR={target.resourcesdir.absolute()}\n")
            f.write("export PATH\n")
            f.write("export ODK_RESOURCES_DIR\n")


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
    tools: list[Tool]
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
        self.tools = [
            SimpleJavaTool("robot", ROBOT_SOURCE),
            SimpleJavaTool("dicer-cli", DICER_SOURCE),
            SimpleJavaTool("sssom-cli", SSSOM_SOURCE),
            MultiJarJavaTool(
                "dosdp-tools", DOSDP_SOURCE, "org.monarchinitiative.dosdp.cli.Main"
            ),
            MultiJarJavaTool(
                "relation-graph", RELGR_SOURCE, "org.renci.relationgraph.Main"
            ),
        ]
        self.files = [
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

        :param force: If true, tools are installed in the environment
            even if they are already available in the current PATH.
        """
        self.bindir.mkdir(parents=True, exist_ok=True)
        self.toolsdir.mkdir(parents=True, exist_ok=True)
        self.pluginsdir.mkdir(parents=True, exist_ok=True)

        for tool in self.tools:
            if not tool.is_available() or force:
                logging.info(f"Installing {tool.name}...")
                tool.install(self)

        for file in self.files:
            logging.info(f"Installing {file.name}...")
            file.install(self)
