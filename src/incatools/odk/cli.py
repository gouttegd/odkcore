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
from shutil import copy

import click
import yaml

from .config import load_config, save_config, update_config_dict
from .template import DEFAULT_TEMPLATE_DIR, Generator, InstallPolicy
from .util import format_yaml_error, runcmd


@click.group()
def main():
    pass


@main.command()
@click.option("-C", "--config", type=click.Path(exists=True))
@click.option("-T", "--templatedir", default=DEFAULT_TEMPLATE_DIR)
@click.option("-i", "--input", type=click.Path(exists=True))
@click.option("-o", "--output")
def create_makefile(config, templatedir, input, output):
    """
    For testing purposes
    """
    try:
        mg = Generator(load_config(config))
    except yaml.YAMLError as exc:
        raise click.ClickException(format_yaml_error(config, exc))
    print(mg.generate("{}/src/ontology/Makefile.jinja2".format(templatedir)))


@main.command()
@click.option("-C", "--config", type=click.Path(exists=True))
@click.option("-T", "--templatedir", default=DEFAULT_TEMPLATE_DIR)
@click.option("-i", "--input", type=click.Path(exists=True))
@click.option("-o", "--output")
def create_dynfile(config, templatedir, input, output):
    """
    For testing purposes
    """
    try:
        mg = Generator(load_config(config))
    except yaml.YAMLError as exc:
        raise click.ClickException(format_yaml_error(config, exc))
    print(mg.generate("{}/_dynamic_files.jinja2".format(templatedir)))


@main.command()
@click.option("-C", "--config", type=click.Path(exists=True))
@click.option("-o", "--output", required=True)
def export_project(config, output):
    """
    For testing purposes
    """
    try:
        mg = Generator(load_config(config))
    except yaml.YAMLError as exc:
        raise click.ClickException(format_yaml_error(config, exc))
    save_config(mg.project, output)


@main.command()
@click.option("-C", "--config", type=click.Path(exists=True))
@click.option("-o", "--output", required=True)
def update_config(config, output):
    """
    Updates a configuration file to account for renamed or moved options.
    """
    with open(config, "r") as f:
        cfg = yaml.load(f, Loader=yaml.FullLoader)
    update_config_dict(cfg)
    with open(output, "w") as f:
        f.write(yaml.dump(cfg, default_flow_style=False))


@main.command()
@click.option("-T", "--templatedir", default=DEFAULT_TEMPLATE_DIR)
def update(templatedir):
    """
    Updates a pre-existing repository. This command is expected to be
    run from within the src/ontology directory (the directory
    containing the configuration file).
    """
    config_matches = list(glob.glob("*-odk.yaml"))
    if len(config_matches) == 0:
        raise click.ClickException("No ODK configuration file found")
    elif len(config_matches) > 1:
        raise click.ClickException("More than ODK configuration file found")
    config = config_matches[0]
    try:
        mg = Generator(load_config(config), templatedir)
    except yaml.YAMLError as exc:
        raise click.ClickException(format_yaml_error(config, exc))
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
    mg.update_gitignore(templatedir + "/.gitignire.jinja2", "../../.gitignore")

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
    help="""
              path to a YAML configuration.
              See examples folder for examples.
              This is optional, configuration can also be passed
              by command line, but an explicit config file is preferred.
              """,
)
@click.option("-c", "--clean/--no-clean", default=False)
@click.option("-T", "--templatedir", default=DEFAULT_TEMPLATE_DIR)
@click.option("-D", "--outdir", default=None)
@click.option("-d", "--dependencies", multiple=True)
@click.option("-t", "--title", type=str)
@click.option("-u", "--user", type=str)
@click.option(
    "-s",
    "--source",
    type=str,
    help="""
              path to existing source for ontology edit file. 
              Optional. If not passed, a stub ontology will be created.
              """,
)
@click.option("-v", "--verbose", count=True)
@click.option("-g", "--skipgit", default=False, is_flag=True)
@click.option("-n", "--gitname", default=None)
@click.option("-e", "--gitemail", default=None)
@click.option("-r", "--commit-artefacts", default=False, is_flag=True)
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
    """
    Seeds an ontology project
    """
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
    except yaml.YAMLError as exc:
        raise click.ClickException(format_yaml_error(config, exc))
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
        save_config(project, tgt_project_file)
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
        save_config(project, odk_config_file)
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


if __name__ == "__main__":
    main()
