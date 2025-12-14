# odkcore - Ontology Development Kit Core
# Copyright © 2025 ODK Developers
#
# This file is part of the ODK Core project and distributed under the
# terms of a 3-clause BSD license. See the LICENSE file in that project
# for the detailed conditions.

import glob
import logging
import os
import shutil
import sys
from pathlib import Path
from shutil import copy

import click
import yaml

from .config import ConfigurationError, load_config, load_config_dict, save_config
from .setup import ODKEnvironment
from .template import DEFAULT_TEMPLATE_DIR, Generator, InstallPolicy
from .util import runcmd


@click.group()
def main():
    logging.basicConfig(level=logging.INFO)


@main.command()
@click.option(
    "-C",
    "--config",
    type=click.Path(exists=True),
    default="config.yaml",
    help="The ODK configuration file (default: config.yaml).",
)
@click.option(
    "-T",
    "--templatedir",
    default=DEFAULT_TEMPLATE_DIR,
    type=click.Path(file_okay=False, dir_okay=True, exists=True),
    help="The directory containing the templates.",
)
@click.option(
    "-n",
    "--name",
    default="src/ontology/Makefile",
    metavar="TEMPLATE",
    help="The file to generate (default: src/ontology/Makefile).",
)
@click.option(
    "-o",
    "--output",
    type=click.File("w"),
    default=sys.stdout,
    help="Write to the specified file. Default is to write to standard output.",
)
def generate_file(config, templatedir, name, output):
    """Generates a single template-derived file.

    This is for testing purposes only.
    """
    try:
        mg = Generator(load_config(config), templatedir)
    except ConfigurationError as ce:
        raise click.ClickException(ce)
    output.write(mg.generate_from_name(name))


@main.command()
@click.option(
    "-C",
    "--config",
    type=click.Path(exists=True),
    default="config.yaml",
    help="The ODK configuration file (default: config.yaml).",
)
@click.option(
    "-o",
    "--output",
    type=click.File("w"),
    default=sys.stdout,
    help="Write to the specified file. Default is to write to standard output.",
)
def export_project(config, output):
    """Exports the full configuration for a project.

    This creates a configuration file containing all settings for the
    project (including settings with default values). This is for
    testing purposes only.
    """
    try:
        mg = Generator(load_config(config))
    except ConfigurationError as ce:
        raise click.ClickException(ce)
    save_config(mg.project, output)


@main.command()
@click.option(
    "-C",
    "--config",
    type=click.Path(exists=True),
    default="config.yaml",
    help="The ODK configuration file (default: config.yaml).",
)
@click.option(
    "-o",
    "--output",
    type=click.File("w"),
    default=sys.stdout,
    help="Write to the specified file. Default is to write to standard output.",
)
def update_config(config, output):
    """Updates a configuration file to account for renamed or moved options."""
    try:
        cfg = load_config_dict(config)[0]
    except ConfigurationError as ce:
        raise click.ClickException(ce)
    output.write(yaml.dump(cfg, default_flow_style=False))


