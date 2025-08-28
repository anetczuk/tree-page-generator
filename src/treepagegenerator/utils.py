#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import datetime
import hashlib
import html
import json
import logging
import os
from collections.abc import Iterable

import pytz
from appdirs import user_data_dir


_LOGGER = logging.getLogger(__name__)


def get_app_datadir():
    data_dir = user_data_dir("tree-page-generator")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def get_recentdate_path():
    data_dir = get_app_datadir()
    return os.path.join(data_dir, "recentdate.obj")


def get_recent_date():
    today_date = datetime.date.today()
    midnight = datetime.datetime.combine(today_date, datetime.time())
    # move back 1 day to prevent short time window where data could be skipped
    midnight = midnight - datetime.timedelta(days=1)
    return add_timezone(midnight)


def string_to_date_general(date_string) -> datetime.datetime:
    try:
        return string_to_date(date_string)
    except ValueError:
        pass

    try:
        return datetime.datetime.fromisoformat(date_string)
    except ValueError:
        _LOGGER.error("unable to convert string '%s' to datetime", date_string)
        raise


# iso format: '2024-06-04T14:23:41Z'
def string_iso_to_date(datetime_string) -> datetime.datetime:
    item_date = datetime.datetime.fromisoformat(datetime_string)
    return add_timezone(item_date)


# handled format: 2024-06-04T14:23:41.077Z
def string_iso2_to_date(datetime_string) -> datetime.datetime:
    item_date = datetime.datetime.strptime(datetime_string, "%Y-%m-%dT%H:%M:%SZ")
    return add_timezone(item_date)


# handled format: 2024-06-04T14:23:41.077Z
def string_isoz_to_date(datetime_string) -> datetime.datetime:
    item_date = datetime.datetime.strptime(datetime_string, "%Y-%m-%dT%H:%M:%S.%fZ")
    return add_timezone(item_date)


def string_isoauto_to_date(datetime_string) -> datetime.datetime:
    try:
        return string_iso2_to_date(datetime_string)
    except ValueError:
        pass
    try:
        return string_isoz_to_date(datetime_string)
    except ValueError:
        pass
    return string_iso_to_date(datetime_string)


def string_to_date(date_string) -> datetime.datetime:
    item_date = datetime.datetime.strptime(date_string, "%Y-%m-%d")
    return add_timezone(item_date)


def string_to_datetime(datetime_string) -> datetime.datetime:
    item_date = datetime.datetime.strptime(datetime_string, "%Y-%m-%d %H:%M:%S")
    return add_timezone(item_date)


def add_timezone(dt: datetime.datetime) -> datetime.datetime:
    tz_info = pytz.timezone("Europe/Warsaw")
    return tz_info.localize(dt)


def convert_to_html(content: str, *, preserve_newline=False) -> str:
    if content is None:
        return None
    if preserve_newline:
        return content.replace("\n", "<br/>\n")
    return content.replace("\n", "<br/>")


def escape_html(content: str) -> str:
    return html.escape(content)


# make various string conversions to meet feed requirements
def normalize_string(content: str) -> str:
    return content.replace("\x02", " ")

    # content = content.encode().decode("utf-8","strict")

    # string_encode = content.encode("ascii", "ignore")
    # return string_encode.decode()

    # return content


def read_data(file_path):
    with open(file_path, encoding="utf8") as fp:
        return fp.read()


def write_data(file_path, content):
    with open(file_path, "w", encoding="utf8") as fp:
        fp.write(content)


def calculate_dict_hash(data_dict):
    data_str = json.dumps(data_dict, sort_keys=True)
    data_bytes = data_str.encode("utf-8")
    # ruff: noqa: S324
    return hashlib.md5(data_bytes).hexdigest()  # nosec


def calculate_hash(data_string):
    data_bytes = data_string.encode("utf-8")
    # ruff: noqa: S324
    return hashlib.md5(data_bytes).hexdigest()  # nosec


## =====================================================


class ObjRepr:
    def __init__(self):
        self._visited = set()

    def repr_obj(self, obj):
        self._visited.clear()
        return self._visit(obj)

    # ruff: noqa: C901, PLR0911
    def _visit(self, obj):
        obj_id = id(obj)
        if obj_id in self._visited:
            # print("visited:", type(next_obj), next_obj)
            return obj
        self._visited.add(obj_id)

        if isinstance(obj, dict):
            ret_dict = {}
            for key, data in obj.items():
                ret_dict[key] = self._visit(data)
            return ret_dict

        if hasattr(obj, "__dict__"):
            ret_dict = {"___type___": type(obj).__name__, "___id___": id(obj)}
            for key, data in obj.__dict__.items():
                ret_dict[key] = self._visit(data)
            return ret_dict

        if hasattr(obj, "__slots__"):
            ret_dict = {"___type___": type(obj).__name__, "___id___": id(obj)}
            for key in obj.__slots__:
                data = getattr(obj, key)
                ret_dict[key] = self._visit(data)
            return ret_dict

        if isinstance(obj, str):
            return obj

        if isinstance(obj, Iterable):
            return [self._visit(data) for data in obj]

        return obj


def obj_to_dict(obj):
    repr_obj = ObjRepr()
    return repr_obj.repr_obj(obj)
