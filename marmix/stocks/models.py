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
from datetime import datetime
# Core Django imports
from django.db import models
from django.utils.translation import ugettext_lazy as _

# Third-party app imports
from django_extensions.db.models import TimeStampedModel

# MarMix imports


class Stock(TimeStampedModel):
    """
    Stocks are shares of a company that are automatically generated during the simulation setup.
    """
    symbol = models.CharField(verbose_name=_("symbol"), max_length=4, help_text=_("Symbol of the stock (4 chars)"))
    name = models.CharField(verbose_name=_("name"), max_length=100, help_text=_("Full name of the stock"))
    description = models.TextField(verbose_name=_("description"), blank=True, help_text=_("Description of the stock (HTML)"))
    quantity = models.IntegerField(verbose_name=_("quantity"), default=1, help_text=_("Total quantity of stocks in circulation"))

    class Meta:
        verbose_name = _('stock')
        verbose_name_plural = _('stocks')
        ordering = ['symbol']

    def __str__(self):
        return self.symbol


class Quote(models.Model):
    """
    Quotes are the price of a given stock at a certain time.
    """
    stock = models.ForeignKey('Stock', verbose_name=_("stock"), related_name="quotes", help_text=_("Related stock"))
    price = models.DecimalField(verbose_name=_("stock price"), max_digits=14, decimal_places=4,
                                          default='0.0000', help_text=_("Current stock price"))
    timestamp = models.DateTimeField(verbose_name=_("timestamp"), auto_now_add=True, default=datetime.now(), help_text=_("Timestamp of the quote"))

    class Meta:
        verbose_name = _('quote')
        verbose_name_plural = _('quotes')
        ordering = ['-timestamp']

    def __str__(self):
        return "%s - %s (%s)" % (self.stock, self.price, self.timestamp)