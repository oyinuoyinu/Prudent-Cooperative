from django.urls import path
from . import views

app_name = 'mono'

urlpatterns = [
    path('', views.MonoConnectView.as_view(), name='mono_connect'),
    path('auth/', views.MonoAuthView.as_view(), name='connect_callback'),
    # path('statement/', views.BankStatementView.as_view(), name='bank_statement'),
]