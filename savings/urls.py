from django.urls import path
from . import views
app_name = 'savings'


urlpatterns = [
    path('plans/', views.SavingsPlansListView.as_view(), name='plans_list'),
    path('plans/<int:pk>/', views.SavingsPlanDetailView.as_view(), name='plan_details'),
    path('plans/create/', views.CreateSavingsPlanView.as_view(), name='create_plan'),
    path('plans/<int:pk>/deposit/', views.CreateDepositView.as_view(), name='create_deposit'),
    path('plans/<int:pk>/withdrawal/', views.CreateWithdrawalView.as_view(), name='create_withdrawal'),
    path('plan/<int:pk>/paystack/initialize/', views.PaystackDepositView.as_view(), name='paystack_initialize'),
    path('paystack/callback/', views.PaystackCallbackView.as_view(), name='paystack_callback'),
    # path('transactions/', views.UserTransactionListView.as_view(), name='user_transactions'),
    # path('transactions/filter/', views.TransactionListView.as_view(), name='transaction_filter'),
    path('transactions/<int:pk>/', views.TransactionDetailView.as_view(), name='transaction_detail'),
    path('transactions/<int:pk>/receipt/', views.DownloadTransactionReceiptView.as_view(), name='download_transaction_receipt'),

    # Admin Transaction URLs
    path('admin/transactions/', views.AdminTransactionListView.as_view(), name='admin_transaction_list'),
    path('admin/transactions/<int:pk>/', views.AdminTransactionDetailView.as_view(), name='admin_transaction_detail'),
    path('admin/transactions/<int:pk>/update/', views.AdminTransactionUpdateView.as_view(), name='admin_transaction_update'),
]

