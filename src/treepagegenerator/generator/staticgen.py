#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import logging

from typing import Any, Dict
import shutil

from treepagegenerator.utils import write_data
from treepagegenerator.generator.dataloader import DataLoader
from treepagegenerator.generator.utils import HTML_LICENSE
from treepagegenerator.data import DATA_DIR


SCRIPT_DIR = os.path.dirname(__file__)

_LOGGER = logging.getLogger(__name__)


def generate_pages(model_path, translation_path, _embed, _nophotos, output_path):
    gen = StaticGenerator()
    data_loader = DataLoader(model_path, translation_path)
    gen.generate(data_loader, output_path)


## ============================================


##
## Generating all possibilities is time consuming.
## For n categories there is following number of possibilities:
##    n1 * n2 * ... * nn
## where
##    n  is number categories
##    nx is number of values in category
##
class StaticGenerator:
    def __init__(self):  # noqa: F811
        self.total_count = 0
        self.page_counter = 0
        self.out_root_dir = None
        self.out_page_dir = None
        self.out_index_path = None

        self.label_back_to_main = "Main page"
        self.label_characteristic = "cecha"
        self.label_value = "wartość"

        self.data_loader: DataLoader = None

    def generate(self, data_loader: DataLoader, output_path):
        self.page_counter = 0

        self.out_root_dir = output_path
        os.makedirs(self.out_root_dir, exist_ok=True)

        self.data_loader = data_loader

        model = self.data_loader.model_data
        model_start = model.get("start")
        self.out_index_path = os.path.join(self.out_root_dir, "index.html")
        gen_index_page(self.out_index_path, model_start)

        css_styles_path = os.path.join(DATA_DIR, "styles.css")
        shutil.copy(css_styles_path, self.out_root_dir, follow_symlinks=True)

        self.out_page_dir = os.path.join(self.out_root_dir, "page")
        os.makedirs(self.out_page_dir, exist_ok=True)

        self.total_count = data_loader.get_total_count()
        self._generate_data()

    def _generate_data(self):
        model = self.data_loader.model_data
        model_data: Dict[str, Any] = model.get("data", {})

        ## prepare characteristic pages
        for item_id, desc_list in model_data.items():
            self._generate_page(item_id, desc_list)

    def _generate_page(self, item_id, desc_list):
        self.page_counter += 1
        page_path = os.path.join(self.out_page_dir, f"{item_id}.html")

        content = ""
        content += f""" \
<html>
{HTML_LICENSE}

<head>
<link rel="stylesheet" type="text/css" href="../styles.css">
</head>

<body>

"""

        prev_content = "<div> Back to: "
        link_list = [f"""<a href="{self.out_index_path}">{self.label_back_to_main}</a>"""]

        nav_dict = self.data_loader.nav_dict
        prev_items = nav_dict.prev_id_list(item_id)
        if prev_items:
            for prev in prev_items:
                item = f"""<a href="{prev}.html">{prev}</a>"""
                link_list.append(item)

        prev_content += " | ".join(link_list)
        prev_content += "</div>"
        content += prev_content

        page_content = self._generate_page_content(item_id, desc_list)
        content += page_content

        content += """
</body>
</html>
"""
        progress = self.page_counter / self.total_count * 100
        # progress = int(self.page_counter / self.total_count * 10000) / 100
        _LOGGER.debug("%f%% writing page: %s", progress, page_path)
        write_data(page_path, content)
        return page_path

    def _generate_page_content(self, item_id, desc_list):
        columns_num = len(desc_list)

        content = ""
        content += """<div>\n"""
        content += """<table>\n"""
        content += "<tr> " + "<th></th> " * columns_num + "</tr>\n" ""

        ## title row
        content += f"""<tr class="title_row"> <td colspan="{columns_num}">Characteristic {item_id}:</td> </tr>\n"""

        ## description row
        content += "<tr> "
        for val in desc_list:
            value = val.get("description")
            content += f"""<td>{value}</td> """
        content += "</tr>\n"

        ## "next" row
        content += """<tr class="navigation_row"> """
        for val in desc_list:
            next_id = val.get("next")
            if next_id:
                next_data = f"""<a href="{next_id}.html">{next_id}</a>"""
                content += f"""<td>{next_data}</td> """
            else:
                target = val.get("target")
                if target:
                    target_label = target[0]
                    target_link = target[1]
                    next_data = f"""<a href="{target_link}">{target_label}</a>"""
                    content += f"""<td>{next_data}</td> """
                else:
                    content += """<td>--- unknown ---</td> """
        content += "</tr>\n"

        ## potential species row
        potential_content = ""
        potential_content += f"""<tr class="title_row"> <td colspan="{columns_num}">Potential species:</td> </tr>\n"""
        potential_content += """<tr class="species_row"> """
        potential_species_dict = self.data_loader.potential_species
        found_potential = False
        for val in desc_list:
            next_species = []
            next_id = val.get("next")
            if next_id:
                next_species = potential_species_dict.get(next_id)
            # else:
            #     target = val.get("target")
            #     if target:
            #         next_species.append( target[0] )
            if next_species:
                found_potential = True
                next_species.sort()
                list_content = ["<ul>\n"]
                for item in next_species:
                    # item_low = prepare_filename(item)
                    # a_href = f"""<a href="{item_low}.html">{item}</a>"""
                    a_href = item
                    list_content.append(f"<li>{a_href}</li>\n")
                list_content.append("</ul>\n")
                list_str = "".join(list_content)
                potential_content += f"""<td>{list_str}</td> """
                continue

            potential_content += """<td></td> """
        potential_content += "</tr>\n"
        if found_potential:
            content += potential_content

        content += """</table>\n"""
        content += """</div>\n"""
        return content


def prepare_filename(name: str):
    name = name.lower()
    name = name.replace(" ", "_")
    return name


def gen_index_page(output_path, start_name):
    content = f""" \
<html>
<head>
<link rel="stylesheet" type="text/css" href="styles.css">
</head>
<body>
<div>
<a href="page/{start_name}.html">start</a>
</div>
</body>
</html>
"""
    write_data(output_path, content)
