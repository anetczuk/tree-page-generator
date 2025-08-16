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

    # check_defs_repetitions(data_loader)


def check_defs_repetitions(data_loader: DataLoader):
    defs_list = data_loader.defs_list
    for def_dict in defs_list:
        defs_list = def_dict.get("defs", [])
        repeated_def = True
        for def_name in defs_list:
            found_defs = data_loader.get_defs(def_name)
            if len(found_defs) < 2:
                repeated_def = False
                break
        if repeated_def:
            _LOGGER.info("found repeated def: %s", defs_list)


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
            self._generate_subpage(item_id, desc_list)

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

        ## main/index page
        content = ""
        content += f"""\
<!DOCTYPE html>
<html>
{HTML_LICENSE}

<head>
    <title>{page_title}</title>
    <link rel="stylesheet" type="text/css" href="styles.css">
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
</head>

<body>

<div class="main_section title">{page_title}</div>

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

    def _generate_subpage(self, item_id, desc_list):
        self.page_counter += 1
        page_path = os.path.join(self.out_page_dir, f"{item_id}.html")

        page_title = self.data_loader.get_model_title()

        ## characteristic page
        content = ""
        content += f"""\
<!DOCTYPE html>
<html>
{HTML_LICENSE}

<head>
    <title>{page_title} - characteristics</title>
    <link rel="stylesheet" type="text/css" href="../styles.css">
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
</head>

<body>

<div class="main_section title">{page_title}</div>

"""

        ## generate content
        prev_content = self._prepare_back_to(self.out_page_dir, item_id)
        content += prev_content + "\n"

        page_content = self._generate_subpage_content(item_id, desc_list)
        content += page_content

        content += """
</body>
</html>
"""
        progress = self.page_counter / self.total_count * 100
        # progress = int(self.page_counter / self.total_count * 10000) / 100
        _LOGGER.debug("%.2f%% writing page: %s", progress, page_path)
        write_data(page_path, content)
        return page_path

    def _generate_subpage_content(self, item_id, desc_list):
        columns_num = len(desc_list)

        content = ""

        graph_content = self._prepare_tree_graph(item_id)
        content += graph_content

        content += """\n<div class="characteristic_section">\n"""
        table_content = """<table>\n"""

        ## title row
        table_content += (
            f"""<tr class="title_row"> <th colspan="{columns_num}">Characteristic {item_id}:</th> </tr>\n"""
        )

        ## description row
        char_keywords = set()
        table_content += "<tr>"
        for val in desc_list:
            value = val.get("description")
            desc, desc_keys = self._prepare_description(value)
            char_keywords.update(desc_keys)
            table_content += f"""\n   <td>{desc}</td>"""
        table_content += "\n</tr>\n"

        ## "next" row
        table_content += """<tr class="navigation_row"> """
        for val in desc_list:
            next_id = val.get("next")
            if next_id:
                next_data = f"""<a href="{next_id}.html" class="next_char">next: {next_id}</a>"""
                table_content += f"""<td>{next_data}</td> """
            else:
                target = val.get("target")
                if target:
                    target_label = target[0]
                    item_low = prepare_filename(target_label)
                    next_data = f"""<a href="{item_low}.html" class="next_char">{target_label}</a>"""
                    table_content += f"""<td>{next_data}</td> """
                else:
                    table_content += """<td>--- unknown ---</td> """
        table_content += "</tr>\n"

        ## potential species row
        potential_content = self._prepare_potential_species(desc_list)
        if potential_content:
            table_content += potential_content

        table_content += """</table>\n"""
        table_content = table_content.replace("\n", "\n    ")
        table_content = table_content.strip()
        table_content = "    " + table_content
        content += table_content
        content += """\n</div>\n"""

        ## keywords row
        if char_keywords:
            keywords_list = list(char_keywords)
            keywords_list.sort()

            content += """\n<div class="keywords_section">\n"""
            content += self._prepare_defs_table(keywords_list, self.out_page_dir)
            content += """\n</div>\n"""

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
        potential_content += """<tr class="species_row">"""
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
                    list_content.append(f"        <li>{a_href}</li>\n")
                list_content.append("        </ul>")
                list_str = "".join(list_content)
                potential_content += f"""\n    <td>{list_str}\n    </td>"""
                continue

            ## no species found
            potential_content += """<td></td> """
        potential_content += "\n</tr>\n"

        if found_potential:
            return potential_content
        return None

    def _prepare_description(self, description) -> Tuple[str, List[str]]:
        description_defs_list = self.data_loader.get_all_defs()
        ret_descr = description
        ret_keywords = []

        places = find_all_defs(description, description_defs_list)
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

        ## species list page
        content = ""
        content += f"""\
