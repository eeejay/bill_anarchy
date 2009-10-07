from bill_anarchy.pay_bills.models import *
from django.contrib import admin



class DebtInline(admin.TabularInline):
    model = Debt
    extra = 4

class BillAdmin(admin.ModelAdmin):
    fields = ['payer', 'comment']
    inlines = [DebtInline]
    
admin.site.register(Bill, BillAdmin)
admin.site.register(Transfer)
