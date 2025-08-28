#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import logging
import os

from treepagegenerator.generator.dataloader import get_translation, is_url


SCRIPT_DIR = os.path.dirname(__file__)

_LOGGER = logging.getLogger(__name__)


HTML_LICENSE = """\
<!--
File was automatically generated using 'tree-page-generator' project (https://github.com/anetczuk/tree-page-generator).
Project is distributed under the BSD 3-Clause license.
-->"""


def dict_to_html_table(data_dict, translation_dict=None, table_class=None, *, header=True):
    if data_dict is None:
        return None
    table_css = ""
    if table_class:
        table_css = """ class='detailstable'"""
    content = ""
    content += f"""<table cellspacing="0"{table_css}>\n"""
    if header:
        content += f"""<tr> <th>{get_translation(translation_dict, "Parameter")}:</th>\
 <th>{get_translation(translation_dict, "Value")}:</th> </tr>\n"""
    for key, val in data_dict.items():
        val_str = ""
        if isinstance(val, list):
            val_list = [convert_href_value(item) for item in val]
            val_str = ", ".join(val_list)
        else:
            val_str = convert_href_value(val)
        if not val_str:
            val_str = f"""<span class="empty">[{get_translation(translation_dict, "empty")}]</span>"""
        content += f"""<tr> <td>{key}</td> <td>{val_str}</td> </tr>\n"""
    content += """</table>"""
    return content


def convert_href_value(val):
    if is_url(val):
        return f"""<a href="{val}">{val}</a>"""
    return str(val)
