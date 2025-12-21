#!/bin/sh

# This script is expected to be run from within the tests/ directory.

set -e
rm -rf testenv status.txt

GITNAME=$(git config --get user.name)
GITEMAIL=$(git config --get user.email)

# Create native ODK environment for testing
mkdir testenv
uv --project .. run odk install testenv
. testenv/bin/activate-odk-environment.sh

# Seed and build all the test configurations
for t in configs/*.yaml ; do
    echo -n "$t... " >> status.txt
    uv --project .. run odk seed --gitname "$GITNAME" --gitemail "$GITEMAIL" -c -C $t
    echo DONE >> status.txt
done

rm -rf target testenv status.txt
