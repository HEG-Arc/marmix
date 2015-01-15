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
from django.utils import timezone
# Core Django imports
from django.db import models
from django.utils.translation import ugettext_lazy as _

# Third-party app imports
from django_extensions.db.models import TimeStampedModel

# MarMix imports
from simulation.models import Simulation


class Ticker(TimeStampedModel):
    simulation = models.OneToOneField(Simulation, verbose_name=_("simulation"), primary_key=True, help_text=_("Related simulation"))
    nb_companies = models.IntegerField(verbose_name=_("number of companies"), null=True, blank=True, help_text=_("Number of real/simulated companies"))
    initial_value = models.IntegerField(verbose_name=_("initial value of companies"), default="100", help_text=_("Initial value of the companies (discounted cash flow). The exact value is randomized."))
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
        try:
            last_tick = self.ticks.all()[0]
        except IndexError:
            last_tick = None
        return last_tick
    last_tick = property(_last_tick)

    def __str__(self):
        return self.simulation.__str__()


class TickerStock(TimeStampedModel):
    """
    Stocks are shares of a company that are automatically generated during the simulation setup.
    """
    ticker = models.ForeignKey('Ticker', verbose_name=_("ticker"), related_name="stocks", help_text=_("Related ticker"))
    symbol = models.CharField(verbose_name=_("symbol"), max_length=4, help_text=_("Symbol of the stock (4 chars)"))
    name = models.CharField(verbose_name=_("name"), max_length=100, help_text=_("Full name of the stock"))
    description = models.TextField(verbose_name=_("description"), blank=True, help_text=_("Description of the stock (HTML)"))
    quantity = models.IntegerField(verbose_name=_("quantity"), default=1, help_text=_("Total quantity of stocks in circulation"))
    #next_price = models.DecimalField(verbose_name=_("next stock price"), max_digits=14, decimal_places=4,
    #                                 default='0.0000', help_text=_("Next stock price"))
    #drift = models.IntegerField(verbose_name=_("next stock price"),
    #                            default='0.0000', help_text=_("Next stock price"))

    class Meta:
        verbose_name = _('stock')
        verbose_name_plural = _('stocks')
        ordering = ['symbol']

    def _last_quote(self):
        try:
            last_quote = self.quotes.all()[0]
        except IndexError:
            last_quote = None
        return last_quote
    last_quote = property(_last_quote)

    def __str__(self):
        return self.symbol


class TickerQuote(models.Model):
    """
    Quotes are the price of a given stock at a certain time.
    """
    stock = models.ForeignKey('TickerStock', verbose_name=_("stock"), related_name="quotes", help_text=_("Related stock"))
    price = models.DecimalField(verbose_name=_("stock price"), max_digits=14, decimal_places=4,
                                          default='0.0000', help_text=_("Current stock price"))
    timestamp = models.DateTimeField(verbose_name=_("timestamp"), auto_now_add=True, help_text=_("Timestamp of the quote"))

    class Meta:
        verbose_name = _('quote')
        verbose_name_plural = _('quotes')
        ordering = ['-timestamp']

    def __str__(self):
        return "%s - %s (%s)" % (self.stock, self.price, self.timestamp)


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