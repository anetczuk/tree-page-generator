#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import logging
from typing import Dict, Any

import time
import json
import requests

from treepagegenerator.utils import write_data


SCRIPT_DIR = os.path.dirname(__file__)

_LOGGER = logging.getLogger(__name__)


def parse_license_file(license_path, output_path):
    loader = LicenseLoader(license_path)
    license_dict = loader.license_dict

    photos_dict: Dict[Any, Any] = {}
    for license_item in license_dict:
        item = license_item["item"][0]
        item_photos = photos_dict.get(item, [])
        item_photos.append(license_item)
        photos_dict[item] = item_photos

    for item, values in photos_dict.items():
        out_dir = os.path.join(output_path, item)
        os.makedirs(out_dir, exist_ok=True)
        for photo_index, photo_data in enumerate(values):
            photo_url = photo_data["direct_url"][0]
            file_name = f"""{photo_index}.img"""
            license_dict = {}
            license_dict["url"] = photo_url
            license_dict["filename"] = file_name
            license_dict["attribution"] = photo_data["attribution"][0]
            out_img_path = os.path.join(out_dir, file_name)
            _LOGGER.debug("downloading file %s to %s", photo_url, out_img_path)
            download_image(photo_url, out_img_path, retry=True)
            out_lic_path = os.path.join(out_dir, f"""{file_name}.lic""")
            out_content = json.dumps(license_dict, indent=4)
            write_data(out_lic_path, out_content)


## ============================================


class LicenseLoader:
    def __init__(self, license_path):
        self.license_path = license_path
        self.license_dict = self._load()

    def _load(self):
        return {}
        # frames = []
        # for index in range(0, 99):
        #     license_data: DataFrame = load_table_from_excel(
        #         self.license_path, "Data:", assume_default=False, sheet_index=index
        #     )
        #     if license_data is None:
        #         break
        #     sub_data: DataFrame = license_data[["item", "direct_url", "attribution"]]
        #     print(sub_data)
        #     frames.append(sub_data)
        # result = pandas.concat(frames)
        # result = result.reset_index(drop=True)
        # data_list = to_dict_list(result)
        # return data_list


def download_image(url, output_path, retry=False) -> bool:
    while True:
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            if not retry:
                return False
            _LOGGER.debug("could not download file from %s, retrying", url)
            time.sleep(1.0)
            continue
        img_data = response.content
        with open(output_path, "wb") as handler:
            handler.write(img_data)
        return True
