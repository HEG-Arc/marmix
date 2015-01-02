#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import marmix
version = '3.0.1'

setup(
    name='MarMix',
    version=version,
    author='',
    author_email='cedric.gaspoz@he-arc.ch',
    packages=[
        'marmix',
    ],
    include_package_data=True,
    install_requires=[
        'Django>=1.7.1',
    ],
    zip_safe=False,
    scripts=['marmix/manage.py'],
)
