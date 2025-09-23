# odkcore - Ontology Development Kit Core
# Copyright © 2025 ODK Developers
#
# This file is part of the ODK Core project and distributed under the
# terms of a 3-clause BSD license. See the LICENSE file in that project
# for the detailed conditions.

import json
import logging
from hashlib import sha256
from typing import Any, Dict, List, Optional

import yaml
from dacite import from_dict

from .model import ImportGroup, OntologyProject, ImportProduct


def load_config(
    config_file: Optional[str] = None,
    imports: Optional[List[str]] = None,
    title: Optional[str] = None,
    org: Optional[str] = None,
    repo: Optional[str] = None,
) -> OntologyProject:
    """Parses a project.yaml file into a Ontology Project."""
    config_hash = None
    if config_file is None:
        project = OntologyProject()
    else:
        with open(config_file, "r") as stream:
            h = sha256()
            h.update(stream.read().encode())
            config_hash = h.hexdigest()
            stream.seek(0)
            obj = yaml.load(stream, Loader=yaml.FullLoader)
        update_stubs(obj)
        update_config_dict(obj)
        project = from_dict(data_class=OntologyProject, data=obj)
    if config_hash:
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
    """
    Updates a configuration dictionary to replace old-style "stubs".

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
        if not "products" in group:
            group["products"] = []
        stubs = group.get("ids")
        if isinstance(stubs, list):
            for stub in stubs:
                group["products"].append({"id": stub})


def update_config_dict(obj: Dict[str, Any]) -> None:
    """
    Updates a config dictionary to replace keys that have been renamed
    or moved.
    """
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
    """
    Gets the value of the key at the specified path, exploring
    subdictionaries recursively as needed. The terminal key, if found,
    is removed from the dictionary.

    For example,

      pop_key(my_dict, 'path.to.key')

    is equivalent to

      my_dict.get('path', {}).get('to', {}).pop('key', None)

    Returns None if any of the keys does not exist, or if one of the
    parent keys exists but is not a dictionary.
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
    """
    Puts a value in a dictionary at the specified path, going through
    subdictionaries recursively as needed.

    For example,

      put_key(my_dict, 'path.to.key', value)

    is almost equivalent to

      my_dict['path']['to']['key'] = value

    except that intermediate dictionaries are automatically created if
    they do not already exist.
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


def save_project_yaml(project: OntologyProject, path: str) -> None:
    """
    Saves an ontology project to a file in YAML format
    """
    # This is a slightly ridiculous bit of tomfoolery, but necessary
    # As PyYAML will attempt to save as a python object using !!,
    # so we must first serialize as JSON then parse than JSON to get
    # a class-free python dict tha can be safely saved
    json_str = project.to_json()
    json_obj = json.loads(json_str)
    with open(path, "w") as f:
        f.write(yaml.dump(json_obj, default_flow_style=False))
