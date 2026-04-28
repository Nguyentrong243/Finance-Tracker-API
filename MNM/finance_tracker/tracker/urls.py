from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('login/2fa-status/', views.two_factor_status, name='login_2fa_status'),
    path('login/2fa-code/', views.login_2fa_code, name='login_2fa_code'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/profile/', views.profile, name='profile'),
    path('dashboard/reports/', views.reports, name='reports'),
    path('dashboard/transactions/', views.transactions_view, name='transactions'),
    path('dashboard/transactions/delete/<int:pk>/', views.delete_transaction, name='delete_transaction'),
    path('dashboard/transactions/export/', views.export_transactions, name='export_transactions'),
    path('dashboard/settings/', views.settings, name='settings'),
    path('add-transaction/', views.add_transaction, name='add_transaction'),
    path('about/', views.about, name='about'),
    path('support/', views.support, name='support'),
    path('news/', views.news, name='news'),
]