from django.conf.urls.defaults import *
import pay_bills.views

urlpatterns = patterns(
    'pay_bills.views',

    (r'^accounts/create_account/$', 'create_account'),
    (r'^login/', 'login'),
    (r'^accounts/login/', 'login'),

    (r'create_group/', 'create_group'),
    (r'([-\w]+)/remove_users/', 'remove_users'),
    (r'([-\w]+)/invite_users/', 'invite_users'),
    (r'invitation/([-\w]+)', 'redeem_invite'),
    
    
    (r'([-\w]+)/add/transfer', 'add_transfer'),
    (r'([-\w]+)/add/bill', 'add_bill'),
    (r'([-\w]+)/view/all', 'show_all_transactions'),
                       
    (r'view/transfer/(\w+)', 'show_transfer'),
    (r'view/bill/(\w+)', 'show_bill'),
                       
    (r'([-\w]+)/export/\w+\.(\w+)', 'show_all_transactions'),
    (r'([-\w]+)/view/bills', 'show_bills'),
    (r'([-\w]+)/view/transfers', 'show_transfers'),
    (r'([-\w]+)/', 'group_home'),
    (r'', 'home'),
)
