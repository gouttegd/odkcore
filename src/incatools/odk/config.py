# odkcore - Ontology Development Kit Core
# Copyright © 2025 ODK Developers
#
# This file is part of the ODK Core project and distributed under the
# terms of a 3-clause BSD license. See the LICENSE file in that project
# for the detailed conditions.

import logging
from hashlib import sha256
from typing import Any, Dict, List, Optional, TextIO, Tuple

import yaml
from dacite import from_dict

from .model import ImportGroup, ImportProduct, OntologyProject


class ConfigurationError(Exception):
    """Error thrown on any problem with a ODK configuration file."""

    message: str

    def __init__(self, msg: str):
        self.message = msg

    def __str__(self):
        return f"ODK configuration error: {self.message}"

    @staticmethod
    def from_yaml_error(file: str, exc: yaml.YAMLError) -> "ConfigurationError":
        """Turns a YAML parser error into a ConfigurationError.

        :param file: The file that triggered the parsing error.
        :param exc: The YAML parsing error.

        :returns: The ODK-specific configuration error.
        """
        msg = "Cannot parse configuration file"
        if hasattr(exc, "problem_mark") and hasattr(exc, "problem"):
            err_line = exc.problem_mark.line
            err_column = exc.problem_mark.column
            msg += f"\nLine {err_line + 1}, column {err_column + 1}: {exc.problem}"
            with open(file, "r") as f:
                line = f.readline()
                linenr = 1
                while line and linenr <= err_line:
                    linenr += 1
                    line = f.readline()
            msg += "\n" + line.rstrip()
            msg += "\n" + " " * err_column + "^"
        else:
            msg += ": Unknown YAML error"
        return ConfigurationError(msg)


def load_config_dict(config_file: str) -> Tuple[Dict[str, Any], str]:
    """Parses a ODK configuration file into a dictionary.

    This method is primarily intended for internal usage, but may be
    useful for client code that needs to access the "raw" dictionary
    representing the ODK configuration, rather than a OntologyProject
    object.

    The parsed dictionary will be automatically updated to reflect the
    current configuration model, prior to being returned.

    :param config_file: The configuration file to parse.

    :returns: A tuple (D,H) were D is the configuration dictionary, and
        H is the SHA-256 hash of the configuration as read from file.
    """
    with open(config_file, "r") as f:
        h = sha256()
        h.update(f.read().encode())
        f.seek(0)
        try:
            obj = yaml.load(f, Loader=yaml.FullLoader)
        except yaml.YAMLError as exc:
            raise ConfigurationError.from_yaml_error(config_file, exc)
    update_config_dict(obj)
    return (obj, h.hexdigest())


def load_config(
    config_file: Optional[str] = None,
    imports: Optional[List[str]] = None,
    title: Optional[str] = None,
    org: Optional[str] = None,
    repo: Optional[str] = None,
) -> OntologyProject:
    """Parses a project.yaml file into a Ontology Project.

    :param config_file: Loads the project from the specified config file.
        If unset, a brand new project is created.
    :param imports: The imports the new project should use. If a config
        file is also used, the imports will be added to those already
        described in the configuration.
    :param title: The title of the new project. Will supersede any value
        set in the configuration file.
    :param org: The organisation owning the repository where the project
        will be hosted. Will supersede any value set in the configuration
        file.
    :param repo: The name of the repository where the project will be
        hosted. Will supersede any value set in the configuration file.

    :returns: The loaded ontology project.
    """
    if config_file is None:
        project = OntologyProject()
    else:
        obj, config_hash = load_config_dict(config_file)
        project = from_dict(data_class=OntologyProject, data=obj)
        project.config_hash = config_hash
    if title:
        project.title = title
    if org:
        project.github_org = org
    if repo:
        project.repo = repo
    if imports:
        if project.import_group is None:
            project.import_group = ImportGroup()
        for imp in imports:
            project.import_group.products.append(ImportProduct(id=imp))
    project.derive_fields()
    return project


