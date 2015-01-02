# -*- coding: utf-8 -*-
# Import the AbstractUser model
from django.contrib.auth.models import AbstractUser

# Import the basic Django ORM models library
from django.db import models

from django.utils.translation import ugettext_lazy as _


class User(AbstractUser):

    def _is_poweruser(self):
        if self.organizations.all().count() > 0 or self.is_staff:
        #if self.is_staff:
            return True
        return False
    is_poweruser = property(_is_poweruser)

    def __unicode__(self):
        return self.username