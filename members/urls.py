from django.urls import path
from . import views
from accounts import views as AccountViews

app_name = 'members'

urlpatterns = [
    # Member Dashboard and Profile
    path('dashboard', AccountViews.memberDashboard, name='memberDashboard'),
    path('admin-dashboard', AccountViews.adminDashboard, name='adminDashboard'),
    # path('profile/', views.profile, name='profile'),

    path('profile/', views.MemberProfileView.as_view(), name='profile'),
    # Member Application Flow
    path('apply/', views.apply_membership, name='apply_membership'),
    path('application/status/', views.application_status, name='application_status'),

    path('payment/initiate/', views.PaystackMembershipPaymentView.as_view(), name='payment_initiate'),
    path('payment/callback/', views.PaystackCallbackView.as_view(), name='payment_callback'),

    # Admin Member Routes
    path('admin/members/', views.AdminMemberListView.as_view(), name='admin_member_list'),
    path('admin/members/<int:pk>/', views.AdminMemberDetailView.as_view(), name='admin_member_detail'),
    path('admin/members/<int:pk>/update/', views.AdminMemberUpdateView.as_view(), name='admin_member_update'),
    path('admin/members/<int:pk>/delete/', views.AdminMemberDeleteView.as_view(), name='admin_member_delete'),

    # Admin Application Routes
    path('admin/applications/', views.AdminMembershipApplicationListView.as_view(), name='admin_application_list'),
    path('admin/applications/<int:pk>/', views.AdminMembershipApplicationDetailView.as_view(), name='admin_application_detail'),
    path('admin/applications/<int:pk>/update/', views.AdminMembershipApplicationUpdateView.as_view(), name='admin_application_update'),
    path('admin/applications/<int:pk>/delete/', views.AdminMembershipApplicationDeleteView.as_view(), name='admin_application_delete'),
]
