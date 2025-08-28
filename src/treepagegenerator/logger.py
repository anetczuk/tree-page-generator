#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import logging
import os
import sys
from logging import handlers


SCRIPT_DIR = os.path.dirname(__file__)
output_file = None


def get_logging_output_file(log_dir=None):
    if not log_dir:
        log_dir = os.path.join(SCRIPT_DIR, "../../tmp/log")
    log_dir = os.path.abspath(log_dir)
    os.makedirs(log_dir, exist_ok=True)
    if os.path.isdir(log_dir) is False:
        ## something bad happened (or unable to create directory)
        log_dir = os.getcwd()

    return os.path.join(log_dir, "log.txt")


def configure(log_file=None, log_dir=None, log_level=None):
    # pylint: disable=W0603
    # ruff: noqa: PLW0603
    global output_file
    output_file = log_file
    if output_file is None:
        output_file = get_logging_output_file(log_dir)

    if log_level is None:
        log_level = logging.DEBUG

    ## rotation of log files, 1048576 equals to 1MB
    file_handler = handlers.RotatingFileHandler(filename=output_file, mode="a+", maxBytes=1048576, backupCount=999)
    ## file_handler    = logging.FileHandler( filename=output_file, mode="a+" )
    console_handler = logging.StreamHandler(stream=sys.stdout)

    formatter = create_formatter()

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logging.root.addHandler(console_handler)
    logging.root.addHandler(file_handler)
    logging.root.setLevel(log_level)

    logging.getLogger("matplotlib").setLevel(logging.WARNING)

    logging.getLogger("urllib3").setLevel(logging.INFO)


##     loggerFormat   = '%(asctime)s,%(msecs)-3d %(levelname)-8s %(threadName)s [%(filename)s:%(lineno)d] %(message)s'
##     dateFormat     = '%Y-%m-%d %H:%M:%S'
##     logging.basicConfig( format   = loggerFormat,
##                          datefmt  = dateFormat,
##                          level    = logging.DEBUG,
##                          handlers = [ fileHandler, consoleHandler ]
##                        )


def configure_console(log_level=None):
    if log_level is None:
        log_level = logging.DEBUG

    console_handler = logging.StreamHandler(stream=sys.stdout)

    formatter = create_formatter()

    console_handler.setFormatter(formatter)

    logging.root.addHandler(console_handler)
    logging.root.setLevel(log_level)


def create_stdout_handler():
    formatter = create_formatter()
    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(formatter)
    return console_handler


def create_formatter(logger_format=None):
    if logger_format is None:
        logger_format = (
            "%(asctime)s,%(msecs)-3d %(levelname)-8s %(threadName)s %(name)s:%(funcName)s "
            "[%(filename)s:%(lineno)d] %(message)s"
        )
    date_format = "%Y-%m-%d %H:%M:%S"
    return EmptyLineFormatter(logger_format, date_format)
    ## return logging.Formatter( logger_format, date_format )


class EmptyLineFormatter(logging.Formatter):
    """Special formatter storing empty lines without formatting."""

    ## override base class method
    def format(self, record):
        msg = record.getMessage()
        clear_msg = msg.replace("\n", "")
        clear_msg = clear_msg.replace("\r", "")
        if not clear_msg:
            # empty
            return msg
        return super().format(record)


def print_log_tree():
    # ruff: noqa: T201
    print(logging.root.manager.loggerDict.keys())  # pylint: disable=no-member
