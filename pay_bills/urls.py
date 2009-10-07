from django.conf.urls.defaults import *
import pay_bills.views

urlpatterns = patterns('pay_bills.views',
    (r'create_group/', 'create_group'),
    (r'(\w+)/invite_user/', 'invite_user'),
    (r'invite_user/', 'invite_user'),
    (r'accounts/create_account/', 'create_account'),
    (r'(\w+)/leave/', 'leave_group'),
    (r'(\w+)/add/transfer', 'add_transfer'),
    (r'(\w+)/add/bill', 'add_bill'),
    (r'(\w+)/view/all', 'show_all_transactions'),
    (r'(\w+)/export/\w+\.(\w+)', 'show_all_transactions'),
    (r'(\w+)/view/bills', 'show_bills'),
    (r'(\w+)/view/transfers', 'show_transfers'),
    (r'(\w+)/', 'group_home'),
    (r'', 'home'),
)