@main.command()
@click.option("-T", "--templatedir", default=DEFAULT_TEMPLATE_DIR)
def update(templatedir):
    """Updates a pre-existing repository.

    This command is expected to be run from within the
    ``src/ontology directory`` of an existing ODK repository (the
    directory containing the configuration file).
    """
    config_matches = list(glob.glob("*-odk.yaml"))
    if len(config_matches) == 0:
        raise click.ClickException("No ODK configuration file found")
    elif len(config_matches) > 1:
        raise click.ClickException("More than ODK configuration file found")
    config = config_matches[0]
    try:
        mg = Generator(load_config(config), templatedir)
    except ConfigurationError as ce:
        raise click.ClickException(ce)
    project = mg.project

    # When updating, for most files, we only install them if
    # they do not already exist in the repository (typically
    # because they are new files that didn't exist in the
    # templates of the previous version of the ODK). But a
    # handful of files are not reinstalled even if they are
    # missing (e.g. DOSDP example files) or on the contrary
    # always reinstalled to overwrite any local changes (e.g.
    # the main Makefile). We declare the corresponding policies.
    policies = [
        ("CODE_OF_CONDUCT.md", InstallPolicy.NEVER),
        ("CONTRIBUTING.md", InstallPolicy.NEVER),
        ("issue_template.md", InstallPolicy.NEVER),
        ("README.md", InstallPolicy.NEVER),
        ("src/patterns/data/default/example.tsv", InstallPolicy.NEVER),
        ("src/patterns/dosdp-patterns/example.yaml", InstallPolicy.NEVER),
        ("src/ontology/Makefile", InstallPolicy.ALWAYS),
        ("src/ontology/run.sh", InstallPolicy.ALWAYS),
        ("src/ontology/catalog-v001.xml", InstallPolicy.NEVER),
        ("src/sparql/*", InstallPolicy.ALWAYS),
        ("docs/odk-workflows/*", InstallPolicy.ALWAYS),
        (".gitignore", InstallPolicy.NEVER),
    ]
    if "github_actions" in project.ci:
        for workflow in ["qc", "diff", "release-diff"]:
            if workflow in project.workflows:
                policies.append(
                    (".github/workflows/" + workflow + ".yml", InstallPolicy.ALWAYS)
                )
        if project.documentation is not None and "docs" in project.workflows:
            policies.append((".github/workflows/docs.yml", InstallPolicy.ALWAYS))
    if not project.robot.report.get("custom_profile", False):
        policies.append(("src/ontology/profile.txt", InstallPolicy.NEVER))

    # Proceed with template instantiation, using the policies
    # declared above. We instantiate directly at the root of
    # the repository -- no need for a staging directory.
    mg.install_template_files("../..", policies)

    # Special procedures to update some ODK-managed files that
    # may have been manually edited.
    mg.update_gitignore(templatedir + "/.gitignore.jinja2", "../../.gitignore")

    if project.manage_import_declarations:
        mg.update_xml_catalog(
            templatedir + "/src/ontology/catalog-v001.xml.jinja2", "catalog-v001.xml"
        )
        mg.update_import_declarations()
    else:
        print("WARNING: You may need to update the -edit file and the XML catalog")
        print("         if you have added/removed/modified any import or component.")

    print("WARNING: This file should be manually migrated: mkdocs.yaml")
    if "github_actions" in project.ci and "qc" not in project.workflows:
        print("WARNING: Your QC workflows have not been updated automatically.")
        print(
            "         Please update the ODK version number in .github/workflows/qc.yml"
        )
    print("Ontology repository update successfully completed.")


