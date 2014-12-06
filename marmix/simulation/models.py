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
from billing.models import Customer
from users.models import User


class Simulation(TimeStampedModel):
    """
    A simulation hold all configuration parameters used to setup and run a simulation.
    """
    INTRO = 'IN'
    ADVANCED = 'AD'
    LIVE = 'LI'
    INDEXED = 'ID'
    SIMULATION_TYPE_CHOICES = (
        (INTRO, _('Introduction')),
        (ADVANCED, _('Advanced')),
        (LIVE, _('Live simulation')),
        (INDEXED, _('Indexed simulation')),
    )

    CONFIGURING = 0
    INITIALIZING = 1
    READY = 2
    RUNNING = 3
    PAUSED = 4
    FINISHED = 5
    ARCHIVED = 9
    SIMULATION_STATE_CHOICES = (
        (CONFIGURING, _('Configuring')),
        (INITIALIZING, _('Initializing')),
        (READY, _('Ready to play')),
        (RUNNING, _('Running')),
        (PAUSED, _('Paused')),
        (FINISHED, _('Finished')),
        (ARCHIVED, _('Archived (closed)')),
    )
    code = models.CharField(verbose_name=_("code"), max_length=15, unique=True, blank=True,
                            help_text=_("The code of the simulation (for the user interface)"))
    customer = models.ForeignKey(Customer, verbose_name=_('customer'), related_name=_('simulations'),
                                 help_text=_("The customer account running this simulation"))
    user = models.ForeignKey(User, verbose_name=_('user'), related_name=_('simulations'),
                             help_text=_("The user account running this simulation"))
    simulation_type = models.CharField(verbose_name=_("type of simulation"), max_length=2,
                                       choices=SIMULATION_TYPE_CHOICES, default=INTRO,
                                       help_text=_("The type of this simulation"))
    teams = models.IntegerField(verbose_name=_("number of teams"), max_length=3,
                                default=1, help_text=_("Number of teams playing (does not include admin accounts"))
    capital = models.DecimalField(verbose_name=_("initial capital"), max_digits=14, decimal_places=4,
                                  default='0.0000', help_text=_("Initial capital paid to each team"))
    currency = models.ForeignKey('Currency', verbose_name=_('currency'),
                                 help_text=_('The currency symbol displayed in the interface (has no impact on the simulation'))
    state = models.IntegerField(verbose_name=_("state of the simulation"), max_length=2,
                                choices=SIMULATION_STATE_CHOICES, default=CONFIGURING,
                                help_text=_("The current state of this simulation"))

    class Meta:
        verbose_name = _('simulation')
        verbose_name_plural = _('simulations')
        ordering = ['code']

    def __unicode__(self):
        return self.code


class Currency(models.Model):
    """
    A currency, used for display purpose in each views. It has no incidence on the core of the simulation.
    """
    code = models.CharField(verbose_name=_("code of currency"), max_length=3,
                            help_text=_("The ISO code of the currency"))
    symbol = models.CharField(verbose_name=_("symbol of currency"), max_length=3, blank=True, null=True,
                              help_text=_("The symbol of the currency"))

    class Meta:
        verbose_name = _('currency')
        verbose_name_plural = _('currencies')
        ordering = ['code']

    def __unicode__(self):
        if self.symbol:
            return self.symbol
        else:
            return self.code