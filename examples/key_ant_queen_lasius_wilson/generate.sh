#!/bin/bash

set -eu


## works both under bash and sh
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")


echo "generating data"

"$SCRIPT_DIR"/preparedata_wilson.py

# dot -Tpng "$SCRIPT_DIR/model_graph.dot" -o "$SCRIPT_DIR/model_graph.png"


echo "generating pages"

OUT_DIR="$SCRIPT_DIR/output"
SCREENS_OUT_DIR="$SCRIPT_DIR/screens"

rm -fr "$OUT_DIR"
rm -fr "$SCREENS_OUT_DIR"


cd "$SCRIPT_DIR/../../src/"


CONFIG_PATH="$SCRIPT_DIR/config.json"
MODEL_PATH="$SCRIPT_DIR/model.json"


if [[ $* == *--info* ]]; then
    # print only info
    python3 -m treepagegenerator.main -la info \
                                      --data "$MODEL_PATH"
    exit 0
fi

set -x
python3 -m treepagegenerator.main -la generate \
                                  --config "$CONFIG_PATH" \
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


## generate image from html
echo -e "\ntaking screenshots"

mkdir -p "${SCREENS_OUT_DIR}"

PAGE_PATH="$OUT_DIR/page/3.html"
if [ -f "$PAGE_PATH" ]; then
    OUT_IMG_PATH="$SCREENS_OUT_DIR/3-page.png"
    cutycapt --url="file://${PAGE_PATH}" --out="${OUT_IMG_PATH}"
fi

cd "$SCREENS_OUT_DIR"
# shellcheck disable=SC1090,SC1091
source "$SCRIPT_DIR/../../doc/generate_small.sh"


echo -e "\ngeneration completed"
