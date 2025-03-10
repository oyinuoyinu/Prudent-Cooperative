from django.urls import path
from . import views

app_name = 'loans'

urlpatterns = [
    # Loan Plan URLs
    path('plans/', views.LoanPlansListView.as_view(), name='plans_list'),
    path('plans/<int:pk>/', views.LoanPlanDetailView.as_view(), name='plan_detail'),

    # Loan URLs
    path('loans/<int:pk>/', views.LoanDetailView.as_view(), name='loan_detail'),
    path('loans/<int:pk>/repayment/', views.LoanRepaymentView.as_view(), name='loan_repayment'),
    #path('loans/<int:pk>/repayment/', views.LoanRepaymentCreateView.as_view(), name='loan_repayment'),

    # Application URLs
    path('applications/create/<int:plan_pk>/', views.LoanApplicationCreateView.as_view(), name='application_create'),
    path('applications/<int:pk>/', views.LoanApplicationDetailView.as_view(), name='application_detail'),
    path('applications/<int:application_pk>/guarantor/add/', views.GuarantorCreateView.as_view(), name='add_guarantor'),

    path('applications/<int:pk>/receipt/', views.DownloadReceiptView.as_view(), name='download_receipt'),

    path('loans/application/<int:pk>/pay/', views.PaystackOnlineLoanPaymentView.as_view(), name='application_payment'),
    path('loans/<int:pk>/pay/', views.PaystackLoanPaymentView.as_view(), name='loan_payment'),
    path('paystack/callback/', views.PaystackOnlineLoanCallbackView.as_view(), name='paystack_callback'),

    # Admin URLs
    path('admin/applications/', views.AdminLoanApplicationListView.as_view(), name='admin_loan_application_list'),
    path('admin/applications/<int:pk>/', views.AdminLoanApplicationDetailView.as_view(), name='admin_application_detail'),
    path('admin/loans/<int:pk>/update/', views.AdminLoanApplicationUpdateView.as_view(), name='admin_loan_update'),
    # path('admin/loans/<int:pk>/delete/', views.AdminLoanApplicationDeleteView.as_view(), name='admin_loan_application_delete'),


    path('admin/loans/', views.AdminLoanListView.as_view(), name='admin_loan_list'),
    path('admin/loans/<int:pk>/', views.AdminLoanDetailView.as_view(), name='admin_loan_detail'),

    path('admin/loans/transaction/', views.AdminLoanTransactionListView.as_view(), name='admin_loan_transaction_list'),
    path('admin/loans/<int:pk>/transaction/<int:transaction_pk>/', views.AdminLoanTransactionUpdateView.as_view(), name='admin_loan_transaction_update'),
]