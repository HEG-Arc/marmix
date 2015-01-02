# -*- coding: UTF-8 -*-
# forms.py
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
from django import forms
from django.db import IntegrityError
from django.shortcuts import redirect
from django.contrib import messages

# Third-party app imports

# MarMix imports
from simulation.models import Team


class TeamCreateForm(forms.Form):
    qty = forms.IntegerField()
    suffix = forms.CharField()
    start_index = forms.IntegerField()

    def create_teams(self, customer, request):
        for i in range(self.cleaned_data['start_index'], self.cleaned_data['start_index'] + self.cleaned_data['qty']):
            try:
                team = Team(name='%s%s' % (self.cleaned_data['suffix'], i), customer=customer)
                team.save()
            except IntegrityError as e:
                messages.error(request, 'A team that you tried to create already exists in you organization.<br><u>Error message</u><br><i>%s</i>' % e.__cause__)
                #return redirect('customers-detail-view', pk=customer.id)
                return False
        return True


