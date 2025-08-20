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
import base64
from PIL import Image

from showgraph.graphviz import Graph, set_node_style

from treepagegenerator.utils import write_data, read_data
from treepagegenerator.generator.dataloader import DataLoader, copy_image, DefItem
from treepagegenerator.generator.utils import HTML_LICENSE
from treepagegenerator.data import DATA_DIR


SCRIPT_DIR = os.path.dirname(__file__)

_LOGGER = logging.getLogger(__name__)

logging.getLogger("PIL").setLevel(logging.WARNING)


def generate_pages(config_path, translation_path, output_path, embedcss=False, embedimages=False):
    gen = StaticGenerator()
    data_loader = DataLoader(config_path, translation_path)
    gen.generate(data_loader, output_path, embedcss=embedcss, embedimages=embedimages)

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

        self.embedcss = False
        self.embedimages = False

        self.label_back_to_main = "Main page"
        self.label_characteristic = "cecha"
        self.label_value = "wartość"

        self.data_loader: DataLoader = None

        self._model_texts = {}
        self._def_texts = {}

    def generate(self, data_loader: DataLoader, output_path, embedcss=False, embedimages=False):
        self.embedcss = embedcss
        self.embedimages = embedimages
        self.page_counter = 0

        self.out_root_dir = output_path
        os.makedirs(self.out_root_dir, exist_ok=True)

        self.out_img_dir = os.path.join(self.out_root_dir, "img")
        if not self.embedimages:
            os.makedirs(self.out_img_dir, exist_ok=True)

        self.data_loader = data_loader

        model = self.data_loader.model_data
        model_data: Dict[str, Any] = model.get("data", {})

        self.total_count = data_loader.get_total_count()
        self.total_count += 3  ## additional predefined pages

        self._prepare_texts()

        ## prepare index page
        self._generate_index_page()

        ## prepare characteristic pages
        for item_id in model_data:
            self._generate_model_page(item_id)

        ## prepare species page
        self._generate_species_index_page()

        ## prepare species pages
        all_species = self.data_loader.get_all_leafs()
        for item in all_species:
            self._generate_species_page(item)

        ## prepare dictionary page
        self._generate_dictionary_page()

    def _prepare_texts(self):
        self._model_texts = {}
        self._def_texts = {}

        ## prepare model texts
        model = self.data_loader.model_data
        model_data: Dict[str, Any] = model.get("data", {})
        for item_id, desc_list in model_data.items():
            prepared_list = []
            for val in desc_list:
                value = val.get("description")
                desc, desc_keys = self._prepare_description(value)
                prepared_list.append((val, desc, desc_keys))
            self._model_texts[item_id] = prepared_list

        ## prepare dictionary texts
        defs_dict: Dict[str, Any] = self.data_loader.get_defs_dict()
        for keyword, keyword_data_list in defs_dict.items():
            prepared_list = []
            for keyword_item in keyword_data_list:
                def_text = keyword_item.get("text")
                if not def_text:
                    prepared_list.append(None)
                    continue
                def_desc, def_keys = self._prepare_description(def_text)
                prepared_list.append((def_text, def_desc, def_keys))
            self._def_texts[keyword] = prepared_list

    def _generate_index_page(self):
        model = self.data_loader.model_data
        model_start = model.get("start")
        self.out_index_path = os.path.join(self.out_root_dir, "index.html")

        page_title = self.data_loader.get_model_title()
        model_desc = self.data_loader.get_model_description()

        css_content = self._prepare_css(self.out_root_dir)
        images_content = self._prepare_images_content()  ## no keywords

        ## main/index page
        content = ""
        content += f"""\
<!DOCTYPE html>
<html>
{HTML_LICENSE}

<head>
    <title>{page_title}</title>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    {css_content}
    {images_content}
</head>

<body>
"""
        content += f"""
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
"""
        content += """
</body>
</html>
"""
        self._store_content(self.out_index_path, content)

        if not self.embedcss:
            css_styles_path = os.path.join(DATA_DIR, "styles.css")
            shutil.copy(css_styles_path, self.out_root_dir, follow_symlinks=True)

        self.out_page_dir = os.path.join(self.out_root_dir, "page")
        os.makedirs(self.out_page_dir, exist_ok=True)

    def _prepare_css(self, page_dir):
        if not self.embedcss:
            css_target_path = os.path.join(self.out_root_dir, "styles.css")
            css_rel_path = os.path.relpath(css_target_path, page_dir)
            return f"""<link rel="stylesheet" type="text/css" href="{css_rel_path}">"""

        ## embed
        css_source_path = os.path.join(DATA_DIR, "styles.css")
        css_content = read_data(css_source_path)
        page_script_content = f"""<style>
{css_content}
    </style>
"""
        return page_script_content

    def _generate_model_page(self, item_id):
        page_path = os.path.join(self.out_page_dir, f"{item_id}.html")

        page_content, keywords_list = self._prepare_model_subpage_content(item_id)
        images_list = self._get_image_paths_from_defs(keywords_list)

        page_title = self.data_loader.get_model_title()
        css_content = self._prepare_css(self.out_page_dir)
        images_content = self._prepare_images_content(images_list)

        ## characteristic page
        content = ""
        content += f"""\
<!DOCTYPE html>
<html>
{HTML_LICENSE}

<head>
    <title>{page_title} - characteristics</title>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    {css_content}
    {images_content}
</head>

<body>
"""
        content += f"""
<div class="main_section title">{page_title}</div>

"""

        ## generate content
        prev_content = self._prepare_back_to(self.out_page_dir, item_id)
        content += prev_content + "\n"
        content += page_content
        content += """
</body>
</html>
"""
        self._store_content(page_path, content)

    def _get_image_paths_from_defs(self, keywords_list: List[DefItem]):
        ret_list = []
        defs_dict = self.data_loader.get_defs_dict()
        for keyword_def in keywords_list:
            keyword = keyword_def.defvalue
            keyword_data_list = defs_dict[keyword]
            for keyword_item in keyword_data_list:
                photo_path = keyword_item.get("image")
                if photo_path:
                    ret_list.append(photo_path)
        return ret_list

    def _prepare_model_subpage_content(self, item_id) -> Tuple[str, List[DefItem]]:
        model = self.data_loader.model_data
        model_data: Dict[str, Any] = model.get("data", {})
        desc_list = model_data[item_id]
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
        prepare_desc_list = self._model_texts[item_id]
        char_keywords = set()
        table_content += "<tr>"
        for prep_data in prepare_desc_list:
            _value, desc, desc_keys = prep_data
            char_keywords.update(desc_keys)
            table_content += f"""\n   <td>{desc}</td>"""
        table_content += "\n</tr>\n"
        keywords_list: List[DefItem] = list(char_keywords)

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
        if keywords_list:
            keywords_list = self._get_related_keywords(keywords_list)
            content += """\n<div class="keywords_section">\n"""
            content += self._prepare_defs_table(keywords_list, self.out_page_dir)
            content += """\n</div>\n"""

        return content, keywords_list

    def get_def_photo_path(self, source_def_path):
        base_path = get_path_components(source_def_path, 2)  ## filename with dir name
        base_path = prepare_filename(base_path)
        dest_img_path = os.path.join(self.out_img_dir, base_path)
        return dest_img_path

    def _prepare_img(self, photo_path, page_dir):
        if not photo_path:
            return None
        dest_img_path = self.get_def_photo_path(photo_path)
        if not dest_img_path:
            return None

        if not self.embedimages:
            img_rel_path = os.path.relpath(dest_img_path, page_dir)
            if not img_rel_path:
                return None
            return f"""<img class="image" src="{img_rel_path}"/>"""

        ## embed
        img_rel_path = os.path.relpath(dest_img_path, self.out_img_dir)
        if not img_rel_path:
            return None
        image_id = prepare_image_id(img_rel_path)
        return f"""<div class="image {image_id}"></div>"""

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

    def _prepare_description(self, description) -> Tuple[str, List[DefItem]]:
        description_defs_list: List[DefItem] = self.data_loader.get_all_defs()
        ret_descr = description
        ret_keywords: List[DefItem] = []

        places: List[Tuple[int, DefItem]] = find_all_defs(description, description_defs_list)
        places = sorted(places, key=lambda x: (x[0], -len(x[1].defvalue)))
        places.reverse()
        for place_item in places:
            pos: int = place_item[0]
            def_item: DefItem = place_item[1]
            def_keyword = def_item.defvalue
            def_len = len(def_keyword)
            end_pos = pos + def_len
            ## add suffix to def
            ret_descr = ret_descr[:end_pos] + "</a>" + ret_descr[end_pos:]
            ## add prefix to def
            ret_descr = ret_descr[:pos] + f"""<a href="#{def_keyword}" class="def_item">""" + ret_descr[pos:]
            ret_keywords.append(def_item)

        return ret_descr, ret_keywords

    def _generate_species_index_page(self):
        page_path = os.path.join(self.out_root_dir, "species.html")

        page_title = self.data_loader.get_model_title()

        css_content = self._prepare_css(self.out_root_dir)
        images_content = self._prepare_images_content()  ## no keywords

        ## species list page
        content = ""
        content += f"""\
<!DOCTYPE html>
<html>
{HTML_LICENSE}

<head>
    <title>{page_title} - species</title>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    {css_content}
    {images_content}
</head>

<body>
"""
        content += f"""
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
        self._store_content(page_path, content)

    def _generate_species_page(self, species_id):
        species_id_low = prepare_filename(species_id)
        page_path = os.path.join(self.out_page_dir, f"{species_id_low}.html")

        prev_list = self.data_loader.nav_dict.prev_items_list(species_id)

        ## characteristics list
        char_keywords = set()
        characteristic_content = """<ul class="characteristic_list">\n"""
        for prev_item in prev_list:
            prev_id = prev_item[0]
            prev_desc_index = prev_item[1]
            prev_data = self._model_texts[prev_id]
            prev_desc_item = prev_data[prev_desc_index]
            _prev_desc, desc, desc_keys = prev_desc_item
            char_keywords.update(desc_keys)
            char_link = f"""<a href="{prev_id}.html">{prev_id}</a>"""
            characteristic_content += f"""<li>{char_link}: {desc}</li>\n"""
        characteristic_content += "</ul>\n"
        keywords_list: List[DefItem] = list(char_keywords)

        ## keywords row
        if keywords_list:
            keywords_list = self._get_related_keywords(keywords_list)
            characteristic_content += """\n<div class="keywords_section">\n"""
            characteristic_content += self._prepare_defs_table(keywords_list, self.out_page_dir)
            characteristic_content += """\n</div>\n"""
        images_list = self._get_image_paths_from_defs(keywords_list)

        last_item = prev_list[-1]
        species_target = self.data_loader.get_target(*last_item)
        species_name = species_target[0]

        page_title = self.data_loader.get_model_title()

        css_content = self._prepare_css(self.out_page_dir)
        images_content = self._prepare_images_content(images_list)

        ## species page
        content = ""
        content += f"""\
