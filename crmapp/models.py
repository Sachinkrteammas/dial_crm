from sys import modules

from django.db import models
from django.contrib.auth.models import User

class Customer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    company = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name



class UserList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    full_name = models.CharField(max_length=100)
    email_id = models.EmailField(max_length=100, unique=True)
    password = models.CharField(max_length=100)
    contact_no = models.CharField(max_length=25)
    company = models.CharField(max_length=100)
    user_role = models.CharField(max_length=100)
    is_deactivated = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='userlist_created_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='userlist_updated_by')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name

    class Meta:
        db_table = 'user_list'


class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='roles')
    username = models.CharField(max_length=100)
    all_access = models.BooleanField(default=False)
    user_read = models.BooleanField(default=False)
    user_write = models.BooleanField(default=False)
    user_create = models.BooleanField(default=False)
    crm_read = models.BooleanField(default=False)
    crm_write = models.BooleanField(default=False)
    crm_create = models.BooleanField(default=False)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_roles')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_roles')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username  # or str(self.user)

    class Meta:
        db_table = 'user_role'



class FieldMaster(models.Model):
    FieldName = models.CharField(max_length=200, null=True, blank=True)
    FieldType = models.CharField(max_length=200, null=True, blank=True)
    FieldValidation = models.CharField(max_length=100, null=True, blank=True)
    RequiredCheck = models.CharField(max_length=100, null=True, blank=True)
    Priority = models.IntegerField(null=True, blank=True)
    fieldNumber = models.IntegerField(null=True, blank=True)
    ClientId = models.IntegerField(null=True, blank=True)
    CreateDate = models.DateTimeField(null=True, blank=True)
    FieldStatus = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.FieldName if self.FieldName else f"FieldMaster {self.id}"

    class Meta:
        db_table = 'field_master'


class FieldMasterValue(models.Model):
    FieldId = models.ForeignKey(FieldMaster, on_delete=models.CASCADE, null=True, blank=True,related_name='field_values')
    FieldValueName = models.CharField(max_length=300, null=True, blank=True)
    ClientId = models.CharField(max_length=20, null=True, blank=True)
    FieldStatus = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.FieldValueName if self.FieldValueName else f"FieldValue {self.id}"

    class Meta:
        db_table = 'field_master_value'


class MenuItem(models.Model):
    name = models.CharField(max_length=100)
    url_name = models.CharField(max_length=100, blank=True, null=True)
    icon_class = models.CharField(max_length=100, blank=True, null=True)
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='children'
    )
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'menu_item'
        ordering = ['order']

    def __str__(self):
        return self.name



class DynamicFormData(models.Model):
    data = models.JSONField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='dynamic_forms_created'
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='dynamic_forms_updated'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dynamic_form_data'
        ordering = ['-submitted_at']

    def __str__(self):
        return f"Form #{self.id} by {self.created_by}"



class LeadTable(models.Model):
    customer_name = models.CharField(max_length=100, blank=True, null=True)
    customer_type = models.CharField(max_length=50, blank=True, null=True)
    calling_number = models.CharField(max_length=15, blank=True, null=True)
    enquiry_type = models.CharField(max_length=100, blank=True, null=True)
    enquiry_source = models.CharField(max_length=100, blank=True, null=True)
    sub_enquiry_source = models.CharField(max_length=100, blank=True, null=True)

    lead_date = models.DateField(blank=True, null=True)
    call_date = models.DateField(blank=True, null=True)

    call_type = models.CharField(max_length=50, blank=True, null=True)
    calling_status = models.CharField(max_length=100, blank=True, null=True)
    interested_status = models.CharField(max_length=100, blank=True, null=True)
    sub_calling_status = models.CharField(max_length=100, blank=True, null=True)
    sub_sub_calling_status = models.CharField(max_length=100, blank=True, null=True)

    select_bus = models.CharField(max_length=100, blank=True, null=True)
    buyer_type = models.CharField(max_length=50, blank=True, null=True)
    lead_status = models.CharField(max_length=100, blank=True, null=True)
    construction_level = models.CharField(max_length=100, blank=True, null=True)

    name = models.CharField(max_length=100, blank=True, null=True)
    alternative_number = models.CharField(max_length=15, blank=True, null=True)
    email_id = models.EmailField(blank=True, null=True)

    address = models.TextField(blank=True, null=True)
    landmark = models.CharField(max_length=100, blank=True, null=True)

    brand = models.CharField(max_length=100, blank=True, null=True)
    product = models.CharField(max_length=100, blank=True, null=True)
    sub_product = models.CharField(max_length=100, blank=True, null=True)

    state = models.CharField(max_length=50, blank=True, null=True)
    district = models.CharField(max_length=50, blank=True, null=True)
    zone = models.CharField(max_length=50, blank=True, null=True)
    pin_code = models.CharField(max_length=10, blank=True, null=True)

    agent_name = models.CharField(max_length=100, blank=True, null=True)
    order_qty = models.PositiveIntegerField(blank=True, null=True)
    order_description = models.TextField(blank=True, null=True)
    order_value = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    customer_type_select = models.CharField(max_length=100, blank=True, null=True)

    registration_status = models.CharField(max_length=50, blank=True, null=True)
    remark = models.TextField(blank=True, null=True)

    seller_email_id = models.EmailField(blank=True, null=True)
    seller_phone_no = models.CharField(max_length=15, blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_leads')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_leads')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.customer_name or f"Lead #{self.id}"

    class Meta:
        db_table = 'lead_table'


class ZoneTable(models.Model):
    zone = models.CharField(max_length=100, blank=True, null=True)
    state_ut = models.CharField(max_length=100, blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_zone')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_zone')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'zone_table'


class BrandTable(models.Model):
    brand = models.CharField(max_length=100, blank=True, null=True)
    product_types = models.CharField(max_length=100, blank=True, null=True)
    sub_product_types = models.CharField(max_length=100, blank=True, null=True)
    escalation_matrix = models.CharField(max_length=100, blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_brand')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_brand')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'brand_table'


class SalesInfoTable(models.Model):
    lead_table = models.ForeignKey(LeadTable, on_delete=models.CASCADE, null=True, blank=True, related_name='lead_table')
    sale_mt = models.CharField(max_length=100, blank=True, null=True)
    sale_inr = models.CharField(max_length=100, blank=True, null=True)
    sale_team_remarks = models.TextField(blank=True, null=True)
    lead_status = models.CharField(max_length=100, blank=True, null=True)
    cc_final_remarks_reformat = models.TextField(blank=True, null=True)
    lead_category = models.CharField(max_length=100, blank=True, null=True)
    product = models.CharField(max_length=100, blank=True, null=True)
    product_value = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=100, blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_sales_info')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_sales_info')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sales_info_table'


