from django.test import TestCase
from django.test.client import Client
 
from django.core.urlresolvers import reverse
from django.core import mail
import urllib
import datetime

from models import *

def create_user(username, group):
    u = User.objects.create_user(username, '', username)
    u.groups.add(group)
    return u

def create_users_and_groups(test_case):
    # create groups
    test_case.rainbow = Group.objects.create(name='rainbow')
    test_case.dog_colors = Group.objects.create(name='dog-colors')

    # create people and add them to groups
    test_case.red = create_user('red', test_case.rainbow)
    test_case.blue = create_user('blue', test_case.rainbow)
    test_case.green = create_user('green', test_case.rainbow)
    test_case.yellow = create_user('yellow', test_case.rainbow)

    test_case.brown = create_user('brown', test_case.dog_colors)
    test_case.silver = create_user('silver', test_case.dog_colors)


class UserTestCase(TestCase):
    def setUp(self):
        create_users_and_groups(self)

    def test_login(self):
        """ Test login"""
        c = Client()
        url = reverse('pay_bills.views.login')
        response = c.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')
        
    def test_home(self):
        """ Test that index page loads"""
 
        c = Client()
        c.login(username='red', password='red')

        url = reverse('pay_bills.views.home')
        response = c.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')

    def test_create_account(self):
        """ Test that creating a new user works as expected"""
        c = Client()
        url = reverse('pay_bills.views.create_account')

        # test GET
        response = c.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'create_account.html')

        # test with good POST data
        response = c.post(url, dict(username='chartruse',
                                    password1='chartruse',
                                    password2='chartruse',
                                    email='',
                                    confirmation_key=''))
        self.assertRedirects(response, reverse('pay_bills.views.home'))
        user = User.objects.latest('id')
        self.assertEquals(user.username, 'chartruse')
        
        # test with password typo POST data
        response = c.post(url, dict(username='greenish-red',
                                    password1='greenish-red',
                                    password2='reddish-green',
                                    email='',
                                    confirmation_key=''))
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'create_account.html')

        # test with a username that is taken
        response = c.post(url, dict(username='chartruse',
                                    password1='pw1',
                                    password2='pw1',
                                    email='',
                                    confirmation_key=''))
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'create_account.html')

