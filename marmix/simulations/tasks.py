# -*- coding: UTF-8 -*-
# tasks.py
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
from django.utils.translation import ugettext_lazy as _

# Third-party app imports
from async_messages import messages

# MarMix imports
from config.celery import app
from simulations.models import Simulation, Team, create_liquidity_manager
from tickers.models import TickerTick
from stocks.models import create_generic_stocks, process_opening_transactions


@app.task
def initialize_simulation(simulation):
    """
    The main task in charge of the initialization of the simulations
    """
    if simulation.simulation_type == Simulation.INTRO:
        messages.info(simulation.user, _("Initialization of introductory simulation running..."))
        # stocks creation
        stocks = create_generic_stocks(simulation)
        if stocks > 0:
            messages.info(simulation.user, _("%s stocks were created..." % stocks))
        else:
            messages.error(simulation.user, _("No stocks were created! Please try to re-run the initialization."))
        # liquidity traders creation
        liquidity_manager = create_liquidity_manager(simulation)
        if liquidity_manager:
            messages.info(simulation.user, _("%s was created..." % liquidity_manager.name))
        else:
            messages.error(simulation.user, _("No liquidity manager was created!"))
        # opening transactions
        openings = process_opening_transactions(simulation)
        # initialize ticker
    elif simulation.simulation_type == Simulation.ADVANCED:
        messages.info(simulation.user, _("Initialization of advanced simulation running..."))
    elif simulation.simulation_type == Simulation.LIVE or simulation.simulation_type == Simulation.INDEXED:
        messages.warning(simulation.user, _("Initialization of live or indexed simulations is not yet implemented! Sorry."))
    else:
        messages.error(simulation.user, _("Initialization of simulation failed!"))