# coding=utf8
from __future__ import unicode_literals

from django.db import models


class User(models.Model):
    # 如果没有models.AutoField，默认会创建一个id的自增列
    name = models.CharField(max_length=30)
    log_authority = models.CharField(max_length=1)
    new_data_authority = models.CharField(max_length=1)
    origin_data_authority = models.CharField(max_length=1)