<!DOCTYPE html>
<html>
{HTML_LICENSE}

<head>
    <title>{page_title} - species</title>
    <link rel="stylesheet" type="text/css" href="styles.css">
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
</head>

<body>

<div class="main_section title">{page_title}</div>

"""

        ## generate content
        prev_content = self._prepare_back_to(self.out_root_dir)
        content += prev_content + "\n"

        content += """\n<div class="main_section">List of species included in the key:</div>\n"""

        species_set = set()
        potential_species_dict = self.data_loader.potential_species
        for char_species_list in potential_species_dict.values():
            species_set.update(char_species_list)
        species_list = list(species_set)
        species_list.sort()

        list_content = ["""\n<ul class="species_list">\n"""]
        for species in species_list:
            item_low = prepare_filename(species)
            a_href = f"""<a href="page/{item_low}.html">{species}</a>"""
            list_content.append(f"    <li>{a_href}</li>\n")
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

        ## species page
        content = ""
        content += f"""\
<!DOCTYPE html>
<html>
{HTML_LICENSE}

<head>
    <title>{page_title} - {species_name}</title>
    <link rel="stylesheet" type="text/css" href="../styles.css">
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
</head>

<body>

<div class="main_section title">{page_title}</div>

"""

        ## generate content
        prev_content = self._prepare_back_to(self.out_page_dir, species_id)
        content += prev_content + "\n"

        graph_content = self._prepare_tree_graph(species_id)
        content += graph_content

        content += f"""\n<div class="title_row main_section">{species_name}</div>\n"""
        info_url = species_target[1]
        if info_url:
            content += f"""<div>Info: <a href="{info_url}">{info_url}</a></div>\n"""

        model = self.data_loader.model_data
        model_data: Dict[str, Any] = model.get("data", {})

        ## characteristics list
        char_keywords = set()
        content += """<ul class="characteristic_list">\n"""
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

            content += """\n<div class="keywords_section">\n"""
            content += self._prepare_defs_table(keywords_list, self.out_page_dir)
            content += """\n</div>\n"""

        content += """
</body>
</html>
"""
        write_data(page_path, content)
        return page_path

    def _prepare_tree_graph(self, active_item_id):
        data_graph = generate_graph(self.data_loader, active_item_id)
        svg_content = get_graph_svg(data_graph)

        ## remove defined 'width' and 'height' - attributes corrupts image placement
        svg_content = re.sub(r'<svg\s+width="\d+\S+"\s+height="\d+\S+"', "<svg", svg_content)
        svg_content = svg_content.replace("\n", "\n    ")
        svg_content = svg_content.strip()
        svg_content = "    " + svg_content

        return f"""
<div class="graph_section">
{svg_content}
</div>
"""

    def _generate_defs_page(self):
        page_path = os.path.join(self.out_root_dir, "dictionary.html")

        page_title = self.data_loader.get_model_title()

        ## dictionary page
        content = ""
        content += f"""\
<!DOCTYPE html>
<html>
{HTML_LICENSE}

<head>
    <title>{page_title} - dictionary</title>
    <link rel="stylesheet" type="text/css" href="styles.css">
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
</head>

<body>

<div class="main_section title">{page_title}</div>

"""

        ## generate content
        prev_content = self._prepare_back_to(self.out_root_dir)
        content += prev_content + "\n"

        content += (
            """\n<div class="main_section">Explanation of some definitions used in the characteristics.</div>\n"""
        )

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
            content += """\n<div class="keywords_section">\n"""
            content += keywords_content
            content += """\n</div>\n"""

        content += """
