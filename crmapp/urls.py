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


]