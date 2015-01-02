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
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse

# Third-party app imports

# MarMix imports
from .models import Team, Simulation


class TeamsSelectionForm(forms.Form):
    class MultipleTeamsField(forms.ModelMultipleChoiceField):
        def label_from_instance(self, obj):
            #url = reverse('card_detail', kwargs={'pk': obj.card_id}))
            label = '%s' % (obj.name, )
            return mark_safe(label)

    teams = MultipleTeamsField(queryset=[], widget=forms.CheckboxSelectMultiple())

    def __init__(self, *args, **kwargs):
        self.customer = kwargs.pop('customer', None)
        self.simulation = kwargs.pop('simulation', None)
        initial = kwargs.get('initial', {})
        initial.update({'teams': self.simulation.teams.all()})
        kwargs['initial'] = initial
        super(TeamsSelectionForm, self).__init__(*args, **kwargs)
        self.fields['teams'].queryset = Team.objects.all().filter(customer=self.customer)

