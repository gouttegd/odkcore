# odkcore - Ontology Development Kit Core
# Copyright © 2025 ODK Developers
#
# This file is part of the ODK Core project and distributed under the
# terms of a 3-clause BSD license. See the LICENSE file in that project
# for the detailed conditions.

import fnmatch
import logging
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from shutil import copy, copymode
from typing import IO, List, Optional, Tuple, Union
from xml.etree import ElementTree

from defusedxml import ElementTree as DefusedElementTree
from jinja2 import Template

from .model import OntologyProject
from .util import runcmd

TEMPLATE_SUFFIX = ".jinja2"
DEFAULT_TEMPLATE_DIR = Path(__file__).parent.resolve() / "templates"


class InstallPolicy(Enum):
    IF_MISSING = 0
    ALWAYS = 1
    NEVER = 2


PolicyList = List[Tuple[str, InstallPolicy]]


@dataclass
class Generator(object):
    """
    Utility class for generating a variety of ontology project artefacts
    from jinja2 templates
    """

    project: OntologyProject
    templatedir: Path

    def __init__(self, project: OntologyProject, templatedir: Optional[str]):
        self.project = project
        if templatedir is not None:
            self.templatedir = Path(templatedir)
        else:
            self.templatedir = DEFAULT_TEMPLATE_DIR

    def generate(self, input: str) -> str:
        """
        Given a path to an input template, renders the template
        using the current execution context
        """
        with open(input) as file_:
            template = Template(file_.read())
            if "ODK_VERSION" in os.environ:
                return template.render(
                    project=self.project, env={"ODK_VERSION": os.getenv("ODK_VERSION")}
                )
            else:
                return template.render(project=self.project)

    def unpack_files(self, basedir: str, txt: str, policies: PolicyList) -> List[str]:
        """
        This unpacks a custom tar-like format in which multiple file paths
        can be specified, separated by ^^^s

        See the file template/_dynamic_files.jinja2 for an example of this
        """
        MARKER = "^^^ "
        lines = txt.split("\n")
        f: Optional[IO] = None
        tgts = []
        ignore = False
        for line in lines:
            if line.startswith(MARKER):
                # Close previous file, if any
                if f != None:
                    f.close()
                filename = line.replace(MARKER, "")
                path = os.path.join(basedir, filename)
                ignore = not must_install_file(filename, path, policies)
                if not ignore:
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    f = open(path, "w")
                    tgts.append(path)
                    logging.info("  Unpacking into: {}".format(path))
            elif not ignore:
                if f is None:
                    if line == "":
                        continue
                    else:
                        raise Exception(
                            'File marker "{}" required in "{}"'.format(MARKER, line)
                        )
                f.write(line + "\n")
        if f != None:
            f.close()
        return tgts

    def get_template_name(self, pathname: str) -> str:
        """Helper function to get the user-visible name of a template file from its complete pathname in the template directory.

        For example, if the pathname is
        "/tools/template/src/ontology/run.sh.jinja2", this will return
        "src/ontology/run.sh".
        """
        name = pathname.replace(self.templatedir.as_posix(), "")
        if len(name) > 0 and name[0] == "/":
            name = name[1:]
        if name.endswith(TEMPLATE_SUFFIX):
            name = name.replace(TEMPLATE_SUFFIX, "")
        return name

    def install_template_files(self, targetdir: str, policies: PolicyList):
        """
        Installs all template-derived files into a target directory.
        """
        tgts = []
        for root, subdirs, files in os.walk(self.templatedir):
            tdir = root.replace(self.templatedir.as_posix(), targetdir + "/")
            os.makedirs(tdir, exist_ok=True)

            # first copy plain files...
            for f in [f for f in files if not f.endswith(TEMPLATE_SUFFIX)]:
                srcf = os.path.join(root, f)
                tgtf = os.path.join(tdir, f)
                if must_install_file(self.get_template_name(srcf), tgtf, policies):
                    logging.info("  Copying: {} -> {}".format(srcf, tgtf))
                    # copy file directly, no template expansions
                    copy(srcf, tgtf)
                    tgts.append(tgtf)
            logging.info("Applying templates")
            # ...then apply templates
            for f in [f for f in files if f.endswith(TEMPLATE_SUFFIX)]:
                srcf = os.path.join(root, f)
                tgtf = os.path.join(tdir, f)
                derived_file = tgtf.replace(TEMPLATE_SUFFIX, "")
                if f.startswith("_dynamic"):
                    logging.info("  Unpacking: {}".format(derived_file))
                    tgts += self.unpack_files(tdir, self.generate(srcf), policies)
                elif must_install_file(
                    self.get_template_name(srcf), derived_file, policies
                ):
                    logging.info("  Compiling: {} -> {}".format(srcf, derived_file))
                    with open(derived_file, "w") as s:
                        s.write(self.generate(srcf))
                    tgts.append(derived_file)
                    copymode(srcf, derived_file)
        return tgts

    def update_gitignore(self, template_file: str, target_file: str) -> None:
        """
        Update a potentially existing .gitignore file while preserving
        its non-ODK-managed contents.
        """
        if not os.path.exists(template_file):
            # Should not happen as we should always have a .gitignore
            # template, but just in case
            return

        existing_lines = []
        if os.path.exists(target_file):
            with open(target_file, "r") as f:
                exclude = False
                for line in [l.strip() for l in f]:
                    if line == "# ODK-managed rules, do not modify":
                        exclude = True
                    elif line == "# End of ODK-managed rules":
                        exclude = False
                    elif not exclude:
                        existing_lines.append(line)

        already_written = {}
        with open(target_file, "w") as f:
            for line in self.generate(template_file).split("\n"):
                if len(line) > 0:
                    already_written[line] = 1
                f.write(line + "\n")
            for line in [l for l in existing_lines if l not in already_written]:
                f.write(line + "\n")

    def update_xml_catalog(self, template_file: str, target_file: str) -> None:
        """
        Updates a potentially existing XML catalog file while preserving
        its non-ODK-managed contents.
        """
        if not os.path.exists(template_file):
            return

        CATALOG_NS = "urn:oasis:names:tc:entity:xmlns:xml:catalog"
        XML_NS = "http://www.w3.org/XML/1998/namespace"
        CATALOG_GROUP = "{" + CATALOG_NS + "}group"
        CATALOG_URI = "{" + CATALOG_NS + "}uri"
        XML_BASE = "{" + XML_NS + "}base"

        template_entries = {}
        ElementTree.register_namespace("", CATALOG_NS)

        def process_children(node):
            to_remove = []
            for child in node:
                if child.tag == CATALOG_URI:
                    # Remove the entry if it corresponds to one already set
                    # by the ODK-managed group.
                    name = child.attrib.get("name")
                    uri = child.attrib.get("uri")
                    if name and uri and name + "@" + uri in template_entries:
                        to_remove.append(child)
                elif child.tag == CATALOG_GROUP:
                    if child.attrib.get("id") == "odk-managed-catalog":
                        # Completely exclude that group, so that it is
                        # entirely replaced by the one from the template.
                        to_remove.append(child)
                    else:
                        # Some existing catalog groups have an empty
                        # xml:base="" attribute; such an attribute is
                        # incorrect according to the XML spec.
                        if child.attrib.get(XML_BASE) == "":
                            child.attrib.pop(XML_BASE)
                        process_children(child)
            for child in to_remove:
                node.remove(child)

        template_root = DefusedElementTree.fromstring(self.generate(template_file))
        if os.path.exists(target_file):
            # Make a list of the entries in the managed catalog
            odk_managed_group = template_root.find(CATALOG_GROUP)
            if odk_managed_group is not None:
                for managed_uri in odk_managed_group.findall(CATALOG_URI):
                    template_entries[
                        managed_uri.attrib["name"] + "@" + managed_uri.attrib["uri"]
                    ] = 1

            # Add the contents of the existing catalog
            existing_tree = DefusedElementTree.parse(target_file)
            process_children(existing_tree.getroot())
            children = existing_tree.getroot()
            if children is not None:
                for child in children:
                    template_root.append(child)

        new_catalog = ElementTree.ElementTree(template_root)
        ElementTree.indent(new_catalog, space="  ", level=0)
        new_catalog.write(target_file, encoding="UTF-8", xml_declaration=True)

    def update_import_declarations(
        self, project: OntologyProject, pluginsdir: str = "/tools/robot-plugins"
    ) -> None:
        """
        Updates the project's -edit file to ensure it contains import
        declarations for all the import modules, components, and
        pattern-derived files declared in the ODK configuration.
        """
        base = project.uribase + "/"
        if project.uribase_suffix is not None:
            base += project.uribase_suffix
        else:
            base += project.id

        if not "ROBOT_PLUGINS_DIRECTORY" in os.environ:
            os.environ["ROBOT_PLUGINS_DIRECTORY"] = pluginsdir

        ignore_missing_imports = "-Dorg.semantic.web.owlapi.model.parameters.ConfigurationOptions.MISSING_IMPORT_HANDLING_STRATEGY=SILENT"
        if "ROBOT_JAVA_ARGS" in os.environ:
            os.environ["ROBOT_JAVA_ARGS"] += " " + ignore_missing_imports
        else:
            os.environ["ROBOT_JAVA_ARGS"] = ignore_missing_imports

        cmd = f"robot odk:import -i {project.id}-edit.{project.edit_format} --exclusive true"
        if project.import_group is not None:
            if project.import_group.use_base_merging:
                cmd += f" --add {base}/imports/merged_import.owl"
            else:
                for product in project.import_group.products:
                    cmd += f" --add {base}/imports/{product.id}_import.owl"
        if project.components is not None:
            for component in project.components.products:
                cmd += f" --add {base}/components/{component.filename}"
        if project.use_dosdps:
            cmd += f" --add {base}/patterns/definitions.owl"
            if project.import_pattern_ontology:
                cmd += f" --add {base}/patterns/pattern.owl"

        if project.edit_format == "owl":
            cmd += f" convert -f ofn -o {project.id}-edit.owl"
        else:
            cmd += f" convert --check false -o {project.id}-edit.obo"
        runcmd(cmd)


def must_install_file(templatefile: str, targetfile: str, policies: PolicyList) -> bool:
    """
    Given a template filename, indicate whether the file should be
    installed according to any per-file policy.

    policies is a list of (PATTERN,POLICY) tuples where PATTERN is
    a shell-like globbing pattern and POLICY is the update policy
    that should be applied to any template whose pathname matches
    the pattern.

    Patterns are tested in the order they are found in the list,
    and the first match takes precedence over any subsequent match.
    If there is no match, the default policy is IF_MISSING.

    Valid policies are:
    * IF_MISSING: install the file if it does not already exist
    * ALWAYS: always install the file, overwrite any existing file
    * NEVER: never install the file
    """
    policy = InstallPolicy.IF_MISSING
    for pattern, pattern_policy in policies:
        if fnmatch.fnmatch(templatefile, pattern):
            policy = pattern_policy
            break
    if policy == InstallPolicy.ALWAYS:
        return True
    elif policy == InstallPolicy.NEVER:
        return False
    else:
        return not os.path.exists(targetfile)
