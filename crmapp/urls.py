from django.urls import path
from . import views

urlpatterns = [
    path('', views.crm_login, name='login'),
    path('signup/', views.signup, name='signup'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),
    path('user_list/', views.user_list, name='user_list'),
    path('api/users/', views.user_list_api, name='user_list_api'),
    path('user/save/', views.save_user, name='save_user'),
    path('user/delete/<int:user_id>/', views.delete_user, name='delete_user'),
    path('user_roles/', views.user_roles , name="user_roles"),
    path("api/add-role/", views.add_role_api, name="add_role_api"),
    path("crm_creation/", views.crm_creation, name="crm_creation"),
    path('user/crm_save/', views.crm_save, name='crm_save'),
    path('delete/<int:pk>/', views.delete_field, name='delete_field'),
    path('fields/<int:pk>/edit/', views.get_field_data, name='get_field_data'),
    path('fields/<int:pk>/edit1/', views.edit_field, name='edit_field'),
    path('save_dynamic_form/', views.save_dynamic_form, name='save_dynamic_form'),
    path('lead_table/', views.lead_table, name='lead_table'),
    path('save_lead/', views.save_lead, name='save_lead'),
    path('api/lead/<int:lead_id>/', views.get_lead_data, name='get_lead_data'),
    path('api/update-lead/', views.update_lead, name='update_lead'),






]