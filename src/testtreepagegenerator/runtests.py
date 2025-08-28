#!/usr/bin/env python3
#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

# ruff: noqa: T201

# try:
#     ## following import success only when file is directly executed from command line
#     ## otherwise will throw exception when executing as parameter for "python -m"
#     # pylint: disable=W0611
#     import __init__
# except ImportError:
#     ## when import fails then it means that the script was executed indirectly
#     ## in this case __init__ is already loaded
#     pass


import argparse
import logging
import os
import re
import sys
import unittest


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# src_dir = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
# sys.path.insert(0, src_dir)


_LOGGER = logging.getLogger(__name__)


def match_tests(pattern: str):
    if pattern.find("*") < 0:
        ## regular module
        loader = unittest.TestLoader()
        return loader.loadTestsFromName(pattern)

    ## wildcarded
    re_pattern = pattern
    # pylint: disable=W1401
    re_pattern = re_pattern.replace("/", ".")
    re_pattern = re_pattern.replace(".", r"\.")
    re_pattern = re_pattern.replace("*", ".*")
    ## re_pattern = "^" + re_pattern + "$"
    _LOGGER.info("searching test cases with pattern: %s", re_pattern)
    loader = unittest.TestLoader()
    tests_suite = loader.discover(SCRIPT_DIR)
    return match_test_suites(tests_suite, re_pattern)


def match_test_suites(tests_list, re_pattern: str):
    ret_suite = unittest.TestSuite()
    for test_object in tests_list:
        if isinstance(test_object, unittest.TestSuite):
            sub_tests = match_test_suites(test_object, re_pattern)
            ret_suite.addTest(sub_tests)
            continue
        if isinstance(test_object, unittest.TestCase):
            classobj = test_object.__class__
            # pylint: disable=W0212,
            # ruff: noqa: SLF001
            test_case_full_name = f"{classobj.__module__}.{classobj.__name__}.{test_object._testMethodName}"
            matched = re.search(re_pattern, test_case_full_name)
            if matched is not None:
                ## _LOGGER.info("test case matched: %s", test_case_full_name )
                ret_suite.addTest(test_object)
            continue
        _LOGGER.warning("unknown type: %s", type(test_object))
    return ret_suite


def get_test_cases(run_test):
    if run_test:
        ## not empty
        return match_tests(run_test)
    tests_loader = unittest.TestLoader()
    return tests_loader.discover(SCRIPT_DIR)


## ============================= main section ===================================


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test runner")
    parser.add_argument("-la", "--logall", action="store_true", help="Log all messages")
    # pylint: disable=C0301
    parser.add_argument(
        "-rt",
        "--run_test",
        action="store",
        required=False,
        default="",
        help="Module with tests, e.g. module.submodule.test_file.test_class.test_method, wildcard * allowed",
    )
    parser.add_argument(
        "-r",
        "--repeat",
        action="store",
        type=int,
        default=0,
        help="Repeat tests given number of times",
    )
    parser.add_argument("-ut", "--untilfailure", action="store_true", help="Run tests in loop until failure")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    logging.basicConfig()
    if args.logall is True:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.ERROR)

    verbosity = 1
    if args.verbose:
        verbosity = 2

    tests_repeats = int(args.repeat)

    ## run proper tests
    if args.untilfailure is True:
        counter = 1
        while True:
            print("Tests iteration:", counter)
            counter += 1
            suite = get_test_cases(args.run_test)
            test_result = unittest.TextTestRunner(verbosity=verbosity).run(suite)
            if test_result.wasSuccessful() is False:
                sys.exit(1)
            print("\n")
    elif tests_repeats > 0:
        for counter in range(1, tests_repeats + 1):
            print("Tests iteration:", counter)
            suite = get_test_cases(args.run_test)
            test_result = unittest.TextTestRunner(verbosity=verbosity).run(suite)
            if test_result.wasSuccessful() is False:
                sys.exit(1)
            print("\n")
    else:
        suite = get_test_cases(args.run_test)
        test_result = unittest.TextTestRunner(verbosity=verbosity).run(suite)
        if test_result.wasSuccessful() is False:
            sys.exit(1)
