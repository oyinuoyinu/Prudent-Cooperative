from django.db import models
from django.conf import settings

class MonoAccount(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    account_id = models.CharField(max_length=255, null=False, blank=False)  # Ensure account_id is required
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Mono Account"
        verbose_name_plural = "Mono Accounts"
        unique_together = ('user', 'account_id')  # Ensure unique combination

    def __str__(self):
        return f"Mono Account - {self.user.email}"

    def save(self, *args, **kwargs):
        if not self.account_id:
            raise ValueError("Account ID is required")

        # Ensure only one active account per user
        if self.is_active:
            MonoAccount.objects.filter(user=self.user).exclude(id=self.id).update(is_active=False)
        super().save(*args, **kwargs)

# class MonoAccount(models.Model):
#     user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     account_id = models.CharField(max_length=100, unique=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"Mono Account - {self.user.email}"

#     class Meta:
#         verbose_name = "Mono Account"
#         verbose_name_plural = "Mono Accounts"


class BankStatement(models.Model):
    PERIOD_CHOICES = [
        ('1month', 'Last Month'),
        ('3months', 'Last 3 Months'),
        ('6months', 'Last 6 Months'),
        ('12months', 'Last 12 Months')
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    mono_account = models.ForeignKey(MonoAccount, on_delete=models.CASCADE)
    generated_at = models.DateTimeField(auto_now_add=True)
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    statement_data = models.JSONField()  # Stores the full statement data
    average_balance = models.DecimalField(max_digits=12, decimal_places=2)
    total_credits = models.DecimalField(max_digits=12, decimal_places=2)
    total_debits = models.DecimalField(max_digits=12, decimal_places=2)
    analysis_complete = models.BooleanField(default=False)

    def __str__(self):
        return f"Bank Statement - {self.user.email} ({self.period})"