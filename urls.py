from django.conf.urls.defaults import *
from os.path import dirname, join

_dir = dirname(__file__)
# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('contact',
                       url(r'^$', 'views.index', name='index'),
                       url(r'^call/(?P<contact_id>\d+)$', 'views.call', name='call'),
                       url(r'^status/(?P<contact_id>\d+)$', 'views.status', name='status'),
                       url(r'^bridge/(?P<contact_id>\d+)$', 'views.bridge', name='bridge'),
                       url(r'^vmme/(?P<contact_id>\d+)$', 'views.vmme', name='vmme'),                        
                       url(r'^transcribe/(?P<contact_id>\d+)$', 'views.transcribe', name='transcribe'),
                       url(r'^goodbye/(?P<contact_id>\d+)$', 'views.goodbye', name='goodbye'),
                       url(r'^update/(?P<contact_id>\d+)$', 'views.update', name='update'), 
)

# Indeed don't do this on prod
urlpatterns.extend(patterns('',
                            (r'^tmedia/(?P<path>.*)$', 'django.views.static.serve',
                             {'document_root': join(_dir, 'media')})
                            )
                   )