class GroupTestCase(TestCase):
    def setUp(self):
        create_users_and_groups(self)

    def test_group_home(self):
        """ Test that index page loads when group is specified"""
 
        c = Client()
        c.login(username='red', password='red')
        
        url = reverse('pay_bills.views.group_home', args=[self.rainbow.name])
        response = c.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'group_home.html')

    def test_create_group(self):
        """ Test that creating a new user works as expected"""
        c = Client()
        url = reverse('pay_bills.views.create_group')

        # test unauthed GET
        response = c.get(url)
        self.assertEquals(response.status_code, 302)

        # test authed GET
        c.login(username='red', password='red')
        response = c.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'create_group.html')

        # test good POST
        response = c.post(url, dict(name='koolaid-colors'))
        group = Group.objects.latest('id')
        self.assertEquals(group.name, 'koolaid-colors')
        self.assertEquals([u.id for u in group.user_set.all()], [self.red.id])
        self.assertRedirects(response, reverse('pay_bills.views.group_home', args=[group.name]))

        # test POST with no name does not create anything
        response = c.post(url, dict(name=''))
        group = Group.objects.latest('id')
        self.assertEquals(group.name, 'koolaid-colors')
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'create_group.html')

        # test POST with duplicate name does not create anything
        response = c.post(url, dict(name='dog-colors'))
        group = Group.objects.latest('id')
        self.assertEquals(group.name, 'koolaid-colors')
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'create_group.html')

    def test_invite_users(self):
        """ Test that user inviting controller works"""
 
        c = Client()
        c.login(username='red', password='red')
        
        url = reverse('pay_bills.views.invite_users', args=[self.rainbow])
        response = c.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'invite_users.html')

        response = c.post(url, dict(email_list='red@example.com\nbrownish-green@example.com'))
        self.assertEquals(len(mail.outbox), 2)
        self.assertRedirects(response, reverse('pay_bills.views.group_home', args=[self.rainbow]))


    def test_join_group_with_invite(self):
        """ Test that join group with invite code works"""
 
        c = Client()

        invite = SignupCode.objects.create(code='test_code',
                                           email='red@example.com',
                                           group=self.rainbow)

        url = reverse('pay_bills.views.redeem_invite', args=[invite.code])
        response = c.get(url)
        self.assertRedirects(response, reverse('pay_bills.views.create_account') + '?code=%s' % invite.code)

        url = reverse('pay_bills.views.create_account') + '?code=%s' % invite.code
        response = c.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'create_account.html')

        # make sure that code works
        response = c.post(url, dict(username='chartruse',
                                    password1='pw1',
                                    password2='pw1',
                                    email='',
                                    confirmation_key=''))

        self.assertEqual(User.objects.latest('id').username, 'chartruse')
        assert User.objects.latest('id') in invite.group.user_set.all()
        self.assertRedirects(response, reverse('pay_bills.views.group_home', args=[invite.group]))

        # make sure that code works only once
        response = c.post(url, dict(username='chartruse2',
                                    password1='pw1',
                                    password2='pw1',
                                    email='',
                                    confirmation_key=''))

        self.assertNotEqual(User.objects.latest('id').username, 'chartruse2')
        assert not 'chartruse2' in [u.username for u in invite.group.user_set.all()]

        # test invite code for an existing user
        invite = SignupCode.objects.create(code='test_code',
                                           email='silver@example.com',
                                           group=self.dog_colors)

        url = reverse('pay_bills.views.login') + '?code=%s' % invite.code
        response = c.post(url, dict(username='blue',
                                    password='blue'))

        assert self.blue in invite.group.user_set.all()
        self.assertRedirects(response, reverse('pay_bills.views.group_home', args=[invite.group]))

        # test invite code for an existing user only works once
        response = c.post(url, dict(username='red',
                                    password='red'))

        assert not self.red in invite.group.user_set.all()
        
        