@main.command()
@click.option(
    "-C",
    "--config",
    type=click.Path(exists=True),
    help="""The ODK configuration file.
            This is optional, configuration options can also be passed
            on the command line, but an explicit configuration file is
            prefered.""",
)
@click.option(
    "-c",
    "--clean/--no-clean",
    default=False,
    help="Cleans the target directory prior to seeding.",
)
@click.option("-T", "--templatedir", default=DEFAULT_TEMPLATE_DIR)
@click.option(
    "-D",
    "--outdir",
    default=None,
    metavar="DIR",
    help="The target directory. The default is target/ID, where ID is the handle of the new ontology.",
)
@click.option(
    "-d",
    "--dependencies",
    multiple=True,
    metavar="ID",
    help="Adds the specified ontology as an import.",
)
@click.option("-t", "--title", type=str, help="The title of the new ontology.")
@click.option("-u", "--user", type=str, help="The name of the repository owner.")
@click.option(
    "-s",
    "--source",
    type=click.Path(exists=True),
    help="""Path to an existing source for the ontology edit file.
            If not specified, a stub ontology will be created.""",
)
@click.option("-v", "--verbose", count=True)
@click.option(
    "-g",
    "--skipgit",
    default=False,
    is_flag=True,
    help="Skip building and committing the initial release.",
)
@click.option(
    "-n", "--gitname", default=None, help="Git user name for the initial commit."
)
@click.option(
    "-e", "--gitemail", default=None, help="Git email for the initial commit."
)
@click.option(
    "-r",
    "--commit-artefacts",
    default=False,
    is_flag=True,
    help="Commits release artefacts into the repository.",
)
@click.argument("repo", nargs=-1)
def seed(
    config,
    clean,
    outdir,
    templatedir,
    dependencies,
    title,
    user,
    source,
    verbose,
    repo,
    skipgit,
    gitname,
    gitemail,
    commit_artefacts,
):
    """Seeds an ontology project."""
    tgts = []
    if len(repo) > 0:
        if len(repo) > 1:
            raise click.ClickException("max one repo; current={}".format(repo))
        repo = repo[0]
    try:
        project = load_config(
            config, imports=dependencies, title=title, org=user, repo=repo
        )
        mg = Generator(project, templatedir)
    except ConfigurationError as ce:
        raise click.ClickException(ce)
    if project.id is None or project.id == "":
        project.id = repo
    if outdir is None:
        outdir = "target/{}".format(project.id)
    if not skipgit:
        if "GIT_AUTHOR_NAME" not in os.environ and not gitname:
            raise click.ClickException(
                "missing Git username; set GIT_AUTHOR_NAME or use --gitname"
            )
        if "GIT_AUTHOR_EMAIL" not in os.environ and not gitemail:
            raise click.ClickException(
                "missing Git email; set GIT_AUTHOR_EMAIL or use --gitemail"
            )
    if clean:
        if os.path.exists(outdir):
            shutil.rmtree(outdir)
    if not os.path.exists(outdir):
        os.makedirs(outdir, exist_ok=True)
    if not os.path.exists(templatedir) and templatedir == "/tools/templates/":
        logging.info("No templates folder in /tools/; assume not in docker context")
        templatedir = "./template"
    policies = []
    if not project.robot.report.get("custom_profile", False):
        policies.append(("src/ontology/profile.txt", InstallPolicy.NEVER))
    tgts += mg.install_template_files(outdir, policies)

    tgt_project_file = "{}/project.yaml".format(outdir)
    if project.export_project_yaml:
        with open(tgt_project_file, "w") as f:
            save_config(project, f)
        tgts.append(tgt_project_file)
    if source is not None:
        copy(
            source,
            "{}/src/ontology/{}-edit.{}".format(
                outdir, project.id, project.edit_format
            ),
        )
    odk_config_file = "{}/src/ontology/{}-odk.yaml".format(outdir, project.id)
    tgts.append(odk_config_file)
    if config is not None:
        copy(config, odk_config_file)
    else:
        with open(odk_config_file, "w") as f:
            save_config(project, f)
    logging.info("Created files:")
    for tgt in tgts:
        logging.info("  File: {}".format(tgt))
    if not skipgit:
        if gitname is not None:
            os.environ["GIT_AUTHOR_NAME"] = gitname
            os.environ["GIT_COMMITTER_NAME"] = gitname
        if gitemail is not None:
            os.environ["GIT_AUTHOR_EMAIL"] = gitemail
            os.environ["GIT_COMMITTER_EMAIL"] = gitemail
        runcmd(
            "cd {dir} && git init -b {branch} && git add {files} && git commit -m 'initial commit'".format(
                dir=outdir,
                branch=project.git_main_branch,
                files=" ".join([t.replace(outdir, ".", 1) for t in tgts]),
            )
        )
        runcmd(
            "cd {dir}/src/ontology && make all_assets copy_release_files".format(
                dir=outdir
            )
        )
        if commit_artefacts:
            runcmd(
                "cd {dir}/src/ontology "
                "&& for asset in $(make show_release_assets) ; do git add -f $asset ; done".format(
                    dir=outdir
                )
            )
        runcmd(
            "cd {dir} && if [ -n \"$(git status -s)\" ]; then git commit -a -m 'initial build' ; fi".format(
                dir=outdir
            )
        )
        print("\n\n####\nNEXT STEPS:")
        print(
            " 0. Examine {} and check it meets your expectations. If not blow it away and start again".format(
                outdir
            )
        )
        print(" 1. Go to: https://github.com/new")
        print(
            " 2. The owner MUST be {org}. The Repository name MUST be {repo}".format(
                org=project.github_org, repo=project.repo
            )
        )
        print(" 3. Do not initialize with a README (you already have one)")
        print(" 4. Click Create")
        print(
            " 5. See the section under '…or push an existing repository from the command line'"
        )
        print("    E.g.:")
        print("cd {}".format(outdir))
        print(
            "git remote add origin git@github.com:{org}/{repo}.git".format(
                org=project.github_org, repo=project.repo
            )
        )
        print("git push -u origin {branch}\n".format(branch=project.git_main_branch))
        print("BE BOLD: you can always delete your repo and start again\n")
        print("")
        print("FINAL STEPS:")
        print("Follow your customized instructions here:\n")
        print(
            "    https://github.com/{org}/{repo}/blob/main/src/ontology/README-editors.md".format(
                org=project.github_org, repo=project.repo
            )
        )
    else:
        print(
            "Repository files have been successfully copied, but no git commands have been run."
        )


@main.command()
@click.argument(
    "target", type=click.Path(dir_okay=True, file_okay=False, path_type=Path)
)
@click.option(
    "--force",
    default=False,
    is_flag=True,
    help="Install all files even if they are already available.",
)
def install(target: Path, force: bool) -> None:
    """Installs a ODK environment."""
    odkenv = ODKEnvironment(target)
    odkenv.install(force)


if __name__ == "__main__":
    main()
