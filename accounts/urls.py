from django.urls import path
from . import views



urlpatterns = [
    path('', views.UserLoginView, name='login'),
    path('admin-login/', views.AdminLoginView, name='admin_login'),
    path('registerAdmin/', views.registerAdmin, name='registerAdmin'),
    path('registerMember/', views.registerMember, name='registerMember'),
    path('logout/', views.LogoutView, name='logout'),
    path('myAccount/', views.myAccount, name='myAccount'),
    path('adminDashboard/', views.adminDashboard, name='adminDashboard'),
    path('memberDashboard/', views.memberDashboard, name='memberDashboard'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    path('forgot_password/', views.forgot_password, name='forgot_password'),
    path('reset_password_validate/<uidb64>/<token>/', views.reset_password_validate, name='reset_password_validate'),
    path('reset_password/', views.reset_password, name='reset_password'),
    path('admin-profile/', views.admin_profile, name='admin_profile'),
    path('member-profile/', views.member_profile, name='member_profile'),
]
