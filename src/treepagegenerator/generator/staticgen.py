#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import io
import logging

from typing import Any, Dict, List, Tuple, Set
import re
import shutil

from showgraph.graphviz import Graph, set_node_style

from treepagegenerator.utils import write_data
from treepagegenerator.generator.dataloader import DataLoader, copy_image
from treepagegenerator.generator.utils import HTML_LICENSE
from treepagegenerator.data import DATA_DIR


SCRIPT_DIR = os.path.dirname(__file__)

_LOGGER = logging.getLogger(__name__)


def generate_pages(config_path, translation_path, _nophotos, output_path):
    gen = StaticGenerator()
    data_loader = DataLoader(config_path, translation_path)
    gen.generate(data_loader, output_path)


## ============================================


##
## Generating all possibilities is time consuming.
##
class StaticGenerator:
    def __init__(self):  # noqa: F811
        self.total_count = 0
        self.page_counter = 0
        self.out_root_dir = None
        self.out_page_dir = None
        self.out_img_dir = None
        self.out_index_path = None

        self.label_back_to_main = "Main page"
        self.label_characteristic = "cecha"
        self.label_value = "wartość"

        self.data_loader: DataLoader = None

    def generate(self, data_loader: DataLoader, output_path):
        self.page_counter = 0

        self.out_root_dir = output_path
        os.makedirs(self.out_root_dir, exist_ok=True)

        self.out_img_dir = os.path.join(self.out_root_dir, "img")
        os.makedirs(self.out_img_dir, exist_ok=True)

        self.data_loader = data_loader

        model = self.data_loader.model_data
        model_data: Dict[str, Any] = model.get("data", {})

        self.total_count = data_loader.get_total_count()

        self._generate_index()

        ## prepare characteristic pages
        for item_id, desc_list in model_data.items():
            self._generate_page(item_id, desc_list)

        ## prepare species pages
        all_species = self.data_loader.get_all_leafs()
        for item in all_species:
            self._generate_species_subpage(item)

        ## prepare species page
        self._generate_species_page()

        ## prepare dictionary page
        self._generate_defs_page()

    def _generate_index(self):
        model = self.data_loader.model_data
        model_start = model.get("start")
        self.out_index_path = os.path.join(self.out_root_dir, "index.html")

        page_title = self.data_loader.get_model_title()
        model_desc = self.data_loader.get_model_description()

        content = f"""\
<html>
{HTML_LICENSE}

<head>
    <title>{page_title}</title>
    <link rel="stylesheet" type="text/css" href="styles.css">
</head>

<body>
<div class="main_section title">
{page_title}
</div>
<div class="main_section description">
{model_desc}
</div>

<div class="main_section">
<a href="page/{model_start}.html">Start</a>
</div>

<div class="main_section">
<a href="species.html">Species</a>
</div>

<div class="main_section">
<a href="dictionary.html">Dictionary</a>
</div>

</body>

</html>
"""
        write_data(self.out_index_path, content)

        css_styles_path = os.path.join(DATA_DIR, "styles.css")
        shutil.copy(css_styles_path, self.out_root_dir, follow_symlinks=True)

        self.out_page_dir = os.path.join(self.out_root_dir, "page")
        os.makedirs(self.out_page_dir, exist_ok=True)

    def _generate_page(self, item_id, desc_list):
        self.page_counter += 1
        page_path = os.path.join(self.out_page_dir, f"{item_id}.html")

        page_title = self.data_loader.get_model_title()

        content = ""
        content += f"""\
<html>
{HTML_LICENSE}

<head>
    <title>{page_title} - characteristics</title>
    <link rel="stylesheet" type="text/css" href="../styles.css">
</head>

<body>

"""

        main_page_rel_path = os.path.relpath(self.out_index_path, self.out_page_dir)
        prev_content = "<div> Back to: "
        link_list = [f"""<a href="{main_page_rel_path}">{self.label_back_to_main}</a>"""]

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

        data_graph = generate_graph(self.data_loader, item_id)
        svg_content = get_graph_svg(data_graph)

        ## remove defined 'width' and 'height' - attributes corrupts image placement
        svg_content = re.sub(r'<svg\s+width="\d+\S+"\s+height="\d+\S+"', "<svg", svg_content)

        content += f"""
<div class="graph_content">
    {svg_content}
</div>
"""

        content += """<div>\n"""
        content += """<table>\n"""
        content += "<tr> " + "<th></th> " * columns_num + "</tr>\n" ""

        ## title row
        content += f"""<tr class="title_row"> <td colspan="{columns_num}">Characteristic {item_id}:</td> </tr>\n"""

        ## description row
        char_keywords = set()
        content += "<tr>"
        for val in desc_list:
            value = val.get("description")
            desc, desc_keys = self._prepare_description(value)
            char_keywords.update(desc_keys)
            content += f"""\n   <td>{desc}</td>"""
        content += "</tr>\n"

        ## "next" row
        content += """<tr class="navigation_row"> """
        for val in desc_list:
            next_id = val.get("next")
            if next_id:
                next_data = f"""<a href="{next_id}.html" class="next_char">next: {next_id}</a>"""
                content += f"""<td>{next_data}</td> """
            else:
                target = val.get("target")
                if target:
                    target_label = target[0]
                    item_low = prepare_filename(target_label)
                    next_data = f"""<a href="{item_low}.html" class="next_char">{target_label}</a>"""
                    content += f"""<td>{next_data}</td> """
                else:
                    content += """<td>--- unknown ---</td> """
        content += "</tr>\n"

        ## potential species row
        potential_content = self._prepare_potential_species(desc_list)
        if potential_content:
            content += potential_content

        content += """</table>\n"""
        content += """</div>\n"""

        ## keywords row
        if char_keywords:
            keywords_list = list(char_keywords)
            keywords_list.sort()

            content += """<div>\n"""
            content += self._prepare_defs_table(keywords_list, self.out_page_dir)
            content += """</div>\n"""

        return content

    def get_def_photo_path(self, source_def_path):
        base_path = get_path_components(source_def_path, 2)  ## filename with dir name
        base_path = prepare_filename(base_path)
        dest_img_path = os.path.join(self.out_img_dir, base_path)
        return dest_img_path

    def _prepare_potential_species(self, desc_list):
        columns_num = len(desc_list)

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
                    item_low = prepare_filename(item)
                    a_href = f"""<a href="{item_low}.html">{item}</a>"""
                    list_content.append(f"<li>{a_href}</li>\n")
                list_content.append("</ul>\n")
                list_str = "".join(list_content)
                potential_content += f"""<td>{list_str}</td> """
                continue

            ## no species found
            potential_content += """<td></td> """
        potential_content += "</tr>\n"

        if found_potential:
            return potential_content
        return None

    def _prepare_description(self, description) -> Tuple[str, List[str]]:
        description_defs_list = self.data_loader.get_all_defs()
        description_defs_list = sorted(description_defs_list, key=lambda x: (-len(x), x))
        ret_descr = description
        ret_keywords = []

        desc_low = description.lower()
        places = find_all_defs(desc_low, description_defs_list)
        places = sorted(places, key=lambda x: (x[0], -len(x[1])))
        places.reverse()
        for palce_item in places:
            pos = palce_item[0]
            def_item = palce_item[1]
            def_len = len(def_item)
            end_pos = pos + def_len
            ## add suffix to def
            ret_descr = ret_descr[:end_pos] + "</a>" + ret_descr[end_pos:]
            ## add prefix to def
            ret_descr = ret_descr[:pos] + f"""<a href="#{def_item}" class="def_item">""" + ret_descr[pos:]
            ret_keywords.append(def_item)

        return ret_descr, ret_keywords

    def _generate_species_page(self):
        page_path = os.path.join(self.out_root_dir, "species.html")

        page_title = self.data_loader.get_model_title()

        content = ""
        content += f"""\
<html>
{HTML_LICENSE}

<head>
    <title>{page_title} - species</title>
    <link rel="stylesheet" type="text/css" href="styles.css">
</head>

<body>

"""

        ## generate content
        main_page_rel_path = os.path.relpath(self.out_index_path, self.out_root_dir)
        prev_content = "<div> Back to: "
        prev_content += f"""<a href="{main_page_rel_path}">{self.label_back_to_main}</a>"""
        prev_content += "</div>"
        content += prev_content

        content += "</br>"

        content += "<div>List of species included in the key:</div>"

        species_set = set()
        potential_species_dict = self.data_loader.potential_species
        for char_species_list in potential_species_dict.values():
            species_set.update(char_species_list)
        species_list = list(species_set)
        species_list.sort()

        list_content = ["<ul>\n"]
        for species in species_list:
            item_low = prepare_filename(species)
            a_href = f"""<a href="page/{item_low}.html">{species}</a>"""
            list_content.append(f"<li>{a_href}</li>\n")
        list_content.append("</ul>\n")
        list_str = "".join(list_content)
        content += list_str

        content += """
</body>
</html>
"""
        write_data(page_path, content)
        return page_path

    def _generate_species_subpage(self, species_id):
        species_id_low = prepare_filename(species_id)
        page_path = os.path.join(self.out_page_dir, f"{species_id_low}.html")

        prev_list = self.data_loader.nav_dict.prev_items_list(species_id)
        last_item = prev_list[-1]
        species_target = self.data_loader.get_target(*last_item)
        species_name = species_target[0]

        page_title = self.data_loader.get_model_title()

        content = ""
        content += f"""\
<html>
{HTML_LICENSE}

<head>
    <title>{page_title} - {species_name}</title>
    <link rel="stylesheet" type="text/css" href="../styles.css">
</head>

<body>

"""

        ## generate content
        main_page_rel_path = os.path.relpath(self.out_index_path, self.out_page_dir)
        prev_content = "<div> Back to: "
        prev_content += f"""<a href="{main_page_rel_path}">{self.label_back_to_main}</a>"""
        prev_content += "</div>"
        content += prev_content

        data_graph = generate_graph(self.data_loader, species_id)
        svg_content = get_graph_svg(data_graph)
        content += f"""
<div class="graph_content">
    {svg_content}
</div>
"""

        content += "</br>"

        content += f"""<div><b>{species_name}</b>:</div>"""
        info_url = species_target[1]
        if info_url:
            content += f"""<div>Info: <a href="{info_url}">{info_url}</a></div>"""

        model = self.data_loader.model_data
        model_data: Dict[str, Any] = model.get("data", {})

        ## characteristics list
        char_keywords = set()
        content += "<ul>\n"
        for prev_item in prev_list:
            prev_id = prev_item[0]
            prev_data = model_data[prev_id]
            prev_desc_index = prev_item[1]
            prev_desc_item = prev_data[prev_desc_index]
            prev_desc = prev_desc_item.get("description")
            desc, desc_keys = self._prepare_description(prev_desc)
            char_keywords.update(desc_keys)
            char_link = f"""<a href="{prev_id}.html">{prev_id}</a>"""
            content += f"""<li>{char_link}: {desc}</li>\n"""
        content += "</ul>\n"

        ## keywords row
        if char_keywords:
            keywords_list = list(char_keywords)
            keywords_list.sort()

            content += """<div>\n"""
            content += self._prepare_defs_table(keywords_list, self.out_page_dir)
            content += """</div>\n"""

        content += """
</body>
</html>
"""
        write_data(page_path, content)
        return page_path

    def _generate_defs_page(self):
        page_path = os.path.join(self.out_root_dir, "dictionary.html")

        page_title = self.data_loader.get_model_title()

        content = ""
        content += f"""\
<html>
{HTML_LICENSE}

<head>
    <title>{page_title} - dictionary</title>
    <link rel="stylesheet" type="text/css" href="styles.css">
</head>

<body>

"""

        ## generate content
        main_page_rel_path = os.path.relpath(self.out_index_path, self.out_root_dir)
        prev_content = "<div> Back to: "
        prev_content += f"""<a href="{main_page_rel_path}">{self.label_back_to_main}</a>"""
        prev_content += "</div>"
        content += prev_content

        content += "</br>"

        content += "<div>Explanation of some definitions used in the characteristics.</div>"

        defs_dict = self.data_loader.get_defs_dict()
        keywords_list = list(defs_dict.keys())
        keywords_list.sort()

        for keyword in keywords_list:
            keyword_data_list = defs_dict[keyword]
            for keyword_item in keyword_data_list:
                photo_path = keyword_item.get("image")
                if not photo_path:
                    continue
                dest_img_path = self.get_def_photo_path(photo_path)
                copy_image(photo_path, dest_img_path, resize=False)

        keywords_content = self._prepare_defs_table(keywords_list, self.out_root_dir)
        if keywords_content:
            content += """<div>\n"""
            content += keywords_content
            content += """</div>\n"""

        content += """
</body>
</html>
"""
        write_data(page_path, content)
        return page_path

    def _prepare_defs_table(self, keywords_list, page_dir):
        if not keywords_list:
            return None

        defs_dict = self.data_loader.get_defs_dict()
        keywords_content = ""
        keywords_content += """<table>\n"""
        keywords_content += """<tr class="title_row"> <td colspan="2">Keywords:</td> </tr>\n"""
        for keyword in keywords_list:
            keywords_content += f"""<tr class="def_row"> <td class="def_item"><a name="{keyword}"></a>{keyword}</td> """
            keyword_data_list = defs_dict[keyword]
            keywords_content += """<td> """
            for keyword_item in keyword_data_list:
                def_text = keyword_item.get("text")
                img_rel_path = None
                photo_path = keyword_item.get("image")
                if photo_path:
                    dest_img_path = self.get_def_photo_path(photo_path)
                    img_rel_path = os.path.relpath(dest_img_path, page_dir)
                description_content = keyword_item.get("description")
                keywords_content += """<div class="imgtile">\n"""
                if def_text:
                    keywords_content += f"""    <div>{def_text}</div>\n"""
                if img_rel_path:
                    keywords_content += f"""    <a href="{img_rel_path}"><img src="{img_rel_path}"></a>\n"""
                if description_content:
                    keywords_content += f"""    <div>{description_content}</div>\n"""
                keywords_content += """</div>\n"""

            keywords_content += """ </td> """
            keywords_content += """</tr>\n"""
        keywords_content += """</table>\n"""
        return keywords_content


