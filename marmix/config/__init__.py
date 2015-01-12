# -*- coding: utf-8 -*-
from __future__ import absolute_import

from .local import Local  # noqa
from .production import Production  # noqa
from .celery import app as celery_app  # noqa
