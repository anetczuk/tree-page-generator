#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import logging
from typing import Dict, Any, List
import math
import json
import shutil
import validators
from PIL import Image


_LOGGER = logging.getLogger(__name__)


class NavDict:

    def __init__(self, model_data):
        ## key: characteristic id
        ## value: pair( next characteristic id, desc index within key characteristic)
        self.next_dict = {}

        ## key: characteristic id
        ## value: pair( prev characteristic id, desc index within prev characteristic)
        self.prev_dict = {}

        for key, desc_list in model_data.items():
            next_list = []
            for desc_index, desc_item in enumerate(desc_list):
                next_id = desc_item.get("next")
                if next_id:
                    next_list.append((next_id, desc_index))
                    self.prev_dict[next_id] = [(key, desc_index)]
                    continue
                target_item = desc_item.get("target")
                if target_item:
                    target_id = target_item[0]
                    next_list.append((target_id, desc_index))
                    self.prev_dict[target_id] = [(key, desc_index)]
                    continue
            self.next_dict[key] = next_list

    def next_item(self, curr_id):
        return self.next_dict.get(curr_id)

    def next_id(self, curr_id):
        item_list = self.next_dict.get(curr_id)
        if not item_list:
            return []
        return [item[0] for item in item_list]

    def prev_item(self, curr_id):
        return self.prev_dict.get(curr_id)

    def prev_id(self, curr_id):
        item_list = self.prev_dict.get(curr_id)
        if not item_list:
            return []
        return [item[0] for item in item_list]

    def prev_id_list(self, curr_item) -> List[str]:
        ret_list: List[str] = []
        prev_items = self.prev_id(curr_item)
        if not prev_items:
            return ret_list
        ret_list.extend(prev_items)
        index = 0
        while index < len(ret_list):
            curr_item = ret_list[index]
            index += 1
            prev_items = self.prev_id(curr_item)
            if not prev_items:
                continue
            ret_list.extend(prev_items)

        ret_list.reverse()
        return ret_list

    def prev_items_list(self, curr_id) -> List[str]:
        ret_list: List[str] = []
        prev_items = self.prev_item(curr_id)
        if not prev_items:
            return ret_list
        ret_list.extend(prev_items)
        index = 0
        while index < len(ret_list):
            curr_item = ret_list[index]
            curr_id = curr_item[0]
            index += 1
            prev_items = self.prev_item(curr_id)
            if not prev_items:
                continue
            ret_list.extend(prev_items)

        ret_list.reverse()
        return ret_list


