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
import random

# Core Django imports
from django.db import models
from django.utils.translation import ugettext_lazy as _

# Third-party app imports
from django_extensions.db.models import TimeStampedModel
from shorturls import baseconv

# MarMix imports
from billing.models import Customer
from users.models import User


def short_code_encode(sim_id, cust_code):
    encoded_id = baseconv.base32.from_decimal(sim_id)
    return "%s-%s" % (cust_code.upper(), encoded_id)


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
    capital = models.DecimalField(verbose_name=_("initial capital"), max_digits=14, decimal_places=4,
                                  default='0.0000', help_text=_("Initial capital paid to each team"))
    currency = models.ForeignKey('Currency', verbose_name=_("currency"),
                                 help_text=_("The currency symbol displayed in the interface (has no impact on the simulation)"))
    state = models.IntegerField(verbose_name=_("state of the simulation"),
                                choices=SIMULATION_STATE_CHOICES, default=CONFIGURING,
                                help_text=_("The current state of this simulation"))

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = 'MM-99999999'
            super(Simulation, self).save(*args, **kwargs)
            self.code = short_code_encode(self.id, self.customer.short_code)
        super(Simulation, self).save(*args, **kwargs)

    def _nb_teams(self):
        teams = self.teams.all().count()
        return teams
    nb_teams = property(_nb_teams)

    class Meta:
        verbose_name = _("simulation")
        verbose_name_plural = _("simulations")
        ordering = ['code']

    def __str__(self):
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
        verbose_name = _("currency")
        verbose_name_plural = _("currencies")
        ordering = ['code']

    def __str__(self):
        if self.symbol:
            return self.symbol
        else:
            return self.code


class Team(TimeStampedModel):
    """
    A team participating in a simulation.
    """
    PLAYERS = 'P'
    LIQUIDITY_MANAGER = 'L'
    TEAM_TYPE_CHOICES = (
        (PLAYERS, _('Players')),
        (LIQUIDITY_MANAGER, _('Liquidity manager')),
    )

    customer = models.ForeignKey(Customer, verbose_name=_('organization'), related_name=_('teams'),
                                 help_text=_("The organization the team belongs to"))
    simulations = models.ManyToManyField('Simulation', verbose_name=_('simulations'), related_name=_('teams'), null=True,
                                         blank=True, help_text=_("The simulation(s) the team belongs to"))
    name = models.CharField(verbose_name=_("name"), max_length=50,
                            help_text=_("A name that can be attributed to the team"))
    team_type = models.CharField(verbose_name=_("type of team"), max_length=10, choices=TEAM_TYPE_CHOICES,
                                 default=PLAYERS,
                                 help_text=_("Indicates if it is a team of players or a liquidity manager"))
    locked = models.BooleanField(verbose_name=_("locked"), default=False,
                                 help_text=_("Locked teams can not log in the simulation"))
    users = models.ManyToManyField(User, verbose_name=_('members'), related_name=_('teams'), null=True, blank=True,
                                   help_text=_("The users belonging to the team"))

    def _get_holdings(self):
        # TODO: Compute it for real ;-)
        holdings = random.randint(10000, 99999)
        return holdings
    get_holdings = property(_get_holdings)

    def _get_members(self):
        return self.users.all().count()
    get_members = property(_get_members)

    class Meta:
        verbose_name = _('team')
        verbose_name_plural = _('teams')
        unique_together = ('customer', 'name')
        ordering = ['customer', 'name']

    def __str__(self):
        return self.name