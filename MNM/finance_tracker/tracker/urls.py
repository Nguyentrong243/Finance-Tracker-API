from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Public pages
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('support/', views.support, name='support'),
    path('news/', views.news, name='news'),
    
    # Auth
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard & Main features
    path('dashboard/', views.dashboard, name='dashboard'),
    path('transactions/', views.transactions_view, name='transactions'),
    path('add-transaction/', views.add_transaction, name='add_transaction'),
    path('delete-transaction/<int:pk>/', views.delete_transaction, name='delete_transaction'),
    path('reports/', views.reports, name='reports'),
    path('budgets/', views.budgets, name='budgets'),
    path('recurring-transactions/', views.recurring_transactions, name='recurring_transactions'),
    
    # User settings
    path('settings/', views.settings, name='settings'),
    path('profile/', views.profile, name='profile'),
    path('export/', views.export_transactions, name='export_transactions'),
    
    # API endpoints
    path('api/two-factor-status/', views.two_factor_status, name='two_factor_status'),
    path('api/login-2fa-code/', views.login_2fa_code, name='login_2fa_code'),
]