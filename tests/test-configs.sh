#!/bin/sh

# This script is expected to be run from within the tests/ directory.

set -e
rm -rf testenv status.txt

GITNAME=$(git config --get user.name)
GITEMAIL=$(git config --get user.email)

run_odk_seed() {
    uv --project .. run odk seed --gitname "$GITNAME" --gitemail "$GITEMAIL" "$@"
}

# Create native ODK environment for testing
mkdir testenv
uv --project .. run odk install testenv
. testenv/bin/activate-odk-environment.sh

# Seed and build all the test configurations
for t in configs/*.yaml ; do
    echo -n "$t... " >> status.txt
    run_odk_seed -c -C $t
    echo DONE >> status.txt
done

# Additional tests without an explicit config file
run_odk_seed -c -t my-ontology1 my-ont
run_odk_seed -c -d pato -d ro -t my-ontology2 my-ont
run_odk_seed -c -d pato -d cl -d ro -t my-ontology3 my-ont

# Additional "GO mini" test
run_odk_seed -c -D target/go-mini \
             -C ../examples/go-mini/project.yaml \
             -s ../examples/go-mini/go-edit.obo

rm -rf target testenv status.txt
