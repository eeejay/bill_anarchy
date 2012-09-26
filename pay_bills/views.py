from pay_bills.models import *
from django.http import *
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, get_object_or_404
from django.template.loader import render_to_string
from django import forms
from django.utils.safestring import mark_safe
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib import messages
from django.template import RequestContext

from models import *

@login_required
def home(request):
    groups = request.user.groups.all()
    return render_to_response('home.html', {'groups': groups, 'current_user': request.user},
                              context_instance=RequestContext(request))

@login_required
def group_home(request, group):
    group = get_object_or_404(Group, name=group)
    if not group in request.user.groups.all():
        return HttpResponseRedirect('/login/?next=%s' % request.path)

    balance_table = [[u.username, '%.2f' % u.balance(group)] for u in group.user_set.all()]
    return render_to_response('group_home.html',
                              {'balance_table': balance_table,
                               'group': group, 'current_user': request.user})


class GroupForm(forms.Form):
    name = forms.SlugField(max_length=20,
                           label = _('Name'),
                           help_text = _('a name consisting only of letters, numbers, underscores and hyphens.'))
    
    def clean_name(self):
        if Group.objects.filter(name__iexact=self.cleaned_data['name']).count() > 0:
            raise forms.ValidationError(_('A group already exists with that name.'))
        return self.cleaned_data['name']

@login_required
def create_group(request, form_class=GroupForm, template_name='create_group.html'):
    group_form = form_class(request.POST or None)
    
    if group_form.is_valid():
        group = Group.objects.create(name=group_form.cleaned_data['name'])
        group.user_set.add(request.user)
        #group.save()
        return HttpResponseRedirect(group.get_absolute_url())
    
    return render_to_response(template_name,
                              {'group_form': group_form,
                               'current_user': request.user},
                               context_instance=RequestContext(request))

class InviteForm(forms.Form):
    email_list = forms.CharField(
        widget=forms.Textarea(attrs={'rows':20, 'cols':80, 'wrap': 'off'}),
        label = _('e-mail Addresses'),
        help_text = _('a list of email addresses, one per line.'))
    
    def clean_email_list(self):
        return self.cleaned_data['email_list'].split('\n')

def random_code(len=12):
    import random
    import string
    
    return ''.join(random.choice(string.digits + string.letters) for i in xrange(len))

    
@login_required
def invite_users(request, group, form_class=InviteForm, template_name='invite_users.html'):
    from django.core.mail import send_mass_mail
    from django.contrib.sites.models import Site

    group = get_object_or_404(Group, name=group)
    if not group in request.user.groups.all():
        return HttpResponseRedirect('/login/?next=%s' % request.path)

    invite_form = form_class(request.POST or None)
    
    if invite_form.is_valid():
        data_list = []
        subject = _('You\'re invited to Bill Anarchy')
        message = _('Visit %s to join group %s.')
        current_site = Site.objects.get_current()
        domain = unicode(current_site.domain)

        for email in invite_form.cleaned_data['email_list']:
            email = email.strip()

            if not email:
                continue
            
            invite = SignupCode.objects.create(code=random_code(), email=email, group=group)

            message = render_to_string('invite_user.txt',
                                       {'invite': invite,
                                        'domain': domain,})
            data_list.append([subject,
                              message,
                              settings.DEFAULT_FROM_EMAIL,
                              [email]])

        send_mass_mail(data_list)
        messages.success(request, 'Sent %d invite(s)' % len(data_list))

        return HttpResponseRedirect(group.get_absolute_url())
    return render_to_response(template_name,
                              {'invite_form': invite_form,
                               'group': group,
                               'current_user': request.user},
                               context_instance=RequestContext(request))

@login_required
def redeem_invite(request, code):
    invite = get_object_or_404(SignupCode, code=code)
    group = invite.group
    group.user_set.add(request.user)
    invite.delete()
    return HttpResponseRedirect(group.get_absolute_url())

class RemoveForm(forms.Form):
    def __init__(self, current_user, group, *args, **kwargs):
        super(RemoveForm, self).__init__(*args, **kwargs)
        self.group = group
        self.fields['remove'] = forms.ModelChoiceField(queryset=group.user_set.all(),
                                                      initial=current_user.id)
    def clean(self):
        from numpy import abs
        if abs(self.cleaned_data['remove'].balance(self.group)) >= .01:
            raise forms.ValidationError(_('Balance must be zero to leave group.'))
        return self.cleaned_data
    
@login_required
def remove_users(request, group, form_class=RemoveForm):
    group = get_object_or_404(Group, name=group)
    if not group in request.user.groups.all():
        return HttpResponseRedirect('/login/?next=%s' % request.path)

    if request.method == "POST":
        form = form_class(request.user, group, request.POST)
        if form.is_valid():
            remove = form.cleaned_data['remove']
            group.user_set.remove(remove)
            if remove == request.user:
                return HttpResponseRedirect(reverse('pay_bills.views.home'))
            else:
                return HttpResponseRedirect(reverse('pay_bills.views.remove_users', args=[group.name]))

    else:
        form = form_class(request.user, group)
    return render_to_response('remove_users.html',
                              {'group': group, 'remove_form': form,
                               'current_user': request.user},
                               context_instance=RequestContext(request))


alnum_re = re.compile(r'^\w+$')

