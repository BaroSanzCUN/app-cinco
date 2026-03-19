from django.db import models
from django.contrib.auth.models import User
import secrets
import hashlib

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


class APIKey(models.Model):
    """
    Modelo para gestionar API Keys de aplicaciones externas
    """
    name = models.CharField(max_length=255, help_text="Nombre de la aplicación externa")
    key_hash = models.CharField(max_length=128, unique=True, db_index=True)
    prefix = models.CharField(max_length=8, db_index=True, help_text="Prefijo visible de la key")
    is_active = models.BooleanField(default=True, help_text="Si la API Key está activa")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    # Restricciones y permisos
    allowed_ips = models.TextField(blank=True, help_text="IPs permitidas separadas por coma")
    rate_limit = models.IntegerField(default=1000, help_text="Requests por hora")
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Fecha de expiración")
    
    # Metadatos
    description = models.TextField(blank=True)
    contact_email = models.EmailField(blank=True)

    class Meta:
        db_table = "api_keys"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.prefix}...)"

    @classmethod
    def get_prefix_length(cls) -> int:
        """Retorna la longitud de prefijo configurada en el modelo."""
        field = cls._meta.get_field("prefix")
        return field.max_length or 8

    @staticmethod
    def generate_key():
        """
        Genera una nueva API Key en formato: cinco_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        Retorna: (key_completa, prefix, hash)
        """
        random_part = secrets.token_urlsafe(32)
        key = f"cinco_{random_part}"
        prefix = key[:APIKey.get_prefix_length()]
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return key, prefix, key_hash

    @staticmethod
    def hash_key(key: str) -> str:
        """Genera el hash de una API Key"""
        return hashlib.sha256(key.encode()).hexdigest()

    def verify_key(self, key: str) -> bool:
        """Verifica si una key coincide con el hash almacenado"""
        return self.key_hash == self.hash_key(key)
