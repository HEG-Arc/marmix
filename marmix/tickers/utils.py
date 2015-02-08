# -*- coding: UTF-8 -*-
# utils.py
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

# Third-party app imports
import numpy as np

# MarMix imports


def geometric_brownian(T, mu, sigma, s0, dt, random=None):
    """
    Geometric brownian distribution.

    :param T: Number of steps
    :param mu: The percentage drift
    :param sigma: The percentage volatility
    :param s0: The initial value
    :param dt: The time step (float).
    :return: An array of simulated values, where G < 0.09
    """
    s = np.linspace(1, int(T/dt), int(T/dt))
    while np.sum(s[int((T-1)/dt):int(T/dt)])/np.sum(s[int((T-2)/dt):int((T-1)/dt)])-1 > 0.09:
        n = int(T/dt)
        t = np.linspace(0, T, n)
        w = np.random.standard_normal(size=n)
        w = np.cumsum(w)*np.sqrt(dt)
        x = (mu-0.5*sigma**2)*t + sigma*w
        s = s0*np.exp(x)
    return s