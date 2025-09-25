# odkcore - Ontology Development Kit Core
# Copyright © 2025 ODK Developers
#
# This file is part of the ODK Core project and distributed under the
# terms of a 3-clause BSD license. See the LICENSE file in that project
# for the detailed conditions.

import logging
import subprocess

from yaml import YAMLError


def format_yaml_error(file: str, exc: YAMLError) -> str:
    """Turns a YAML parser error into a human-readable error message.

    :param file: The file that triggered the parsing error.
    :param exc: The YAML parsing error.

    :returns: The formatted error message.
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
        msg += ": unknown YAML error"
    return msg


def runcmd(cmd: str) -> None:
    """Runs a command in a new process.

    An exception will be thrown if the command fails for any reason.

    :param cmd: The command to run.
    """
    logging.info("RUNNING: {}".format(cmd))
    p = subprocess.Popen(
        [cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        universal_newlines=True,
    )
    (out, err) = p.communicate()
    logging.info("OUT: {}".format(out))
    if err:
        logging.error(err)
    if p.returncode != 0:
        raise Exception("Failed: {}".format(cmd))
