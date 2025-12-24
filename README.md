Ontology Development Kit Core
=============================

This project provides the core functionality of the [Ontology
Development Kit](https://github.com/INCATools/ontology-development-kit)
as a standalone Python package (`odk-core`).

Namely, it provides:

* the `odk` script to seed and update a ODK-managed repository;
* the template files used to seed a ODK-managed repository.

Installation
------------
Unless they wish to use a “native ODK environment” (see below), most
users will not need to manually install this package. Instead, they will
use it through one of the [Docker
images](https://hub.docker.com/u/obolibrary) provided by the ODK project
– those images will include the `odk-core` package and its `odk` script.

The package _can_ definitely be used independently of the Docker images
though. For that, it can be installed as any other Python packages,
either from [PyPI](https://pypi.org/project/odk-core/):

```sh
$ python -m pip install odk-core
```

or from a release tarball
```sh
$ curl -L -O https://github.com/INCATools/odkcore/releases/download/odkcore-X.Y.Z/odk_core-X.Y.Z.tar.gz
$ tar xf odk_core-X.Y.Z.tar.gz
$ python -m pip install ./odk_core-X.Y.Z
```

Setting up a native ODK environment
-----------------------------------
Installing the `odk-core` package as shown above will automatically
install all the Python packages required to run the `odk` script (e.g.
to seed or update a ODK-managed repository).

In addition, installing the package with the `workflows` “extra” (as in
`pip install odk-core[workflows]` will also install all the Python
packages that are required by some of the standard ODK workflows as
implemented in the `src/ontology/Makefile` generated Makefile.

Non-Python tools need to be installed separately and made available in
the PATH. The various tools used by ODK workflows are:

* [GNU Make](https://www.gnu.org/software/make/) (always required – note
  that we do mean specifically **GNU** Make, other flavours of Make may
  not work),
* a [Java Runtime
  Environment](https://www.oracle.com/java/technologies/downloads/)
  (JRE; always required),
* [ROBOT](https://robot.obolibrary.org/) (always required),
* [Dicer-CLI](https://incenp.org/dvlpt/dicer/dicer-cli/index.html)
  (always required),
* [SSSOM-CLI](https://incenp.org/dvlpt/sssom-java/sssom-cli/index.html)
  (required for projects using SSSOM mappings),
* [DOSDP-Tools](https://github.com/INCATools/dosdp-tools) (required for
  projects using DOSDP patterns),
* [SQLite3](https://www.sqlite.org/),
  [Rdftab](https://github.com/ontodev/rdftab.rs), and
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

When using the ODK through one of the Docker images, all those
requirements are automatically met. When _not_ using the Docker images,
it is the user’s responsibility to ensure they are met, before ODK
workflows can be run. The `odk` script provides a command to help with
that:

```sh
$ odk install /path/to/my/env
```

That command will initialise the `/path/to/my/env` directory as a
“native ODK environment”, containing all the tools and ROBOT plugins
mentioned above (except GNU Make and the JRE, which are always expected
to be already available on the system).

To use the newly initialised environment, source the
`bin/activate-odk-environment.sh` script:

```sh
$ . /path/to/my/env/bin/activate-odk-environment.sh
```

The current shell is then ready to run ODK workflows.

Note that ODK native environments are only supported for the following
platforms:

* GNU/Linux x86_64,
* macOS x86_64,
* and macOS arm64.


Developing ODK-Core
-------------------
ODK-Core is managed with the [UV](https://docs.astral.sh/uv/) project
manager. Type checking is ensured through
[Mypy](https://www.mypy-lang.org/), and linting and formatting through
[Ruff](https://docs.astral.sh/ruff/).

Set up the development environment with:

```sh
$ uv sync --dev --extra workflows
```

from within the project’s checked out repository. The `--extra
workflows` is optional, but using it will make it easier to use the same
environment to also run (and therefore test) the ODK-generated
workflows.

To test seeding a ODK repository:

```sh
$ uv run odk seed -C config.yaml -g [other seeding options...]
```

Note the `-g` option, which instructs the seeding process not to try
building a first release in the newly seeded repository (trying to build
a release would likely fail, unless you happen to have the tools
mentioned in the previous section already available in your PATH).

The previous command assumed that you are in the directory where
ODK-Core was checked out. To run a `odk` command from anywhere else, use
UV’s `--project` option:

```sh
$ uv --project /path/to/odk-core run odk seed -C config.yaml -g [...]
```

I’d recommend setting up an alias like:

```sh
$ alias odk-dev="uv --project /path/to/odk-core run odk"
```

so that you can use `odk-dev` from anywhere, e.g. try seeding a
repository with:

```sh
$ odk-dev seed -g -C config.yaml [...]
```

To be able to test running a ODK workflow, instead of merely seeding a
ODK repository, first create a native ODK environment, then activate it:

```sh
$ odk-dev install /my/test/env
$ . /my/test/env/bin/activate-odk-environment.sh
```

It is then possible to seed a repository without skipping the building
of the initial release, and more generally to run any workflow within
the newly seeded repository:

```sh
$ odk-dev seed -C config.yaml [...]
$ cd target/<myont>/src/ontology
$ make clean refresh-imports
```

Copying
-------
The ODK Core is free software, published under the same 3-clause BSD
license as the original ODK. See the [LICENSE](LICENSE) file.
