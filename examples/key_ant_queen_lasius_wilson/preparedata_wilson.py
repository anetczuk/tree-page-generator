#!/usr/bin/env python3
#
# Copyright (c) 2025, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import json
import os
from typing import Any

from bs4 import BeautifulSoup


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


def main():
    # url = "https://antwiki.org/wiki/Key_to_Lasius_queens"
    # # Fetch the page content
    # response = requests.get(url)
    # response.raise_for_status()  # Raise error for bad status
    # html_content = response.content

    root_url = "https://antwiki.org"
    url = f"{SCRIPT_DIR}/antwiki_lasius_key.html"
    with open(url, encoding="utf-8") as file:
        html_content = file.read()

    # Parse the page
    soup = BeautifulSoup(html_content, "html.parser")

    # Main content div
    content_div = soup.find("div", {"id": "mw-content-text"})
    div_child_list = content_div.findChildren("div", recursive=False)  # type: ignore[union-attr]
    child_div = div_child_list[0]

    dict_data = {}
    first_id = None
    recent_id = None
    recent_item = []

    for tag in child_div.find_all(["h2", "h3", "p", "ul", "ol"], recursive=False):
        if tag.name in ("h2", "h3"):
            if recent_id is not None:
                dict_data[recent_id] = recent_item
                recent_id = None
                recent_item = []
            recent_id = tag.get_text(strip=True)
            if first_id is None:
                first_id = recent_id

        elif tag.name in ("ul", "ol"):
            for li in tag.find_all("li"):
                item_data: dict[str, Any] = {"description": None, "next": None, "target": None}
                item_text = li.get_text(strip=True)
                pos = item_text.find(". .")
                item_text = item_text[:pos]
                item_text = item_text.strip()
                item_data["description"] = item_text

                for href in li.find_all("a"):
                    next_url = href["href"]
                    if next_url.startswith("#"):
                        next_id = next_url[1:]
                        item_data["next"] = next_id
                    else:
                        next_label = href.get_text(strip=True)
                        next_label = next_label.replace(".", " ")
                        next_label = next_label.strip()
                        target_url = f"{root_url}{next_url}"
                        item_data["target"] = (next_label, target_url)

                recent_item.append(item_data)

    if recent_id is not None:
        dict_data[recent_id] = recent_item
        recent_id = None
        recent_item = []

    model_dict = {"start": first_id, "data": dict_data}

    json_str = json.dumps(model_dict, indent=4)
    with open(f"{SCRIPT_DIR}/model.json", "w", encoding="utf-8") as f:
        f.write(json_str)

    # generate_dot(model_dict)


if __name__ == "__main__":
    main()
