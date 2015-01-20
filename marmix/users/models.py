# -*- coding: utf-8 -*-
# Import the AbstractUser model
from django.contrib.auth.models import AbstractUser


from simulations.models import Simulation, Team


class User(AbstractUser):

    def _is_poweruser(self):
        if self.organizations.all().count() > 0 or self.is_staff:
        #if self.is_staff:
            return True
        return False
    is_poweruser = property(_is_poweruser)

    def _get_team(self):
        return Team.objects.filter(simulations__state__gte=Simulation.READY, simulations__state__lte=Simulation.FINISHED).filter(users__username=self.username).first()
    get_team = property(_get_team)

    def __unicode__(self):
        return self.username