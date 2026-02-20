import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class RefreshToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    replaced_by = models.OneToOneField(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='replaced_token'
    )

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def is_active(self):
        return self.revoked_at is None and not self.is_expired()

    def revoke(self, replaced_by=None):
        self.revoked_at = timezone.now()
        if replaced_by:
            self.replaced_by = replaced_by
        self.save(update_fields=['revoked_at', 'replaced_by'])

    @staticmethod
    def generate():
        return uuid.uuid4().hex
    
    class Meta:
        db_table = "refresh_tokens"
        # app_label = "authentication"
        unique_together = ("user", "token")