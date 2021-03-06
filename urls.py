from django.conf.urls.defaults import *
import os

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

public_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), 'public'))

urlpatterns = patterns(
    '',
    (r'^admin/', include(admin.site.urls)),

    (r'^browserid/', include('django_browserid.urls')),

    (r'^accounts/logout/$', 'django.contrib.auth.views.logout',
     {'next_page': '/'}),
    (r'^accounts/forgot_password/$', 'django.contrib.auth.views.password_reset',
     {'template_name': 'forgot_password.html'}),
    (r'^accounts/forgot_password/reset/$', 'django.contrib.auth.views.password_reset_done',
     {'template_name': 'password_reset_sent.html'}),
    (r'^accounts/forgot_password/(?P<uidb36>\w+)/(?P<token>.+)$',
     'django.contrib.auth.views.password_reset_confirm',
     {'template_name': 'password_reset_confirm.html', 'post_reset_redirect': '/'}),
    
    (r'^accounts/set_password/$', 'django.contrib.auth.views.password_change',
     {'template_name': 'password_change_form.html', 'post_change_redirect': '/'}),
                       
    (r'^public/$', 'django.views.static.serve',
        {'document_root': public_dir,
         'path': 'index.html'}),
    (r'^public/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': public_dir}),

    (r'^', include('bill_anarchy.pay_bills.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
)
