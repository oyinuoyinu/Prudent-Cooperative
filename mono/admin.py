from django.contrib import admin
from .models import MonoAccount, BankStatement
# Register your models here.

admin.site.register(MonoAccount)
admin.site.register(BankStatement)