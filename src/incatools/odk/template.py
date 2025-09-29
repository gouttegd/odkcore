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
from typing import IO, List, Optional, Tuple
from xml.etree import ElementTree

from defusedxml import ElementTree as DefusedElementTree
from jinja2 import Template

from .model import OntologyProject
from .util import runcmd

TEMPLATE_SUFFIX = ".jinja2"
DEFAULT_TEMPLATE_DIR = Path(__file__).parent.resolve() / "templates"
RESOURCES_DIR = Path(os.environ.get("ODK_RESOURCES_DIR", "/tools/resources"))


class InstallPolicy(Enum):
    """A policy to decide whether to install a given file or not."""

    IF_MISSING = 0
    """Install the file only if it does not already exist."""

    ALWAYS = 1
    """Always install the file, overwriting any existing file."""

    NEVER = 2
    """Never install the file."""


PolicyList = List[Tuple[str, InstallPolicy]]


def _must_install_file(
    templatefile: str, targetfile: str, policies: PolicyList
) -> bool:
    """Determines whether a given file should be installed.

    Given a template filename, this function determines whether the file
    should be installed according to any per-file policy.

    policies is a list of (PATTERN,POLICY) tuples where PATTERN is
    a shell-like globbing pattern and POLICY is the update policy
    that should be applied to any template whose pathname matches
    the pattern.

    Patterns are tested in the order they are found in the list,
    and the first match takes precedence over any subsequent match.
    If there is no match, the default policy is IF_MISSING.

    :param templatefile: The name of the template, relative to the root
        template directory.
    :param targetfile: Where the template should be instanciated, as
        either an absolute pathname or a pathname relative to the
        current working directory.
    :param policies: The list of per-file policies as explained above.

    :returns: True if the file is to be installed, False otherwise.
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


@dataclass
class Generator(object):
    """Generates ontology project artefacts from Jinja2 templates."""

    project: OntologyProject
    templatedir: Path

    def __init__(self, project: OntologyProject, templatedir: Optional[str] = None):
        """Creates a new instance for the specified ontology project.

        :param project: The project for which to generate artefacts.
        :param templatedir: The directory containing the Jinja2 templates.
            The default is to use the templates bundled with the package.
        """
        self.project = project
        if templatedir is not None:
            self.templatedir = Path(templatedir)
        else:
            self.templatedir = DEFAULT_TEMPLATE_DIR

    def generate(self, input: Path | str) -> str:
        """Renders one template file.

        :param input: The path to the template to instanciate.

        :returns: The text of the instantiated template.
        """
        with open(input) as file_:
            template = Template(file_.read())
            if "ODK_VERSION" in os.environ:
                return template.render(
                    project=self.project, env={"ODK_VERSION": os.getenv("ODK_VERSION")}
                )
            else:
                return template.render(project=self.project)

    def generate_from_name(self, name: str) -> str:
        """Renders one template.

        This method differs from ``generate`` in that it expects the
        basename of a template file, relative to the root of the
        template directory and without any suffix. Basically, this is
        the name of the file as it would appear to an external user with
        no knowledge of how the templating system works (e.g.
        ``src/ontology/Makefile``).

        :param name: The name of the template to generate.

        :returns: The text of the instantiated template.
        """
        template_file = self.templatedir / (name + TEMPLATE_SUFFIX)
        if not template_file.exists():
            raise FileNotFoundError(f"No {name} template found")
        return self.generate(template_file)

    def unpack_files(self, basedir: str, txt: str, policies: PolicyList) -> List[str]:
        """Unpack all files found in a dynamic files pack.

        A "dynamic files pack" uses a custom tar-like format in which
        multiple file paths can be specified, separated by ``^^^`` tags.

        See the ``_dynamic_files.jinja2`` file in the templates
        directory for an example of this.

        :param basedir: The root directory where any files should be
            installed.
        :param txt: The text of the dynamic files pack.
        :param policies: The list of per-file install policies.

        :returns: The names of the files that were effectively installed.
        """
        MARKER = "^^^ "
        lines = txt.split("\n")
        f: Optional[IO] = None
        tgts = []
        ignore = False
        for line in lines:
            if line.startswith(MARKER):
                # Close previous file, if any
                if f is not None:
                    f.close()
                filename = line.replace(MARKER, "")
                path = os.path.join(basedir, filename)
                ignore = not _must_install_file(filename, path, policies)
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
        if f is not None:
            f.close()
        return tgts

    def get_template_name(self, pathname: str) -> str:
        """Gets the user-visible name of a template file.

        For example, if the pathname is::

          /tools/template/src/ontology/run.sh.jinja2

        this will return (assuming ``/tools/template`` is the template
        directory)::

          src/ontology/run.sh

        :param pathname: The full pathname of a template file.

        :returns: The pathname of the template file, relative to the
            template directory and without any template suffix.
        """
        name = pathname.replace(self.templatedir.as_posix(), "")
        if len(name) > 0 and name[0] == "/":
            name = name[1:]
        if name.endswith(TEMPLATE_SUFFIX):
            name = name.replace(TEMPLATE_SUFFIX, "")
        return name

    def install_template_files(self, targetdir: str, policies: PolicyList) -> List[str]:
        """Installs all template-derived files into a directory.

        :param targetdir: The base directory where all files should be
            installed.
        :param policies: The list of per-file install policies. See the
            documentation of the ``_must_install_file`` function.

        :returns: The names of the files that were effectively installed.
        """
        tgts = []
        for root, subdirs, files in os.walk(self.templatedir):
            tdir = root.replace(self.templatedir.as_posix(), targetdir + "/")
            os.makedirs(tdir, exist_ok=True)

            # first copy plain files...
            for f in [f for f in files if not f.endswith(TEMPLATE_SUFFIX)]:
                srcf = os.path.join(root, f)
                tgtf = os.path.join(tdir, f)
                if _must_install_file(self.get_template_name(srcf), tgtf, policies):
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
                elif _must_install_file(
                    self.get_template_name(srcf), derived_file, policies
                ):
                    logging.info("  Compiling: {} -> {}".format(srcf, derived_file))
                    with open(derived_file, "w") as s:
                        s.write(self.generate(srcf))
                    tgts.append(derived_file)
                    copymode(srcf, derived_file)
        return tgts

    def update_gitignore(self, template_file: str, target_file: str) -> None:
        """Updates a potentially existing .gitignore file.

        This method will update a ``.gitignore`` file to ensure it
        contains all the ODK-mandated entries, while preserving any
        non-ODK-managed contents.

        :param template_file: Path to the .gitignore template.
        :param target_file: Path to the file to update.
        """
        if not os.path.exists(template_file):
            # Should not happen as we should always have a .gitignore
            # template, but just in case
            return

        existing_lines = []
        if os.path.exists(target_file):
            with open(target_file, "r") as f:
                exclude = False
                for line in [ln.strip() for ln in f]:
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
            for line in [ln for ln in existing_lines if ln not in already_written]:
                f.write(line + "\n")

    def update_xml_catalog(self, template_file: str, target_file: str) -> None:
        """Updates a potentially existing XML catalog file.

        This method will update a XML catalog file to ensure it contains
        all entries required by ODK workflows (e.g., redirections for
        all import modules described in the project configuration) while
        preserving any non-ODK-managed contents.

        :param template_file: Path to the XML catalog template.
        :param target_file: Path to the file to update.
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

    def update_import_declarations(self) -> None:
        """Updates import declarations within the project's edit file.

        This method will update the project's -edit file to ensure it
        contains import declarations for all the import modules,
        components, and pattern-derived files declared in the project
        configuration.
        """
        base = self.project.uribase + "/"
        if self.project.uribase_suffix is not None:
            base += self.project.uribase_suffix
        else:
            base += self.project.id

        if "ROBOT_PLUGINS_DIRECTORY" not in os.environ:
            plugins_dir = RESOURCES_DIR / "robot/plugins"
            os.environ["ROBOT_PLUGINS_DIRECTORY"] = plugins_dir.as_posix()

        ignore_missing_imports = "-Dorg.semantic.web.owlapi.model.parameters.ConfigurationOptions.MISSING_IMPORT_HANDLING_STRATEGY=SILENT"
        if "ROBOT_JAVA_ARGS" in os.environ:
            os.environ["ROBOT_JAVA_ARGS"] += " " + ignore_missing_imports
        else:
            os.environ["ROBOT_JAVA_ARGS"] = ignore_missing_imports

        cmd = f"robot odk:import -i {self.project.id}-edit.{self.project.edit_format} --exclusive true"
        if self.project.import_group is not None:
            if self.project.import_group.use_base_merging:
                cmd += f" --add {base}/imports/merged_import.owl"
            else:
                for product in self.project.import_group.products:
                    cmd += f" --add {base}/imports/{product.id}_import.owl"
        if self.project.components is not None:
            for component in self.project.components.products:
                cmd += f" --add {base}/components/{component.filename}"
        if self.project.use_dosdps:
            cmd += f" --add {base}/patterns/definitions.owl"
            if self.project.import_pattern_ontology:
                cmd += f" --add {base}/patterns/pattern.owl"

        if self.project.edit_format == "owl":
            cmd += f" convert -f ofn -o {self.project.id}-edit.owl"
        else:
            cmd += f" convert --check false -o {self.project.id}-edit.obo"
        runcmd(cmd)
