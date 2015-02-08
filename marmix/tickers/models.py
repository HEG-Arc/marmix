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
import datetime

# Core Django imports
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.cache import cache
from django.utils import timezone

# Third-party app imports
from django_extensions.db.models import TimeStampedModel

# MarMix imports
from simulations.models import Simulation
from stocks.models import Stock


class Ticker(TimeStampedModel):
    simulation = models.OneToOneField(Simulation, verbose_name=_("simulation"), help_text=_("Related simulation"))
    nb_companies = models.IntegerField(verbose_name=_("number of companies"), null=True, blank=True, help_text=_("Number of real/simulated companies"))
    initial_value = models.IntegerField(verbose_name=_("initial daily dividend value"), default="1", help_text=_("Initial value of the dividend par day (try with 1.00)"))
    state = models.IntegerField(verbose_name=_("state of the ticker"),
                                choices=Simulation.SIMULATION_STATE_CHOICES, default=Simulation.CONFIGURING,
                                help_text=_("Current state of this ticker"))
    with_drift = models.BooleanField(verbose_name=_("display the drift"), default=False, help_text=_("Advanced simulations display the drift"))
    nb_rounds = models.IntegerField(verbose_name=_("number of rounds"), default="4", help_text=_("Number of simulation rounds"))
    nb_days = models.IntegerField(verbose_name=_("number of days per round"), default="10", help_text=_("Number of days in a simulation round"))
    day_duration = models.IntegerField(verbose_name=_("duration of a day"), default="60", help_text=_("Duration of each simulation day in seconds"))
    dividend_payoff_rate = models.DecimalField(verbose_name=_("dividend payoff rate"), max_digits=14, decimal_places=4,
                                               default='30.0000', help_text=_("Payoff rate in percent. To disable dividend payoff, set to 0.00"))
    transaction_costs = models.DecimalField(verbose_name=_("transaction cost"), max_digits=14, decimal_places=4,
                                            default='5.5000', help_text=_("Amount to be paid for one transaction. To disable transaction costs, set to 0.00"))
    interest_rate = models.DecimalField(verbose_name=_("interest rate"), max_digits=14, decimal_places=4,
                                        default='3.0000', help_text=_("Interest rate retributing portfolios. To disable retribution of cash, set to 0.00"))
    fixed_interest_rate = models.BooleanField(verbose_name=_("fixed interest rate"), default=False, help_text=_("If fixed, the interest rate will not vary accross time"))
    # TODO: Add fields needed for the live simulation

    class Meta:
        verbose_name = _('ticker')
        verbose_name_plural = _('tickers')
        ordering = ['simulation']

    def _last_tick(self):
        tick = cache.get('tick-%s' % self.simulation_id)
        if tick:
            last_tick = tick
        else:
            try:
                last_tick = self.ticks.all()[0]
            except IndexError:
                last_tick = None
        return last_tick
    last_tick = property(_last_tick)

    def save(self, *args, **kwargs):
        if self.simulation_id:
            cache.delete('ticker-%s' % self.simulation_id)
        super(Ticker, self).save(*args, **kwargs)

    def __str__(self):
        return self.simulation.__str__()


class TickerCompany(models.Model):
    """
    Stocks are shares of a company that are automatically generated during the simulation setup.
    """
    ticker = models.ForeignKey('Ticker', verbose_name=_("ticker"), related_name="companies", help_text=_("Related ticker"))
    symbol = models.CharField(verbose_name=_("symbol"), max_length=4, help_text=_("Symbol of the company (4 chars)"))
    name = models.CharField(verbose_name=_("name"), max_length=100, help_text=_("Full name of the company"))
    stock = models.ForeignKey(Stock, verbose_name=_("stock"), related_name="companies", help_text=_("Related stock"))
    description = models.TextField(verbose_name=_("description"), blank=True, help_text=_("Description of the stock (HTML)"))

    class Meta:
        verbose_name = _('company')
        verbose_name_plural = _('companies')
        ordering = ['symbol']

    def __str__(self):
        return self.name


class CompanyFinancial(models.Model):
    company = models.ForeignKey('TickerCompany', verbose_name=_("company"), related_name="financials", help_text=_("Related company"))
    daily_dividend = models.DecimalField(verbose_name=_("daily dividend"), max_digits=14, decimal_places=4,
                                         default='0.0000', help_text=_("Daily simulated dividend"))
    daily_net_income = models.DecimalField(verbose_name=_("daily net income"), max_digits=14, decimal_places=4,
                                           default='0.0000', help_text=_("Daily simulated net income"))
    sim_round = models.IntegerField(verbose_name=_("round"), default=0, help_text=_("Current round"))
    sim_day = models.IntegerField(verbose_name=_("day"), default=0, help_text=_("Current day"))
    sim_date = models.IntegerField(verbose_name=_("date"), default=0, help_text=_("Current date"))

    class Meta:
        verbose_name = _('financial')
        verbose_name_plural = _('financials')
        ordering = ['-sim_round', '-sim_day']

    def __str__(self):
        return "%s-R%sD%s %s" % (self.company, self.sim_round, self.sim_day, self.daily_net_income)


class CompanyShare(models.Model):
    company = models.ForeignKey('TickerCompany', verbose_name=_("company"), related_name="shares", help_text=_("Related company"))
    share_value = models.DecimalField(verbose_name=_("share value"), max_digits=14, decimal_places=4,
                                      default='0.0000', help_text=_("Simulated share value"))
    dividends = models.DecimalField(verbose_name=_("dividends"), max_digits=14, decimal_places=4,
                                    default='0.0000', help_text=_("Simulated dividends"))
    net_income = models.DecimalField(verbose_name=_("net income"), max_digits=14, decimal_places=4,
                                     default='0.0000', help_text=_("Simulated net income"))
    drift = models.DecimalField(verbose_name=_("drift"), max_digits=14, decimal_places=4,
                                default='0.0000', help_text=_("Drift"))
    sim_round = models.IntegerField(verbose_name=_("round"), default=0, help_text=_("Current round"))

    class Meta:
        verbose_name = _('share')
        verbose_name_plural = _('shares')
        ordering = ['-sim_round']

    def __str__(self):
        return "%s-R%s %s" % (self.company, self.sim_round, self.share_value)


class TickerTick(models.Model):
    """
    Stocks are shares of a company that are automatically generated during the simulation setup.
    """
    ticker = models.ForeignKey('Ticker', verbose_name=_("ticker"), related_name="ticks", help_text=_("Related ticker"))
    timestamp = models.DateTimeField(verbose_name=_("timestamp"), auto_now_add=True, help_text=_("Timestamp of the tick"))
    sim_round = models.IntegerField(verbose_name=_("round"), default=0, help_text=_("Current round"))
    sim_day = models.IntegerField(verbose_name=_("day"), default=0, help_text=_("Current day"))

    class Meta:
        verbose_name = _('tick')
        verbose_name_plural = _('ticks')
        ordering = ['-timestamp']

    def __str__(self):
        return "R%s/D%s" % (self.sim_round, self.sim_day)

    def save(self, *args, **kwargs):
        tick = {'ticker': self.ticker_id, 'timestamp': self.timestamp, 'sim_round': self.sim_round,
                'sim_day': self.sim_day}

