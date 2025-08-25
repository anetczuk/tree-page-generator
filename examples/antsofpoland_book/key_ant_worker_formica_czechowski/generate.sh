#!/bin/bash

set -eu


## works both under bash and sh
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


echo "generating data"

MODEL_PATH="$SCRIPT_DIR/model.json"

"$SCRIPT_DIR"/../preparedata_antsofpoland.py --rawkey "${SCRIPT_DIR}"/raw_key.txt --outjson "${MODEL_PATH}"

# dot -Tpng "$SCRIPT_DIR/model_graph.dot" -o "$SCRIPT_DIR/model_graph.png"


echo "generating pages"

OUT_DIR="$SCRIPT_DIR/output"

rm -fr "$OUT_DIR"


SRC_DIR="${SCRIPT_DIR}/../../../src/"

cd "${SRC_DIR}"


CONFIG_PATH="$SCRIPT_DIR/config.json"


if [[ $* == *--info* ]]; then
    # print only info
    python3 -m treepagegenerator.main -la info \
                                      --data "$MODEL_PATH"
    exit 0
fi

set -x
python3 -m treepagegenerator.main -la generate \
                                  --config "$CONFIG_PATH" \
                                  --embedcss --embedimages --singlepagemode \
                                  --outdir "$OUT_DIR"
{ set +x; } 2> /dev/null

INDEX_PATH="${OUT_DIR}/index.html"

echo -e "\n\nchecking links"

result=$(checklink -r -q "${INDEX_PATH}" -X "http" 2> /dev/null || true)
if [[ "$result" != "" ]]; then
    echo "broken links found:"
    echo "$result"
    exit 1
fi
# else: # empty string - no errors
echo "no broken links found"


echo
echo "generated page: file://${INDEX_PATH}"


echo -e "\ngeneration completed"
