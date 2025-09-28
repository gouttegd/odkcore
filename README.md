Ontology Development Kit Core
=============================

This is an _experimental_ project aiming at isolating the core features
of the [Ontology Development
Kit](https://github.com/INCATools/ontology-development-kit) (ODK) and
providing them as a single Python package, independently of the ODK
Docker images.

Rationale
---------
The “Ontology Development Kit” is currently three different things at
once:

* it is a set of executable workflows to manage the lifecycle of an
  ontology;
* it is a tool to create (“seed”, in ODK parlance) and update an
  ontology repository that would use said workflows;
* it is a toolbox of ontology engineering tools, provided as a Docker
  image.

This project posits that the first two things are in fact largely
independent of the third one, and makes the hypothesis that treating
them as such, and clearly separating them as two entities being
developed on their own, could overall facilitate the development of the
entire project.

Therefore, the aim of this “ODK Core” project is to provide the ODK’s
executable workflows and seeding/updating script, independently of the
ODK Docker image. Once it will have reached maturity (if it does!), the
idea is then that the ODK Core will become merely one of the tools
provided by the ODK Docker image.

A secondary goal is to make it possible to seed, update, and use a
ODK-managed repository _without_ using the Docker image at all.

Setting up a ODK environment
----------------------------
Installing the `odk-core` package (this project) with `pip` (or similar
tool) will automatically install all the Python packages required to run
the `odk` script itself (e.g. to seed or update a ODK project).

In addition, installing the package with the `workflows` “extra” (as in
`pip install odk-core[workflows]` will also install all the Python
packages that are required by some of the standard ODK workflows as
implemented in the `src/ontology/Makefile` generated Makefile.

Non-Python tools need to be installed separately and made available in
the PATH. The various tools used by ODK workflows are:

* [GNU Make](https://www.gnu.org/software/make/) (always required – note
  that we do mean specifically **GNU** Make, other flavours of Make may
  not work),
* [ROBOT](https://robot.obolibrary.org/) (always required),
* [Dicer-CLI](https://incenp.org/dvlpt/dicer/dicer-cli/index.html)
  (always required),
* [SSSOM-CLI](https://incenp.org/dvlpt/sssom-java/sssom-cli/index.html)
  (required for projects using SSSOM mappings),
* [DOSDP-Tools](https://github.com/INCATools/dosdp-tools) (required for
  projects using DOSDP patterns),
* [SQLite3](https://www.sqlite.org/) and
  [Relation-Graph](https://github.com/INCATools/relation-graph)
  (required for exporting release artefacts to [SemSQL
  format](https://incatools.github.io/semantic-sql/), if desired),
* and [GitHub’s command-line tool](https://cli.github.com/) (required
  to automatically push releases to GitHub, if desired).

Lastly, the environment must also provide some [ROBOT
plugins](https://robot.obolibrary.org/plugins). They must be made
available in a `$ODK_RESOURCES_DIR/robot/plugins` directory, where
`ODK_RESOURCES_DIR` is a variable exported into the environment. The
plugins used by ODK workflows are:

* the [ODK plugin](https://incatools.github.io/odk-robot-plugin/)
  (always required),
* and the [SSSOM
  plugin](https://incenp.org/dvlpt/sssom-java/sssom-robot/index.html)
  (required for projects using SSSOM mappings).

The easiest way (and, for now, the only really supported way) to get
such an environment is to use the [ODK Docker
image](https://github.com/INCATools/ontology-development-kit).


Developing ODK-Core
-------------------
ODK-Core is managed with the [UV](https://docs.astral.sh/uv/) project
manager. Type checking is ensured through
[Mypy](https://www.mypy-lang.org/), and linting and formatting through
[Ruff](https://docs.astral.sh/ruff/).

Set up the development environment with:

```sh
uv sync --dev --extra workflows
```

from within the project’s checked out repository. The `--extra
workflows` is optional, but using it will make it easier to use the same
environment to also run (and therefore test) the ODK-generated
workflows.

To test seeding a ODK repository:

```sh
uv run odk seed -C config.yaml -g [other seeding options...]
```

Note the `-g` option, which instructs the seeding process not to try
building a first release in the newly seeded repository (trying to build
a release would likely fail, unless you happen to have the tools
mentioned in the previous section already available in your PATH).

The previous command assumed that you are in the directory where
ODK-Core was checked out. To run a `odk` command from anywhere else, use
UV’s `--project` option:

```sh
uv --project /path/to/odk-core run odk seed -C config.yaml -g [...]
```

I’d recommend setting up an alias like:

```sh
alias odk-dev="uv --project /path/to/odk-core run odk"
```

so that you can use `odk-dev` from anywhere, e.g. try seeding a
repository with:

```sh
odk-dev seed -g -C config.yaml [...]
```


Copying
-------
The ODK Core is free software, published under the same 3-clause BSD
license as the original ODK. See the [LICENSE](LICENSE) file.
