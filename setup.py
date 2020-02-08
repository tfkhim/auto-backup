#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name = "auto-backup",
    version = "0.1",
    py_modules = ["auto-backup"],

    install_requires = ["aioxmpp>=0.10.5"]
)
