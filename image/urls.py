# -*- coding: UTF-8 -*-
from django.conf.urls.defaults import patterns

urlpatterns = patterns('image.views',
    (r'^image/(?P<path>.*)/((?P<parameters>.*))$', 'image'),
    (r'^image-crosshair', 'crosshair'),
)