## ===========================================================================================


def get_path_components(path, level):
    remaining = path
    ret = None
    for _i in range(0, level):
        parts = os.path.split(remaining)
        head = parts[0]
        tail = parts[1]
        if not ret:
            ret = tail
        else:
            ret = os.path.join(tail, ret)
        remaining = head
    return ret


def find_all_defs(content, def_list: List[str]) -> List[Tuple[int, str]]:
    palces_list = []
    for def_item in def_list:
        desc_low = content.lower()
        places = find_all(desc_low, def_item)
        if not places:
            continue
        for pos in places:
            palces_list.append((pos, def_item))

    ret_list = []
    recent_end = -1
    palces_list = sorted(palces_list, key=lambda x: (x[0], -len(x[1])))
    for pos_item in palces_list:
        pos = pos_item[0]
        if pos <= recent_end:
            continue
        ret_list.append(pos_item)
        pos_end = pos + len(pos_item[1])
        recent_end = pos_end

    return ret_list


def find_all(content, substring) -> List[int]:
    ret_list = []
    pos = 0
    while True:
        new_pos = content.find(substring, pos)
        if new_pos < 0:
            break
        ret_list.append(new_pos)
        pos = new_pos + 1
    return ret_list


def prepare_filename(name: str):
    name = name.lower()
    name = re.sub(r"\s+", "_", name)
    return name


