# odkcore - Ontology Development Kit Core
# Copyright © 2025 ODK Developers
#
# This file is part of the ODK Core project and distributed under the
# terms of a 3-clause BSD license. See the LICENSE file in that project
# for the detailed conditions.

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import List, Tuple
from urllib.parse import urlparse

import click
from lightrdf import Parser as LightRDFParser  # type: ignore
from rdflib import Graph

from . import __version__
from .download import Compression, DownloadError, RemoteFileInfo, download_file
from .template import DEFAULT_TEMPLATE_DIR, RESOURCES_DIR


@click.group()
def main() -> None:
    """Helper commands for ODK workflows."""
    logging.basicConfig(level=logging.INFO)


@main.command()
@click.option(
    "-p",
    "--profile",
    type=click.Path(path_type=Path),
    default="profile.txt",
    help="The profile file to check.",
)
def check_robot_profile(profile) -> None:
    """Checks a ROBOT profile for missing standard rules."""
    if not profile.exists():
        raise click.ClickException("ROBOT profile is missing")
    with profile.open() as f:
        current_rules = set([line.strip() for line in f])

    standard_profile = RESOURCES_DIR / "robot/profile.txt"
    if not standard_profile.exists():
        standard_profile = DEFAULT_TEMPLATE_DIR / "src/ontology/profile.txt"
        if not standard_profile.exists():
            raise click.ClickException("Standard ROBOT profile is missing")
    with standard_profile.open() as f:
        standard_rules = set([line.strip() for line in f])

    missing_rules = standard_rules - current_rules
    if len(missing_rules) > 0:
        print("Missing rules in current ROBOT profile:")
        print("\n".join(missing_rules))


@main.command()
@click.argument("context", type=click.Path(exists=True, path_type=Path))
def context2csv(context) -> None:
    """Converts a JSON context file to CSV."""
    with context.open() as f:
        try:
            ctx = json.load(f)
        except json.JSONDecodeError:
            raise click.ClickException("Cannot read context file")
    if "@context" not in ctx:
        raise click.ClickException("No @context in supposed context file")

    print("prefix,base")
    for prefix_name, url_prefix in context["@context"].items():
        print(f"{prefix_name},{url_prefix}")


@main.command()
@click.argument("file", type=click.Path(exists=True))
@click.option(
    "--lightrdf/--no-lightrdf", default=True, help="Check with the LightRDF parser."
)
@click.option(
    "--rdflib/--no-rdflib", default=False, help="Check with the RDFLib parser."
)
@click.option(
    "--jena/--no-jena", default=False, help="Check with the Apache Jena parser."
)
def check_rdfxml(file, lightrdf, rdflib, jena) -> None:
    """Checks that a RDF/XML file is valid."""
    errors = 0

    if lightrdf:
        parser = LightRDFParser()
        try:
            for triple in parser.parse(file):
                pass
            print("LightRDF: OK")
        except Exception:
            print("LightRDF: FAIL")
            errors += 1

    if rdflib:
        try:
            Graph().parse(file)
            print("RDFLib: OK")
        except Exception:
            print("RDFLib: FAIL")
            errors += 1

    if jena:
        riot = shutil.which("riot")
        if riot is None:
            print("Jena: Not available")
        else:
            ret = subprocess.run([riot, "--validate", file], capture_output=True)
            if ret.returncode == 0:
                print("Jena: OK")
            else:
                print("Jena: FAIL")
                errors += 1

    if errors > 0:
        raise click.ClickException(f"RDF/XML errors found in {file}")


@main.command()
@click.option(
    "--tools/--no-tools", default=True, help="Print informations about available tools."
)
def info(tools) -> None:
    """Print informations about the Ontology Development Kit backend."""
    print(f"ODK Core {__version__}")
    backend_info = shutil.which("odk-info")
    if backend_info is not None:
        cmd = [backend_info]
        if tools:
            cmd.append("--tools")
        subprocess.run(cmd)


@main.command()
@click.argument("url")
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    help="""Write the downloaded file to the specified location.
            The default is derived from the URL.""",
)
@click.option(
    "-r",
    "--reference",
    type=click.Path(path_type=Path),
    help="""Use the specified file as reference to decide whether to
            download the file again. The default is to use the file
            specified with the --output option.""",
)
@click.option(
    "-i",
    "--cache-info",
    type=click.Path(path_type=Path),
    help="""Read/write cache data from/to the specified file. The
            default is the same location as specified with the
            --reference option plus an added '.info' extension.""",
)
@click.option(
    "--max-retry",
    default=4,
    metavar="N",
    help="""Retry at most N times. Default is 4. Set to zero to disable retrying.""",
)
@click.option(
    "--try-gzip/--no-try-gzip",
    default=True,
    help="""Given the URL "U", automatically attempt to download "U.gz",
            then fallback to "U". This is enabled by default, unless the
            provided URL already points to a compressed file.""",
)
def download(url, output, reference, cache_info, max_retry, try_gzip) -> None:
    """Download a file."""

    urlpath = Path(urlparse(url).path)
    compression = Compression.from_extension(urlpath)

    attempts: List[Tuple[str, Compression]] = []
    if compression == Compression.NONE and try_gzip:
        attempts.append((url + ".gz", Compression.GZIP))
    attempts.append((url, compression))

    if output is None:
        output = Path(urlpath.name)
        if not output.name:
            raise click.ClickException(
                f"Explicit output name required for downloading from {url}"
            )
    if reference is None:
        reference = output
    if cache_info is None:
        cache_info = output.with_suffix(output.suffix + ".info")

    info = RemoteFileInfo()
    if reference.exists():
        info.from_cache_file(cache_info)
        if reference != output and output.exists():
            output.unlink()

    try:
        for u, c in attempts:
            status = download_file(u, output, info, max_retry, c)
            if status == 200:
                info.to_file(cache_info)
                return
            elif status == 304:
                return
        if status == 404:  # Last attempt failed
            raise click.ClickException(f"Cannot download {url}: 404 Not Found")
    except DownloadError as e:
        raise click.ClickException(f"Cannot download {url}: {e}")
