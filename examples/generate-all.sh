#!/bin/bash

set -eu


## works both under bash and sh
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


"$SCRIPT_DIR"/key_ant_queen_lasius_wilson/generate.sh


## generate small images
#$SCRIPT_DIR/generate_small.sh