<!DOCTYPE html>
<html>
{HTML_LICENSE}

<head>
    <title>{page_title} - {species_name}</title>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    {css_content}
    {images_content}
</head>

<body>
"""
        content += f"""
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

        content += characteristic_content
        content += """
</body>
</html>
"""
        self._store_content(page_path, content)

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

    def _generate_dictionary_page(self):
        page_path = os.path.join(self.out_root_dir, "dictionary.html")

        keywords_list = []
        for prepare_desc_list in self._model_texts.values():
            for prep_data in prepare_desc_list:
                if not prep_data:
                    continue
                _desc_raw, _desc, desc_keys = prep_data
                keywords_list.extend(desc_keys)
        keywords_list = self._get_related_keywords(keywords_list)
        images_list = self._get_image_paths_from_defs(keywords_list)

        page_title = self.data_loader.get_model_title()
        css_content = self._prepare_css(self.out_root_dir)
        images_content = self._prepare_images_content(images_list)

        ## dictionary page
        content = ""
        content += f"""\
<!DOCTYPE html>
<html>
{HTML_LICENSE}

<head>
    <title>{page_title} - dictionary</title>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    {css_content}
    {images_content}
</head>

<body>
"""
        content += f"""
<div class="main_section title">{page_title}</div>

"""

        ## generate content
        prev_content = self._prepare_back_to(self.out_root_dir)
        content += prev_content + "\n"

        content += (
            """\n<div class="main_section">Explanation of some definitions used in the characteristics.</div>\n"""
        )

        ## copy images
        if not self.embedimages:
            defs_dict = self.data_loader.get_defs_dict()
            for keyword_def in keywords_list:
                keyword = keyword_def.defvalue
                keyword_data_list = defs_dict[keyword]
                for keyword_item in keyword_data_list:
                    photo_path = keyword_item.get("image")
                    if not photo_path:
                        continue
                    dest_img_path = self.get_def_photo_path(photo_path)
                    if dest_img_path:
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
        self._store_content(page_path, content)

    def _prepare_images_content(self, source_image_path_list=None):
        if not self.embedimages:
            return ""
        if not source_image_path_list:
            return ""

        source_image_path_list = list(set(source_image_path_list))

        img_class_list = []
        for photo_path in source_image_path_list:
            dest_img_path = self.get_def_photo_path(photo_path)
            if not dest_img_path:
                continue
            img_rel_path = os.path.relpath(dest_img_path, self.out_img_dir)
            if not img_rel_path:
                continue
            image_id = prepare_image_id(img_rel_path)

            # with open(photo_path, "rb") as image_file:
            #     encoded_string = base64.b64encode(image_file.read())
            #     img_text = encoded_string.decode('utf-8')

            img = Image.open(photo_path)
            img_w, img_h = img.size
            img_scale = 512 / img_w
            img_w = 512
            img_h = int(img_h * img_scale)
            newimg = img.resize((img_w, img_h), Image.LANCZOS)  # pylint: disable=E1101
            buffered = io.BytesIO()
            newimg.save(buffered, img.format)
            encoded_string = base64.b64encode(buffered.getvalue())
            img_text = encoded_string.decode("utf-8")

            css_content = f"""\
.{image_id} {{
    width: {img_w}px;
    height: {img_h}px;
    background-repeat: no-repeat;
    background-image: url(data:image/png;base64,{img_text});
}}
"""
            img_class_list.append(css_content)

        css_content = "\n".join(img_class_list)
        page_script_content = f"""<style>
/* images */
{css_content}
    </style>
"""
        return page_script_content

    def _get_related_keywords(self, def_key_list: List[DefItem]) -> List[DefItem]:
        def_key_list = self._append_keywords_in_defs(def_key_list)
        ## remove duplicates
        def_key_list = list({item.defvalue: item for item in def_key_list}.values())
        def_key_list.sort(key=lambda x: x.get_label().lower())
        return def_key_list

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

    def _prepare_defs_table(self, keywords_list: List[DefItem], page_dir):  # pylint: disable=R0914
        if not keywords_list:
            return None

        ## prepare "mentioned" list
        model_item_keys = {}
        for item_id, prep_desc_list in self._model_texts.items():
            item_keys = []
            for prep_item in prep_desc_list:
                _desc_text, _desc, desc_keys = prep_item
                item_keys.extend([item.defvalue for item in desc_keys])
            model_item_keys[item_id] = item_keys

        defs_dict: Dict[str, Any] = self.data_loader.get_defs_dict()
        keywords_content = ""
        keywords_content += """<table>\n"""
        keywords_content += """<tr class="title_row"> <th colspan="2">Keywords:</th> </tr>\n"""
        for keyword_def in keywords_list:
            keyword = keyword_def.defvalue
            keyword_label = keyword_def.get_label()
            single_keyword_content = f"""<tr class="def_row">
    <td class="def_item"><a name="{keyword}"></a>{keyword_label}</td>\n"""
            single_keyword_content += """    <td> """

            keyword_data_list = defs_dict[keyword]
            keyword_text_list = self._def_texts[keyword]
            keyword_defs_content = ""
            for keyword_index, keyword_item in enumerate(keyword_data_list):
                photo_path = keyword_item.get("image")
                img_content = self._prepare_img(photo_path, page_dir)
                description_content = keyword_item.get("description")
                keyword_defs_content = """<div class="imgtile">\n"""
                def_item = keyword_text_list[keyword_index]
                if def_item:
                    _def_raw, def_text, _def_keys = def_item
                    keyword_defs_content += f"""         <div>{def_text}</div>\n"""
                if img_content:
                    keyword_defs_content += f"""         {img_content}\n"""
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

    def _append_keywords_in_defs(self, keywords_list: List[DefItem]):
        counter = 0
        found_keywords = {item.defvalue for item in keywords_list}
        while counter < len(keywords_list):
            keyword_def = keywords_list[counter]
            keyword = keyword_def.defvalue
            counter += 1
            keyword_data_list = self._def_texts[keyword]
            for def_item in keyword_data_list:
                if not def_item:
                    continue
                _def_raw, _def_desc, def_keys = def_item
                for item in def_keys:
                    if item.defvalue not in found_keywords:
                        found_keywords.add(item.defvalue)
                        keywords_list.append(item)
        keywords_list = sorted(list(set(keywords_list)), key=lambda x: x.defvalue.lower())
        return keywords_list

    def _store_content(self, page_path, content):
        self.page_counter += 1
        progress = self.page_counter / self.total_count * 100
        # progress = int(self.page_counter / self.total_count * 10000) / 100
        _LOGGER.debug("%.2f%% storing page: %s", progress, page_path)
        write_data(page_path, content)


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


def find_all_defs(content, def_list: List[DefItem]) -> List[Tuple[int, DefItem]]:
    palces_list = []
    for def_item in def_list:
        def_key = def_item.defvalue
        def_match = def_item.casesensitive
        item_content = content
        if def_match is False:
            item_content = content.lower()
        places = find_all(item_content, def_key)
        if not places:
            continue
        for pos in places:
            palces_list.append((pos, def_item))

    ret_list = []
    recent_end = -1
    palces_list = sorted(palces_list, key=lambda x: (x[0], -len(x[1].defvalue)))
    for pos_item in palces_list:
        pos = pos_item[0]
        if pos <= recent_end:
            continue
        ret_list.append(pos_item)
        pos_end = pos + len(pos_item[1].defvalue)
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


def prepare_image_id(img_path: str):
    image_id = img_path
    image_id = image_id.replace(".", "_")
    image_id = image_id.replace("-", "_")
    image_id = image_id.replace("/", "_")
    image_id = image_id.replace("\\", "_")
    return f"image_{image_id}"


def prepare_filename(name: str):
    name = name.lower()
    name = re.sub(r"\s+", "_", name)
    # name = name.replace(".", "_")
    name = name.replace("(", "_")
    name = name.replace(")", "_")
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
