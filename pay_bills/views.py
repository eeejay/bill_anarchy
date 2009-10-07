from pay_bills.models import *
from django.http import *
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, get_object_or_404
from django import forms
from django.utils.safestring import mark_safe
from django.contrib.auth.decorators import login_required

from models import *


@login_required
def home(request):
    groups = request.user.groups.all()
    return render_to_response('home.html', {'groups': groups, 'current_user': request.user})

@login_required
def group_home(request, group):
    group = get_object_or_404(Group, name=group)
    if not group in request.user.groups.all():
        return HttpResponseRedirect('/login/?next=%s' % request.path)

    balance_table = [[u.username, '%.2f' % u.balance(group)] for u in group.user_set.all()]
    return render_to_response('group_home.html',
                              {'balance_table': balance_table,
                               'group': group, 'current_user': request.user})

@login_required
def create_group(request):
    return render_to_response('create_group.html',
                              {'current_user': request.user})

@login_required
def invite_user(request, group=''):
    if group:
        group = get_object_or_404(Group, name=group)
    return render_to_response('invite_user.html',
                              {'group': group,
                               'current_user': request.user})

@login_required
def leave_group(request, group):
    group = get_object_or_404(Group, name=group)
    return render_to_response('leave_group.html',
                              {'group': group, 'current_user': request.user})

def create_account(request):
    return render_to_response('create_account.html')

class TransferForm(forms.Form):
    comment = forms.CharField(required=False)
    amount = forms.FloatField()
    def __init__(self, current_user, group, *args, **kwargs):
        super(TransferForm, self).__init__(*args, **kwargs)
        self.fields['payer'] = forms.ModelChoiceField(queryset=group.user_set.all(),
                                                      initial=current_user.id)
        self.fields['payee'] = forms.ModelChoiceField(queryset=group.user_set.all())

@login_required
def add_transfer(request, group):
    group = get_object_or_404(Group, name=group)
    if not group in request.user.groups.all():
        return HttpResponseRedirect('/login/?next=%s' % request.path)

    if request.method == 'GET': # no form data is associated with page, yet
        form = TransferForm(request.user, group)
    elif request.method == 'POST': # If the form has been submitted...
        form = TransferForm(request.user, group, request.POST) # A form bound to the POST data
        if form.is_valid():
            # All validation rules pass, so create new data based on the
            # form contents 
            Transfer.objects.create(group=group, **form.cleaned_data)
            return HttpResponseRedirect(reverse('pay_bills.views.group_home', args=[group.name]))
    return render_to_response('add_transfer.html', {'form': form, 'group': group, 'current_user': request.user})

class BillForm(forms.Form):
    comment = forms.CharField(required=False)
    amount = forms.FloatField(widget=forms.TextInput(
            attrs={'onKeyUp': mark_safe("split_bill()")}))

    def __init__(self, current_user, group, *args, **kwargs):
        super(BillForm, self).__init__(*args, **kwargs)
        # now we add each question individually
        self.debtors = group.user_set.all()

        self.fields['payer'] = forms.ModelChoiceField(queryset=self.debtors,
                                                      initial=current_user.id)

        self.debtor_fields = []
        for d in self.debtors:
            self.fields['debtor_%d' % d.id] = forms.FloatField(label=d.username)
            self.debtor_fields.append(self['debtor_%d' % d.id])
        self.num_debtors = len(self.debtors)
        
    def clean(self):
        total_debts = sum([self.cleaned_data.get('debtor_%d'%d.id, 0.) for d in self.debtors])
        if self.cleaned_data.get('amount') != total_debts:
            raise forms.ValidationError('Sum of debts must equal total bill amount')

        return self.cleaned_data

@login_required
def add_bill(request, group):
    group = get_object_or_404(Group, name=group)
    if not group in request.user.groups.all():
        return HttpResponseRedirect('/login/?next=%s' % request.path)

    if request.method == 'GET': # no form data is associated with page, yet
        form = BillForm(request.user, group)
    elif request.method == 'POST': # If the form has been submitted...
        form = BillForm(request.user, group, request.POST) # A form bound to the POST data
        if form.is_valid():
            # All validation rules pass, so create new data based on the
            # form contents 

            b = Bill.objects.create(payer=form.cleaned_data['payer'],
                                    comment=form.cleaned_data['comment'],
                                    group=group)

            for u in group.user_set.all():
                a = form.cleaned_data['debtor_%d'%u.id]
                Debt.objects.create(debtor=u,
                                    bill=b,
                                    amount=a)
                
            return HttpResponseRedirect(reverse('pay_bills.views.group_home', args=[group.name]))
    return render_to_response('add_bill.html', {'form': form, 'group': group, 'current_user': request.user})

@login_required
def show_all_transactions(request, group, format='html'):
    if not format in ['html', 'xls']:
        raise Http404
    group = get_object_or_404(Group, name=group)
    if not group in request.user.groups.all():
        return HttpResponseRedirect('/login/?next=%s' % request.path)

    people = [u for u in group.user_set.all()]
    transfers = [t for t in Transfer.objects.filter(group=group)]
    bills = [b for b in Bill.objects.filter(group=group)]

    transactions = sorted(bills + transfers, key=lambda t: t.date)
    transaction_table = [t.to_rows(people) for t in transactions]

    balances = ['%.2f' % p.balance(group) for p in people]

    if format == 'html':
        return render_to_response('show_all_transactions.html',
                                  {'people': people,
                                   'transaction_table': transaction_table,
                                   'balances': balances,
                                   'group': group, 'current_user': request.user})
    else:
        import xlwt
        from StringIO import StringIO
        
        wbk = xlwt.Workbook()
        sheet = wbk.add_sheet('sheet 1')

        row = 0
        for col, val in enumerate(['Date:', 'Description:'] + [str(p) for p in people]):
            sheet.write(row, col, val)
        row += 1

        # formating dates
        # TODO: make the date a date in spreadsheet (also make the numbers a currency)
        excel_date_fmt = 'M/D/YY'
        style = xlwt.XFStyle()
        style.num_format_str = excel_date_fmt

        for t in transaction_table:
            for r in t:
                for col, cell in enumerate(r):
                    if col == 0:
                        sheet.write(row, col, cell, style)
                    elif col == 1:
                        sheet.write(row, col, cell)
                    else:
                        try:
                            cell = float(cell)
                        except ValueError:
                            pass
                        sheet.write(row, col, cell)
                row += 1

        f = StringIO()
        wbk.save(f)
        f.seek(0)
        content = f.read()
        
        return HttpResponse(content, mimetype='application/ms-excel')

@login_required
def show_transfers(request, group):
    group = get_object_or_404(Group, name=group)
    if not group in request.user.groups.all():
        return HttpResponseRedirect('/login/?next=%s' % request.path)

    transfers = Transfer.objects.filter(group=group)
    return render_to_response('show_transfers.html', {'transfers': transfers,
                                                      'group': group, 'current_user': request.user})
@login_required
def show_bills(request, group):
    group = get_object_or_404(Group, name=group)
    if not group in request.user.groups.all():
        return HttpResponseRedirect('/login/?next=%s' % request.path)

    people = [u for u in group.user_set.all()]
    bills = [b for b in Bill.objects.filter(group=group)]

    bill_table = [b.to_rows(people) for b in bills]
    return render_to_response('show_bills.html',
                              {'people': people, 'transaction_table': bill_table,
                               'group': group,
                               'current_user': request.user})