# from pinax.apps.account.forms
class SignupForm(forms.Form):
    
    username = forms.CharField(label=_("Username"), max_length=30, widget=forms.TextInput())
    password1 = forms.CharField(label=_("Password"), widget=forms.PasswordInput(render_value=False))
    password2 = forms.CharField(label=_("Password (again)"), widget=forms.PasswordInput(render_value=False))

    settings.ACCOUNT_REQUIRED_EMAIL = 0
    settings.ACCOUNT_EMAIL_VERIFICATION = 0
    
    if settings.ACCOUNT_REQUIRED_EMAIL or settings.ACCOUNT_EMAIL_VERIFICATION:
        email = forms.EmailField(
            label = _("Email"),
            required = True,
            widget = forms.TextInput()
        )
    else:
        email = forms.EmailField(
            label = _("Email (optional)"),
            required = False,
            widget = forms.TextInput()
        )
    
    confirmation_key = forms.CharField(max_length=40, required=False, widget=forms.HiddenInput())

    next = forms.CharField(max_length=40, required=False, widget=forms.HiddenInput())
    
    def clean_username(self):
        if not alnum_re.search(self.cleaned_data["username"]):
            raise forms.ValidationError(_("Usernames can only contain letters, numbers and underscores."))
        try:
            user = User.objects.get(username__iexact=self.cleaned_data["username"])
        except User.DoesNotExist:
            return self.cleaned_data["username"]
        raise forms.ValidationError(_("This username is already taken. Please choose another."))
    
    def clean(self):
        if "password1" in self.cleaned_data and "password2" in self.cleaned_data:
            if self.cleaned_data["password1"] != self.cleaned_data["password2"]:
                raise forms.ValidationError(_("You must type the same password each time."))
        return self.cleaned_data
    
    def save(self):
        username = self.cleaned_data["username"]
        email = self.cleaned_data["email"]
        password = self.cleaned_data["password1"]
        
        if self.cleaned_data["confirmation_key"]:
            # TODO: join existing group here
            from friends.models import JoinInvitation # @@@ temporary fix for issue 93
            try:
                join_invitation = JoinInvitation.objects.get(confirmation_key = self.cleaned_data["confirmation_key"])
                confirmed = True
            except JoinInvitation.DoesNotExist:
                confirmed = False
        else:
            confirmed = False
        
        # @@@ clean up some of the repetition below -- DRY!
        
        if confirmed:
            if email == join_invitation.contact.email:
                new_user = User.objects.create_user(username, email, password)
                join_invitation.accept(new_user) # should go before creation of EmailAddress below
                messages.info(request, ugettext(u"Your email address has already been verified"))
                # already verified so can just create
                EmailAddress(user=new_user, email=email, verified=True, primary=True).save()
            else:
                new_user = User.objects.create_user(username, "", password)
                join_invitation.accept(new_user) # should go before creation of EmailAddress below
                if email:
                    messages.info(request, ugettext(u"Confirmation email sent to %(email)s") % {'email': email})
                    EmailAddress.objects.add_email(new_user, email)
        else:
            new_user = User.objects.create_user(username, "", password)
            if email:
                messages.info(request, ugettext(u"Confirmation email sent to %(email)s") % {'email': email})
                EmailAddress.objects.add_email(new_user, email)
        
        if settings.ACCOUNT_EMAIL_VERIFICATION:
            new_user.is_active = False
            new_user.save()
                
        return username, password # required for authenticate()

# adapted from pinax.apps.account.views
def create_account(request):
    form_class = SignupForm
    success_url = reverse('pay_bills.views.home')

    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():

            username, password = form.save()

            user = authenticate(username=username, password=password)
            auth_login(request, user)
            messages.info(
                request, _(
                    "Successfully logged in as %(username)s.") % \
                    {"username": user.username})

            return HttpResponseRedirect(form.cleaned_data['next'] or success_url)
    else:
        form = form_class(initial={'next': request.GET.get('next', '')})

    return render_to_response('create_account.html',
                              dict(form=form),
                              context_instance=RequestContext(request))


import django.contrib.auth
def login(request):
    authentication_form = django.contrib.auth.forms.AuthenticationForm
    success_url = reverse('pay_bills.views.home')

    response = django.contrib.auth.views.login(
        request, template_name='login.html',
        extra_context={'modelbackend': 'django.contrib.auth.backends.ModelBackend' in settings.AUTHENTICATION_BACKENDS})
    # redeem valid invite code for group membership, if possible
    code = request.GET.get('code')
    form = authentication_form(data=request.POST)
    if code and form.is_valid():
        user = form.get_user()
        if user and user.is_authenticated():
            invite = get_object_or_404(SignupCode, code=code)
            success_url = reverse('pay_bills.views.group_home', args=[invite.group.name])
            invite.group.user_set.add(request.user)
            invite.delete()

            return HttpResponseRedirect(success_url)

    return response


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
    return render_to_response('add_transfer.html', {'form': form, 'group': group, 'current_user': request.user}, context_instance=RequestContext(request))

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
    return render_to_response('add_bill.html', {'form': form, 'group': group, 'current_user': request.user}, context_instance=RequestContext(request))

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
    return render_to_response('show_transfers.html',
                              {'transfers': transfers,
                               'group': group, 'current_user': request.user})


@login_required
def show_transfer(request, id):
    transfer = get_object_or_404(Transfer, id=id)
    group = transfer.group
    if not group in request.user.groups.all():
        return HttpResponseRedirect('/login/?next=%s' % request.path)

    return render_to_response('show_transfer.html',
                              {'transfer': transfer,
                               'transfer_fields': transfer.__dict__.items(),
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

@login_required
def show_bill(request, id):
    bill = get_object_or_404(Bill, id=id)
    group = bill.group

    if not group in request.user.groups.all():
        return HttpResponseRedirect('/login/?next=%s' % request.path)

    return render_to_response('show_bill.html',
                              {'bill': bill, 'bill_fields': bill.__dict__.items(),
                               'group': group, 'current_user': request.user})
