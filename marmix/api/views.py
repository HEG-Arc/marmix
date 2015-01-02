# -*- coding: UTF-8 -*-
# views.py
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
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse

# MarMix imports


@api_view(('GET',))
def api_root(request, format=None):
    return Response({
        'users': reverse('api-users-list', request=request, format=format),
        'simulations': reverse('api-simulations-list', request=request, format=format),
        'currencies': reverse('api-currencies-list', request=request, format=format),
    })
