from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/(.*)', admin.site.root),
                       
    (r'^accounts/logout/$', 'django.contrib.auth.views.logout',
     {'next_page': '/'}),
    (r'^accounts/forgot_password/$', 'django.contrib.auth.views.password_reset'),
    (r'^accounts/forgot_password/(?P<uidb36>\w+)/(?P<token>.+)$', 'django.contrib.auth.views.password_reset_confirm'),
    (r'^accounts/forgot_password/reset/$', 'django.contrib.auth.views.password_reset_complete'),
    (r'^accounts/forgot_password/reset/completed/$', 'django.contrib.auth.views.password_reset_done'),
    (r'^accounts/set_password/$', 'django.contrib.auth.views.password_change'),
    (r'^accounts/password_set$', 'django.contrib.auth.views.password_change_done'),
                       
    (r'^public/$', 'django.views.static.serve',
        {'document_root': 'public',
         'path': 'index.html'}),
    (r'^public/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': 'public'}),

    (r'^', include('bill_anarchy.pay_bills.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
)