## ================================================================


def generate_graph(data_loader: DataLoader, active_item: str) -> Graph:
    graph: Graph = Graph()
    base_graph = graph.base_graph
    base_graph.set_name("model_graph")
    base_graph.set_type("digraph")
    # base_graph.set_rankdir("LR")

    model_data = data_loader.model_data["data"]

    added_nodes: Set[str] = set()

    ## add edges
    for key, val_list in model_data.items():
        for val in val_list:
            edges = []
            next_id = val["next"]
            if next_id is not None:
                edges.append((key, next_id))
            target = val["target"]
            if target is not None:
                edges.append((key, target[0]))

            for new_edge in edges:
                for node in new_edge:
                    if node in added_nodes:
                        continue
                    if node == active_item:
                        graph.addNode(node, shape="ellipse")
                        active_node = graph.getNode(node)
                        style = {"style": "filled", "fillcolor": "yellow"}
                        set_node_style(active_node, style)
                    else:
                        graph.addNode(node, shape="ellipse")
                        active_node = graph.getNode(node)
                        style = {"style": "filled", "fillcolor": "white"}
                        set_node_style(active_node, style)
                    created_node = graph.getNode(node)
                    node_filename = prepare_filename(node)
                    created_node.set("href", f"{node_filename}.html")

                new_edge = graph.addEdge(*new_edge)
                new_edge.set("color", "black")  # type: ignore
    return graph


def get_graph_svg(graph: Graph):
    with io.BytesIO() as buffer:
        graph.write(buffer, file_format="svg")
        contents = buffer.getvalue()
        contents_str = contents.decode("utf-8")
        return contents_str