</body>
</html>
"""
        write_data(page_path, content)
        return page_path

    def _prepare_back_to(self, subpage_dir, item_id=None):
        main_page_rel_path = os.path.relpath(self.out_index_path, subpage_dir)
        prev_content = """<div class="main_section">Back to: """
        link_list = [f"""<a href="{main_page_rel_path}">{self.label_back_to_main}</a>"""]

        if item_id:
            nav_dict = self.data_loader.nav_dict
            prev_items = nav_dict.prev_id_list(item_id)
            if prev_items:
                for prev in prev_items:
                    item = f"""<a href="{prev}.html">{prev}</a>"""
                    link_list.append(item)

        prev_content += " | ".join(link_list)
        prev_content += "</div>"
        return prev_content

    def _prepare_defs_table(self, keywords_list, page_dir):
        if not keywords_list:
            return None

        model = self.data_loader.model_data
        model_data: Dict[str, Any] = model.get("data", {})
        model_item_keys = {}
        ## prepare "mentioned" list
        for item_id, desc_list in model_data.items():
            item_keys = []
            for val in desc_list:
                desc_text = val.get("description")
                _desc, desc_keys = self._prepare_description(desc_text)
                item_keys.extend(desc_keys)
            model_item_keys[item_id] = item_keys

        keywords_list = self._append_keywords_in_defs(keywords_list)

        defs_dict = self.data_loader.get_defs_dict()
        keywords_content = ""
        keywords_content += """<table>\n"""
        keywords_content += """<tr class="title_row"> <th colspan="2">Keywords:</th> </tr>\n"""
        for keyword in keywords_list:
            single_keyword_content = f"""<tr class="def_row">
    <td class="def_item"><a name="{keyword}"></a>{keyword}</td>\n"""
            single_keyword_content += """    <td> """

            keyword_data_list = defs_dict[keyword]
            keyword_defs_content = ""
            for keyword_item in keyword_data_list:
                def_text = keyword_item.get("text")
                img_rel_path = None
                photo_path = keyword_item.get("image")
                if photo_path:
                    dest_img_path = self.get_def_photo_path(photo_path)
                    img_rel_path = os.path.relpath(dest_img_path, page_dir)
                description_content = keyword_item.get("description")
                keyword_defs_content = """<div class="imgtile">\n"""
                if def_text:
                    def_text, _def_keys = self._prepare_description(def_text)
                    keyword_defs_content += f"""         <div>{def_text}</div>\n"""
                if img_rel_path:
                    keyword_defs_content += f"""         <a href="{img_rel_path}"><img src="{img_rel_path}"></a>\n"""
                if description_content:
                    keyword_defs_content += f"""         <div>{description_content}</div>\n"""
                keyword_defs_content += """         </div>\n"""

            # ## prepare "mentioned" content
            if keyword_defs_content:
                single_keyword_content += keyword_defs_content

                mentioned_list = []
                for item_id, item_desc_keys in model_item_keys.items():
                    if keyword in item_desc_keys:
                        item_path = os.path.join(self.out_page_dir, f"{item_id}.html")
                        item_rel_path = os.path.relpath(item_path, page_dir)
                        item_link = f"""<a href="{item_rel_path}">{item_id}</a>"""
                        mentioned_list.append(item_link)
                if mentioned_list:
                    items_str = " ".join(mentioned_list)
                    single_keyword_content += f"""         <div>Mentioned in: {items_str}</div>\n"""

                single_keyword_content += """    </td>\n</tr>\n"""
                keywords_content += single_keyword_content

        keywords_content += """</table>\n"""

        keywords_content = keywords_content.replace("\n", "\n    ")
        keywords_content = keywords_content.strip()
        keywords_content = "    " + keywords_content

        return keywords_content

    def _append_keywords_in_defs(self, keywords_list):
        defs_dict = self.data_loader.get_defs_dict()
        counter = 0
        while counter < len(keywords_list):
            keyword = keywords_list[counter]
            counter += 1
            keyword_data_list = defs_dict[keyword]
            for keyword_item in keyword_data_list:
                def_text = keyword_item.get("text")
                if not def_text:
                    continue
                _def_desc, def_keys = self._prepare_description(def_text)
                for item in def_keys:
                    if item not in keywords_list:
                        keywords_list.append(item)
        keywords_list = sorted(list(set(keywords_list)), key=lambda x: x.lower())
        return keywords_list


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


def find_all_defs(content, def_list: List[Any]) -> List[Tuple[int, str]]:
    palces_list = []
    for def_item in def_list:
        def_key, def_match = def_item
        item_content = content
        if def_match is False:
            item_content = content.lower()
        places = find_all(item_content, def_key)
        if not places:
            continue
        for pos in places:
            palces_list.append((pos, def_key))

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


def find_all(content, substring, match_subword=False) -> List[int]:
    ret_list = []
    content_endpos = len(content)
    substr_len = len(substring)
    pos = 0
    while True:
        new_pos = content.find(substring, pos)
        if new_pos < 0:
            break
        pos = new_pos + 1
        if match_subword:
            ret_list.append(new_pos)
            continue
        ## additional match
        if new_pos > 0:
            prev_char = content[new_pos - 1]
            if prev_char.isalpha():
                ## middle of word - skip
                continue
        new_after_endpos = new_pos + substr_len
        if new_after_endpos < content_endpos:
            next_char = content[new_after_endpos]
            if next_char.isalpha():
                ## middle of word - skip
                continue
        ret_list.append(new_pos)
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
