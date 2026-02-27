from django.urls import path
from . import views,sales_views,salesdiary
from .api_view import WebhookLeadsView,webhook

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
    path('delete-lead/<int:lead_id>/', views.delete_lead, name='delete_lead'),
    path('api/user-emails/', views.get_user_emails, name='get_user_emails'),
    path('api/user-contact/', views.get_contact_by_email, name='get_contact_by_email'),
    path('api/get-states/', views.get_states_by_zone, name='get_states_by_zone'),

    #API VIEW
    path('api/webhook-leads/', WebhookLeadsView.as_view(), name='webhook_leads_api'),
    path('api/webhook/', webhook, name='webhook'),
    #API VIEW END

    #Sales url
    path('sales/', sales_views.sales_user, name='sales_user'),
    path('sales_get_data/', sales_views.sales_get_data, name='sales_get_data'),

    path('sales_get_data/<int:uid>/', sales_views.sales_get_data, name='sales_get_data'),

    path('update_sales_info/', sales_views.update_sales_info, name='update_sales_info'),
    path('lead_detail/<int:lead_id>/', sales_views.lead_detail, name='lead_detail'),
    path('api/zone-info/', sales_views.get_zone_data, name='get_zone_data'),
    path('save_follow_up/<int:lead_id>/', sales_views.save_follow_up, name='save_follow_up'),


    path('api/make-call/', sales_views.make_call_api, name='make_call_api'),

    #Exports leads
    path('leads_export/',sales_views.leads_export,name="leads_export"),
    path('sales_export/',sales_views.sales_export,name="sales_export"),
    path('follow_up/',sales_views.follow_up,name="follow_up"),
    path('call_date/',sales_views.call_date,name="call_date"),


    path('main_leads_export/',sales_views.main_leads_export,name="main_leads_export"),
    path('updated_leads_export/',sales_views.updated_leads_export,name="updated_leads_export"),
    path('lead_close_status_export/',sales_views.lead_close_status_export,name="lead_close_status_export"),

    path('reallocate/',sales_views.reallocate,name="reallocate"),
    path('get-leads-by-user/<int:user_id>/', sales_views.get_leads_by_user, name='get_leads_by_user'),
    path('api/get-voc-options/',sales_views.get_voc_options_api, name='get_voc_options_api'),
    path('api/get-customer-voc-options/', sales_views.get_customer_voc_options_api, name='get_customer_voc_options_api'),
    path('api/lead-copy/<int:lead_id>/', sales_views.copy_lead, name='copy_lead'),

    #lead bulk upload data save
    path('bulk_upload/', sales_views.bulk_upload, name='bulk_upload'),
    path('api/upload-leads/', sales_views.upload_leads_excel, name='upload_leads_excel'),
    path('download-template/', sales_views.download_excel_template, name='download_excel_template'),
    path('call_back_lead/', sales_views.call_back_lead, name='call_back_lead'),
    path('follow_up_data/', sales_views.follow_up_data, name='follow_up_data'),
    path('not_connected_lead/', sales_views.not_connected_lead, name='not_connected_lead'),
    path('new_lead/', sales_views.new_lead, name='new_lead'),
    path('agent_lead/', sales_views.agent_lead, name='agent_lead'),

    ## whatsapp api call
    path("api/send-whatsapp/", sales_views.send_whatsapp_message, name="send_whatsapp"),


    path('api/upload-leads-update/', sales_views.upload_leads_update, name='upload_leads_update'),
    path('download-excel-template-update/', sales_views.download_excel_template_update, name='download_excel_template_update'),


    ############ salesdiary url ##############

    path("get-access-token/", salesdiary.get_access_token, name="get_access_token"),
    path("get-business-structure/", salesdiary.get_business_structure, name="get_business_structure"),
    path("get-lead-status/", salesdiary.get_lead_status, name="get_lead_status"),
    path("save_lead_status/", salesdiary.save_lead_status, name="save_lead_status"),


    ####### policy #########
    path("privacy_policy/", sales_views.privacy_policy, name="privacy_policy"),
    path("terms_of_service/", sales_views.terms_of_service, name="terms_of_service"),
    path("data_deletion/", sales_views.data_deletion, name="data_deletion"),

    ######## ales-diary-api ####
    path("sales-diary-api/", views.sales_diary_api, name="sales_diary_api"),
    path("url_request/", views.url_request, name="url_request"),

    path("admin_dashboard/", views.admin_dashboard, name="admin_dashboard"),


]