class PayBillsTestCase(TestCase):
    def setUp(self):
        create_users_and_groups(self)

        # rainbow group activity
        self.bill = Bill.objects.create(payer=self.red, group=self.rainbow)
        Debt.objects.create(debtor=self.red, bill=self.bill, amount=25.)
        Debt.objects.create(debtor=self.blue, bill=self.bill, amount=25.)
        Debt.objects.create(debtor=self.green, bill=self.bill, amount=25.)
        Debt.objects.create(debtor=self.yellow, bill=self.bill, amount=25.)

        self.transfer = Transfer.objects.create(payer=self.yellow, payee=self.red, amount=25.,
                                                date=datetime.datetime.today(),
                                                group=self.rainbow)

        # dog-color group activity
        self.dog_bill = Bill.objects.create(payer=self.silver, group=self.dog_colors)
        Debt.objects.create(debtor=self.silver, bill=self.dog_bill, amount=25.)
        Debt.objects.create(debtor=self.brown, bill=self.dog_bill, amount=25.)

        self.dog_transfer = Transfer.objects.create(payer=self.brown, payee=self.silver,
                                                    amount=25.,
                                                    date=datetime.datetime.today(),
                                                    group=self.rainbow)

    # unit tests
    def test_user_balance(self):
        """ Test computation of user balance"""
        self.assertEqual(self.red.balance(self.rainbow), 50.)
 

    # functional tests
    def test_show_transfers(self):
        """ Test that transfers show"""
 
        c = Client()
        c.login(username='red', password='red')

        url = reverse('pay_bills.views.show_transfers', args=[self.rainbow.name])
        response = c.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'show_transfers.html')

    def test_show_transfer(self):
        """ Test that single transaction shows"""
 
        c = Client()
        c.login(username='red', password='red')
        
        url = reverse('pay_bills.views.show_transfer', args=[self.transfer.id])
        response = c.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'show_transfer.html')

    def test_show_bills(self):
        """ Test that bills show"""
 
        c = Client()
        c.login(username='red', password='red')
        
        url = reverse('pay_bills.views.show_bills', args=[self.rainbow.name])
        response = c.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'show_bills.html')

    def test_show_bill(self):
        """ Test that single bill shows"""
 
        c = Client()
        c.login(username='red', password='red')
        
        url = reverse('pay_bills.views.show_bill', args=[self.bill.id])
        response = c.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'show_bill.html')

    def test_show_all_transactions(self):
        """ Test that all transactions show"""
 
        c = Client()
        c.login(username='red', password='red')

        url = reverse('pay_bills.views.show_all_transactions', args=[self.rainbow.name])
        response = c.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'show_all_transactions.html')

    def test_export_all_transactions(self):
        """ Test that all transactions export"""

        c = Client()
        c.login(username='red', password='red')

        url = reverse('pay_bills.views.show_all_transactions', args=[self.rainbow.name, 'xls'])
        response = c.get(url)
        self.assertEquals(response.status_code, 200)
        
    def test_add_transfer(self):
        """ Test the add transfer interface"""
 
        c = Client()
        c.login(username='red', password='red')

        url = reverse('pay_bills.views.add_transfer', args=[self.rainbow.name])
        response = c.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'add_transfer.html')

        # post with no data
        response = c.post(url, {})
        self.assertTemplateUsed(response, 'add_transfer.html')
 
        # now do it right, and make sure that data and datasets are added
        response = c.post(url, {u'payer':self.red.id, 'payee': self.blue.id, 'amount': 10.,
                                'comment': ''})
        self.assertRedirects(response, reverse('pay_bills.views.group_home', args=[self.rainbow.name]))
        t1 = Transfer.objects.latest('id')

        # create another transfer and check that it has a later time
        import time
        time.sleep(.1)
        response = c.post(url, {u'payer':self.red.id, 'payee': self.blue.id, 'amount': 20.,
                                'comment': ''})
        t2 = Transfer.objects.latest('id')
        self.assertNotEqual(t1.date, t2.date)

    def test_add_bill(self):
        """ Test the add bill interface"""
 
        c = Client()
        c.login(username='red', password='red')

        url = reverse('pay_bills.views.add_bill', args=[self.rainbow.name])
        response = c.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'add_bill.html')

        # post with no data
        response = c.post(url, {})
        self.assertTemplateUsed(response, 'add_bill.html')

        # post with debts that don't add up
        response = c.post(url, {'payer':self.red.id, 'amount': 0., 'comment': '',
                                'debtor_%d'%self.red.id: 10,
                                'debtor_%d'%self.green.id: 5,
                                'debtor_%d'%self.blue.id: 5,
                                'debtor_%d'%self.yellow.id: 5,
                                })

        # since debts don't add up to amount, add_bill page should
        # display again with an error
        self.assertTemplateUsed(response, 'add_bill.html')
        
        
        # now do it right, and make sure the debts are added
        response = c.post(url, {'payer':self.red.id, 'amount': 15., 'comment': '',
                                'debtor_%d'%self.red.id: 7.5,
                                'debtor_%d'%self.green.id: 2.5,
                                'debtor_%d'%self.blue.id: 2.5,
                                'debtor_%d'%self.yellow.id: 2.5,
                                })

        self.assertRedirects(response, reverse('pay_bills.views.group_home', args=[self.rainbow.name]))
        
        bill = Bill.objects.latest('id')

        self.assertEquals(bill.payer, self.red)

        for d in bill.debt_set.all():
            if d.debtor == self.red:
                self.assertEquals(d.amount, 7.5) 
            else:
                self.assertEquals(d.amount, 2.5)
        
        
