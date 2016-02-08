# -*- coding: UTF-8 -*-
# models.py
#
# Copyright (C) 2014 HES-SO//HEG Arc
#
# Author(s): Cédric Gaspoz <cedric.gaspoz@he-arc.ch>
#
# This file is part of MarMix.
#
# MarMix is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MarMix is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with MarMix. If not, see <http://www.gnu.org/licenses/>.

# Stdlib imports

# Core Django imports
from django.db import models
from django.utils.translation import ugettext_lazy as _

# Third-party app imports
from django_extensions.db.models import TimeStampedModel

# MarMix imports
from users.models import User


class Customer(TimeStampedModel):
    """
    A customer is the entity who is contractually linked to MarMix. It's usually a Higher Ed institution. Users
    are members of customers' organizations.
    """
    name = models.CharField(verbose_name=_("name"), max_length=100,
                            help_text=_("Customer's name, usually a higher ed institution"))
    short_code = models.CharField(verbose_name=_("short code"), max_length=5, unique=True,
                                  help_text=_("This code is used to create simulation identification code in the user interface"))
    users = models.ManyToManyField(User, verbose_name=_("admin users"), related_name='organizations', blank=True,
                                   help_text=_('Users who are entitled to manage the organization'))

    class Meta:
        verbose_name = _('customer')
        verbose_name_plural = _('customers')
        ordering = ['name']

    def __str__(self):
        return self.name
