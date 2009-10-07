from django.test import TestCase
from django.test.client import Client
 
from django.core.urlresolvers import reverse
import urllib
import datetime

from models import *

class PayBillsTestCase(TestCase):
    def create_user(self, username, group):
        u = User.objects.create_user(username, '', username)
        u.groups.add(group)
        return u
    
    def setUp(self):
        # create groups
        self.rainbow = Group.objects.create(name='rainbow')
        self.dog_colors = Group.objects.create(name='dog-colors')

        # create people and add them to groups
        self.red = self.create_user('red', self.rainbow)
        self.blue = self.create_user('blue', self.rainbow)
        self.green = self.create_user('green', self.rainbow)
        self.yellow = self.create_user('yellow', self.rainbow)
        
        self.brown = self.create_user('brown', self.dog_colors)
        self.silver = self.create_user('silver', self.dog_colors)

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
    def test_home(self):
        """ Test that index page loads"""
 
        c = Client()
        c.login(username='red', password='red')

        url = reverse('pay_bills.views.home')
        response = c.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')

    def test_group_home(self):
        """ Test that index page loads when group is specified"""
 
        c = Client()
        c.login(username='red', password='red')
        
        url = reverse('pay_bills.views.group_home', args=[self.rainbow.name])
        response = c.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'group_home.html')
        
    def test_create_group(self):
        """ Test that group creation controller works"""
 
        c = Client()
        c.login(username='red', password='red')
        
        url = reverse('pay_bills.views.create_group')
        response = c.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'create_group.html')

        # TODO: add test for creating the group
        
    def test_invite_user(self):
        """ Test that user inviting controller works"""
 
        c = Client()
        c.login(username='red', password='red')
        
        url = reverse('pay_bills.views.invite_user')
        response = c.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'invite_user.html')

        # TODO: add test for creating the group

    def test_create_account(self):
        """ Test that user inviting controller works"""
 
        c = Client()
        
        url = reverse('pay_bills.views.create_account')
        response = c.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'create_account.html')

        # TODO: add test for creating the group
        
    def test_show_transfers(self):
        """ Test that transfers show"""
 
        c = Client()
        c.login(username='red', password='red')

        url = reverse('pay_bills.views.show_transfers', args=[self.rainbow.name])
        response = c.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'show_transfers.html')

    def test_show_bills(self):
        """ Test that bills show"""
 
        c = Client()
        c.login(username='red', password='red')
        
        url = reverse('pay_bills.views.show_bills', args=[self.rainbow.name])
        response = c.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'show_bills.html')

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
                                'date': datetime.date.today(), 'comment': ''})
        self.assertRedirects(response, reverse('pay_bills.views.group_home', args=[self.rainbow.name]))

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
        
        