def update_stubs(obj: Dict[str, Any]) -> None:
    """Updates a configuration dictionary to replace old-style "stubs".

    The ODK configuration file accepts two different ways of listing products
    within a group (e.g., imports).

    Either as an explicit list of product objects:

    ```
    import_group:
      products:
        - id: a-product
        - id: another-product
    ```

    Or as an implicit list of product IDs:

    ```
    import_group:
      ids:
        - a-product
        - another-product
    ```

    This function transforms the second form into the first one, which is
    the form expected by the model.

    :param obj: The dictionary to update.
    """
    for group_name in [
        "import_group",
        "subset_group",
        "pattern_pipelines_group",
        "sssom_mappingset_group",
        "bridge_group",
        "components",
    ]:
        if group_name not in obj:
            continue
        group = obj[group_name]
        if not isinstance(group, dict):
            continue
        if "products" not in group:
            group["products"] = []
        stubs = group.get("ids")
        if isinstance(stubs, list):
            for stub in stubs:
                group["products"].append({"id": stub})


def update_config_dict(obj: Dict[str, Any]) -> None:
    """Updates a config dictionary to the latest version of the model.

    The model for an ontology project (as defined in the model module)
    may change at anytime, but existing configuration files must remain
    usable. To achieve that, this method will silently update the
    configuration dictionary (as read from the configuration file) to
    replace keys that have been renamed or moved.

    The onus is on whoever introduces a change to the project model to
    update this function so that it can accomodates the change.

    :param obj: The dictionary to update.
    """
    # First take care of stubs, if needed
    update_stubs(obj)

    # Then all the other changes
    changes = [
        # old key path               new key path
        ("reasoner", "robot.reasoner"),
        ("obo_format_options", "robot.obo_format_options"),
        ("relax_options", "robot.relax_options"),
        ("reduce_options", "robot.reduce_options"),
        ("robot_plugins.plugins", "robot.plugins"),
        ("robot_plugins", None),
        ("robot_report", "robot.report"),
    ]
    for old, new in changes:
        v = pop_key(obj, old)
        if v is not None:
            if new is not None:
                logging.warning(f"Option {old} is deprecated, use {new} instead")
                put_key(obj, new, v)
            else:
                logging.warning(f"Option {old} is deprecated")


def pop_key(obj: Dict[str, Any], path: str) -> Optional[str]:
    """Gets the value of a key in a nested dictionary structure.

    This function will interpret any dot in the provided ``path`` as a
    jump into a nested dictionary.

    For example::

      pop_key(my_dict, 'path.to.key')

    is equivalent to::

      my_dict.get('path', {}).get('to', {}).pop('key', None)

    The terminal key, if found, is removed from the dictionary.

    :param obj: The top-level dictionary to query.
    :param path: The path identifying the key to retrieve.

    :returns: The retrieved value. May be None if any of the components
        of ``path`` does not exist, or if one the component exists but
        is not a dictionary.
    """
    components = path.split(".")
    n = len(components)
    for i, component in enumerate(components):
        if i < n - 1:
            tmp = obj.get(component)
            if not isinstance(tmp, dict):
                return None
            obj = tmp
        else:
            return obj.pop(component, None)
    return None


def put_key(obj: Dict[str, Any], path: str, value: Any) -> None:
    """Puts a value in a nested dictionary structure.

    This function will interpret any dot in the provided ``path`` as a
    jump into a nested dictionary.

    For example::

      put_key(my_dict, 'path.to.key', value)

    is almost equivalent to::

      my_dict['path']['to']['key'] = value

    except that intermediate dictionaries are automatically created if
    they do not already exist.

    :param obj: The top-level dictionary to modify.
    :param path: The path identifying the key to set.

    :param value: The new value to set.
    """
    components = path.split(".")
    n = len(components)
    for i, component in enumerate(components):
        if i < n - 1:
            if component not in obj:
                obj[component] = {}
            obj = obj[component]
        else:
            obj[component] = value


def save_config(project: OntologyProject, output: TextIO) -> None:
    """Saves an ontology project to a file in YAML format.

    :param project: The project to save.
    :param output: The file-like object where to save the project.
    """
    output.write(yaml.dump(project.to_dict(), default_flow_style=False))
