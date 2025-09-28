# odkcore - Ontology Development Kit Core
# Copyright © 2025 ODK Developers
#
# This file is part of the ODK Core project and distributed under the
# terms of a 3-clause BSD license. See the LICENSE file in that project
# for the detailed conditions.

import json
import shutil
import subprocess
from pathlib import Path

import click
from lightrdf import Parser as LightRDFParser  # type: ignore
from rdflib import Graph

from . import __version__
from .template import DEFAULT_TEMPLATE_DIR, RESOURCES_DIR


@click.group()
def main() -> None:
    """Helper commands for ODK workflows."""
    pass


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
