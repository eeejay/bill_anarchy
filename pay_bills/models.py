from django.db.models import *
from django.contrib.auth.models import User, Group
from django.core.urlresolvers import reverse

import datetime


# monkey patch balance method into User model
def balance(user, group):
    """ A person's balance equals the amount they paid in all
    bill-payment transactions plus the amount they paid in all
    transfer transactions, minus the owed by them for all
    bill-payment transactions, minus the amount they received in
    all transfer transactions.

    In other words, balance(red) = 100 means the group owes red $100,
    balance(blue) = -25 means blue owes the group $25.
    """
    b = 0.

    for bill in Bill.objects.filter(payer=user, group=group):
        b += bill.total()

    for payTransfer in Transfer.objects.filter(payer=user, group=group):
        b += payTransfer.amount

    for payTransfer in Transfer.objects.filter(payee=user, group=group):
        b -= payTransfer.amount

    for d in Debt.objects.filter(debtor=user, bill__group=group):
        b -= d.amount

    return b
User.balance = balance


# monkey patch get_absolute_url into Group model
Group.get_absolute_url = lambda group: reverse('pay_bills.views.group_home', args=[group.name])

class Transfer(Model):
    payer = ForeignKey(User, related_name='transer_payer')
    payee = ForeignKey(User, related_name='transfer_payee')
    amount = FloatField()
    comment = TextField(blank=True)
    group = ForeignKey(Group)
    date = DateTimeField('transaction date', auto_now_add=True)
    is_void = BooleanField('is void?', default=False)

    def __unicode__(self):
        name = 'Transfer: %s paid %s $%.2f' % (self.payer, self.payee, self.amount)
        if self.comment:
            name += ' (%s)' % self.comment
        return name

    def get_absolute_url(self):
        return reverse('pay_bills.views.show_transfer', args=[self.id])

    def to_rows(self, people):
        """ Turn the transfer data into a row for a transaction table
        Parameters
        ----------
        people : list of User objects
          order of the user columns in the transaction table
        Results
        -------
          returns row data in the form [['date', 'description', change in p[0]'s balance, ...]]
        """
        row = [datetime.datetime.strftime(self.date, '%m/%d/%Y'),
              '<a href="%s">%s</a>' % (self.get_absolute_url(), str(self))]
        for p in people:
            if p == self.payer:
                row.append('%.2f' % self.amount)
            elif p == self.payee:
                row.append('%.2f' % -self.amount)
            else:
                row.append('')
        return [row]
    
class Bill(Model):
    participants = ManyToManyField(User, through='Debt')
    payer = ForeignKey(User, related_name='bill_payer')
    comment = TextField(blank=True)
    date = DateTimeField('transaction date', auto_now_add=True)
    group = ForeignKey(Group)
    is_void = BooleanField('is void?', default=False)
    
    def __unicode__(self):
        name = 'Bill: %s paid $%.2f' % (self.payer, self.total())
        if self.comment:
            name += ' (%s)' % self.comment
        return name

    def get_absolute_url(self):
        return reverse('pay_bills.views.show_bill', args=[self.id])

    def total(self):
        return sum([d.amount for d in Debt.objects.filter(bill=self)])

    def debt_for(self, person):
        """ Return the Debt object for a particular person
        Parameters
        ----------
        person : Person object

        Notes
        -----
        Caches the Debt objects in a dictionary
        """
        if not hasattr(self, 'debt_dict'):
            self.debt_dict = {}
            for d in self.debt_set.all():
                self.debt_dict[d.debtor] = d

        return self.debt_dict.get(person)
    
    def to_rows(self, people):
        """ Turn the bill data into a row for a transaction table
        Parameters
        ----------
        people : list of User objects
          order of the user columns in the transaction table

        Results
        -------
          returns data in two rows, in the form::
              ['date', 'description', change in p[0]'s balance, ...]
        """
        r1 = [datetime.datetime.strftime(self.date, '%m/%d/%Y'),
              '<a href="%s">%s</a>' % (self.get_absolute_url(), str(self))]
        for p in people:
            if self.debt_for(p):
                r1.append('%.2f' % -self.debt_for(p).amount)
            else:
                r1.append('')

        r2 = ['', '']
        for p in people:
            if p == self.payer:
                r2.append('%.2f' % self.total())
            else:
                r2.append('')

        return [r1, r2]
    
class Debt(Model):
    debtor = ForeignKey(User)
    bill = ForeignKey(Bill)
    amount = FloatField()
    
    def __unicode__(self):
        return 'Debt %d: %s owes $%.2f' % (self.id, self.debtor, self.amount)

