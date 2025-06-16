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