class DataLoader:
    def __init__(self, config_path, translation_path=None):
        self.config_path = config_path
        self.model_path = None
        self.translation_path = translation_path

        self.config_dict = self._load_config()
        self.model_data = self._load_model()
        self.nav_dict: NavDict = self._load_nav_dict()

        ## key: characteristic id
        ## value: list of species
        self.potential_species: Dict[str, List[str]] = self._load_potential_species()

        self.defs_list: List[Dict[str, Any]] = self._load_all_defs()

        self.translation_dict = self._load_transaltion()

    def _load_config(self) -> Dict[str, Any]:
        _LOGGER.debug("loading config from file %s", self.config_path)
        with open(self.config_path, "r", encoding="utf8") as fp:
            return json.load(fp)

    def _load_model(self) -> Dict[str, Any]:
        model_dir = self.config_dict["model_dir"]
        config_dir = os.path.dirname(self.config_path)
        self.model_path = os.path.join(config_dir, model_dir)

        _LOGGER.debug("loading model from file %s", self.model_path)
        with open(self.model_path, "r", encoding="utf8") as fp:
            return json.load(fp)

    def _load_nav_dict(self) -> NavDict:
        model_data = self.model_data.get("data")
        return NavDict(model_data)

    def _load_potential_species(self) -> Dict[str, List[str]]:
        model_data = self.model_data.get("data")

        ## get leaves
        leaves_list: List[str] = []
        for key, val_list in model_data.items():
            leaf = True
            for val in val_list:
                next_item = val.get("next")
                if next_item:
                    leaf = False
                    break
            if leaf:
                leaves_list.append(key)

        potential_species: Dict[str, List[str]] = {}
        while leaves_list:
            item_key: str = leaves_list.pop(0)
            item_data = model_data[item_key]

            ## get direct targets
            target_labels: List[str] = []
            for val in item_data:
                target = val.get("target")
                if target:
                    target_labels.append(target[0])

            ## get descent targets
            next_keys = self.nav_dict.next_id(item_key)
            for next_key in next_keys:
                next_targets = potential_species.get(next_key)
                if next_targets:
                    target_labels.extend(next_targets)

            potential_species[item_key] = target_labels

            prev_keys = self.nav_dict.prev_id(item_key)
            if prev_keys:
                leaves_list.extend(prev_keys)

        return potential_species

    def _load_transaltion(self) -> Dict[str, str]:
        if not self.translation_path:
            return None
        with open(self.translation_path, "r", encoding="utf8") as fp:
            return json.load(fp)

    def _load_all_defs(self) -> List[Dict[str, Any]]:
        ret_list = []

        defs_dirs = self.config_dict["defs_dirs"]
        config_dir = os.path.dirname(self.config_path)
        for defs_dir in defs_dirs:  # pylint: disable=R1702
            defs_path = os.path.join(config_dir, defs_dir)
            if not os.path.isdir(defs_path):
                continue

            dirs_list = os.listdir(defs_path)
            for dir_item in dirs_list:
                defs_dir_path = os.path.join(defs_path, dir_item)
                defs_file_path = os.path.join(defs_dir_path, "defs.json")
                if not os.path.isfile(defs_file_path):
                    continue
                try:
                    with open(defs_file_path, "r", encoding="utf8") as fp:
                        defs_data = json.load(fp)
                except Exception:
                    _LOGGER.error("unable to load JSON file: %s", defs_file_path)
                    raise

                defs_list = []
                if isinstance(defs_data, list):
                    defs_list = defs_data
                else:
                    defs_list.append(defs_data)

                for defs_dict in defs_list:
                    description_content = defs_dict.get("description")
                    def_items = defs_dict["items"]
                    for item in def_items:
                        image_path = item.get("image")
                        if image_path:
                            image_path = os.path.join(defs_dir_path, image_path)
                            if not os.path.isfile(image_path):
                                _LOGGER.error("could not find image in defs file: %s", defs_file_path)
                            item["image"] = image_path
                        if "description" not in item:
                            item["description"] = description_content
                    ret_list.append(defs_dict)

        return ret_list

    # def get_page_title(self):
    #     page_title = self.config_dict.get("page_title", "")
    #     return self.get_translation(page_title)

    # def get_translation(self, key: str, group: str = None) -> str:
    #     return get_translation(self.translation_dict, key, group)

    def get_model_title(self):
        return self.config_dict["title"]

    def get_model_description(self):
        return self.config_dict["description"]

    def get_total_count(self) -> int:
        data_list = self.model_data.get("data")
        total_count = len(data_list)
        return total_count

    def get_all_leafs(self) -> List[str]:
        model_data = self.model_data.get("data")
        leaves_list: List[str] = []
        for _key, val_list in model_data.items():
            for val in val_list:
                target_item = val.get("target")
                if target_item:
                    leaves_list.append(target_item[0])
        return leaves_list

    def get_target(self, item_id, desc_index):
        model_data = self.model_data.get("data")
        item_data = model_data.get(item_id)
        if not item_data:
            return None
        desc_item = item_data[desc_index]
        return desc_item.get("target")

    def print_info(self):
        json_str = json.dumps(self.model_data, indent=4)
        print(f"model data:\n{json_str}")

        # model_values = to_dict_col_vals(self.model_data)
        # cols_list = list(model_values.keys())[1:]
        # for char_name in cols_list:
        #     values_set = model_values[char_name]
        #     # if "" in values_set:
        #     #     values_set.remove("")
        #     length = len(values_set)
        #     print(f"{char_name}: {length} {values_set}")
        # total_count = self.get_total_count()
        # print("total_count:", total_count)

    def get_all_defs(self) -> List[str]:
        if not self.defs_list:
            return []
        defs_set = set()
        for item in self.defs_list:
            defs = item.get("defs", [])
            defs_set.update(defs)
            def_items = item.get("items")
            for def_item in def_items:
                item_defs = def_item.get("defs", [])
                defs_set.update(item_defs)
        defs_list = list(defs_set)
        defs_list.sort()
        return defs_list

    ## key: keyword
    ## value:
    def get_defs_dict(self) -> Dict[str, Any]:
        if not self.defs_list:
            return {}
        ret_dict: Dict[str, Any] = {}
        for item in self.defs_list:
            names_list = item.get("defs", [])
            items_list = item["items"]
            for def_name in names_list:
                def_list = ret_dict.get(def_name, [])
                ret_dict[def_name] = def_list
                def_list.extend(items_list)
            for item_item in items_list:
                item_defs = item_item.get("defs", [])
                for item_name in item_defs:
                    def_list = ret_dict.get(item_name, [])
                    ret_dict[item_name] = def_list
                    def_list.append(item_item)
        return ret_dict


# ===================================================


def get_translation(translation_dict: Dict[str, Any], key: str, group: str = None) -> str:
    if translation_dict is None:
        return key
    if is_url(key):
        return key
    if group is not None:
        group_dict: Dict[str, str] = translation_dict.get(group)
        return get_translation(group_dict, key)
    value = translation_dict.get(key)
    if value is not None:
        return value
    _LOGGER.warning("translation not found for '%s'", key)
    return key


def is_url(value):
    return validators.url(value)


# ================================================================


def copy_image(source_path, dest_path, resize=False):
    parts = os.path.split(dest_path)
    os.makedirs(parts[0], exist_ok=True)

    if not resize:
        shutil.copyfile(source_path, dest_path, follow_symlinks=True)
        return

    parts = os.path.splitext(source_path)
    if parts[1] in (".svg"):
        shutil.copyfile(source_path, dest_path, follow_symlinks=True)
        return

    with Image.open(source_path) as src_img:
        file_area = src_img.size[0] * src_img.size[1]
        factor = file_area / 1048576  # 1024 x 1024
        if factor > 1.0:
            old_size = src_img.size
            root_factor = math.sqrt(factor)
            width = int(src_img.size[0] / root_factor)
            height = int(src_img.size[1] / root_factor)
            src_img = src_img.resize((width, height), Image.LANCZOS)  # pylint: disable=no-member
            _LOGGER.debug("image %s resized from %s to %s by factor %s", dest_path, old_size, src_img.size, root_factor)
        src_img.save(dest_path, optimize=True, quality=50)
