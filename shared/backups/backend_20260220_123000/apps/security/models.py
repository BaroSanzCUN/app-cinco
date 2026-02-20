from django.db import models
from django.contrib.auth.models import User

class UserPermission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    menu_id = models.IntegerField()  # ID de config_menu
    can_read = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_insert = models.BooleanField(default=False)
    can_import = models.BooleanField(default=False)
    can_manual = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)

    class Meta:
        db_table = "api_user_permissions"
        unique_together = ("user", "menu_id")
