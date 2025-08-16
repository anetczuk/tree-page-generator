#!/usr/bin/env python3
#
# Copyright (c) 2025, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
from typing import Dict, Any, List
import argparse

import json
import re


SCRIPT_DIR = os.path.dirname(__file__)


def generate_dot(model_dict):
    model_start = model_dict["start"]
    model_data = model_dict["data"]

    content = ""
    content += """\
digraph data_graph {
"""

    content += f"""    "start" -> "{model_start}" \n"""

    for key, val_list in model_data.items():
        for val in val_list:
            next_id = val["next"]
            if next_id is not None:
                content += f"""    "{key}" -> "{next_id}" \n"""
                continue
            target = val["target"]
            if target is not None:
                content += f"""    "{key}" -> "{target[0]}" \n"""
                continue

    content += """\
}
"""

    with open(f"{SCRIPT_DIR}/model_graph.dot", "w", encoding="utf-8") as f:
        f.write(content)


def find_nth(haystack: str, needle: str, n: int, start: int = 0) -> int:
    start = haystack.find(needle, start)
    while start >= 0 and n > 1:
        start = haystack.find(needle, start + len(needle))
        n -= 1
    return start


def convert_key(raw_key_content):
    first_key = None
    characteristic_list: Dict[str, Any] = {}
    curr_key = None
    choices_list: List[Any] = []  ## choices for single characteristic
    choice_lines: List[str] = []  ## text lines for single choice
    for line in raw_key_content:
        line = line.strip()
        if not line:
            ## empty line
            continue

        if not choice_lines:
            found_nums = re.findall(r"^(\d+)\. ", line)
            if found_nums:
                ## new characteristic
                if choices_list:
                    characteristic_list[curr_key] = choices_list
                choices_list = []
                curr_key = found_nums[0]
                line = line[len(curr_key) + 2 :]
                if first_key is None:
                    first_key = curr_key
            if choices_list:
                found_prefixes = re.findall(r"^-\s+", line)
                if found_prefixes:
                    prefix_str = found_prefixes[0]
                    line = line[len(prefix_str) :]

        found_postfix = re.findall(r"\s+\.[\.]+$", line)
        if found_postfix:
            postfix = found_postfix[0]
            end_pos = len(line) - len(postfix)
            line = line[:end_pos]

        choice_lines.append(line)

        if "... " in line:
            ## end of choice
            curr_choice = " ".join(choice_lines)
            curr_choice = curr_choice.strip()

            next_item = None
            target = None
            found_next = re.findall(r"(\s+\.[\.]+\s+(\d+))$", curr_choice)
            if found_next:
                ## next step
                item = found_next[0]
                postfix = item[0]
                end_pos = len(curr_choice) - len(postfix)
                curr_choice = curr_choice[:end_pos]
                next_item = item[1]
            else:
                found_target = re.findall(r"(\s+\.[\.]+\s+(.+))$", curr_choice)
                if found_target:
                    ## species
                    item = found_target[0]
                    postfix = item[0]
                    end_pos = len(curr_choice) - len(postfix)
                    curr_choice = curr_choice[:end_pos]
                    species_name = item[1]
                    species_name = species_name.replace("M.", "Myrmica")
                    species_name = species_name.replace("F.", "Formica")

                    ## remove subname (discoverer)
                    second_pos = find_nth(species_name, " ", 2)
                    third_pos = species_name.find("(", second_pos)
                    if third_pos >= 0:
                        species_name = species_name[: second_pos + 1] + species_name[third_pos:]
                    subsp_pos = species_name.find("subsp.")
                    if subsp_pos >= 0:
                        subsp_space_pos = find_nth(species_name, " ", 2, subsp_pos)
                        subsp_end_pos = species_name.find(")", subsp_space_pos)
                        species_name = species_name[:subsp_space_pos] + species_name[subsp_end_pos:]

                    ## remove page information
                    page_pos = species_name.find("(p.")
                    if page_pos > 0:
                        page_pos -= 1
                        species_name = species_name[:page_pos]

                    target = (species_name, None)

            choice_dict = {"description": curr_choice, "next": next_item, "target": target}
            choices_list.append(choice_dict)
            choice_lines = []
    characteristic_list[curr_key] = choices_list

    model_dict = {"start": first_key, "data": characteristic_list}
    return model_dict


def main():
    parser = argparse.ArgumentParser(
        description="parse raw key",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-la", "--logall", action="store_true", help="Log all messages")
    # have to be implemented as parameter instead of command (because access to 'subparsers' object)
    parser.add_argument("--rawkey", action="store", required=True, help="Path to raw key to parse")
    parser.add_argument("--outjson", action="store", required=True, help="Path to output model")

    args = parser.parse_args()

    data_path = args.rawkey
    with open(data_path, "r", encoding="utf-8") as file:
        txt_content = file.readlines()

    model_dict = convert_key(txt_content)

    json_str = json.dumps(model_dict, indent=4)
    model_output_path = args.outjson
    with open(model_output_path, "w", encoding="utf-8") as f:
        f.write(json_str)

    # generate_dot(model_dict)


if __name__ == "__main__":
    main()
