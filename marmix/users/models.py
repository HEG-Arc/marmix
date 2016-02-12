# -*- coding: utf-8 -*-
# Import the AbstractUser model
from django.contrib.auth.models import AbstractUser
from django.db import models
from jsonfield import JSONField


#from simulations.models import Simulation


class User(AbstractUser):

    dashboard = JSONField(null=True, blank=True)
    #ame = models.CharField(verbose_name="name", max_length=50)

    def _is_poweruser(self):
        if self.organizations.all().count() > 0 or self.is_staff:
        #if self.is_staff:
            return True
        return False
    is_poweruser = property(_is_poweruser)

    def _get_team(self):
        from simulations.models import Simulation, Team
        return Team.objects.filter(simulations__state__gte=Simulation.READY, simulations__state__lte=Simulation.FINISHED).filter(users__username=self.username).first()
    get_team = property(_get_team)

    def __unicode__(self):
        return self.username
