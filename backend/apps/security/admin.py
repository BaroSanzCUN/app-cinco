from django.contrib import admin
from apps.security.models import UserPermission, APIKey
from django.utils.html import format_html
from django.utils import timezone


@admin.register(UserPermission)
class UserPermissionAdmin(admin.ModelAdmin):
    list_display = ['user', 'menu_id', 'can_read', 'can_edit', 'can_insert', 'is_admin']
    list_filter = ['can_read', 'can_edit', 'can_insert', 'is_admin']
    search_fields = ['user__username', 'menu_id']


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'prefix_display', 'status_display', 
        'rate_limit', 'last_used_display', 'created_at'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'prefix', 'contact_email']
    readonly_fields = ['key_hash', 'prefix', 'created_at', 'updated_at', 'last_used_at']
    
    fieldsets = (
        ('Información General', {
            'fields': ('name', 'description', 'contact_email')
        }),
        ('API Key', {
            'fields': ('prefix', 'key_hash'),
            'description': 'La API Key completa solo se muestra al crearla. Aquí solo ves el prefijo y hash.'
        }),
        ('Estado y Límites', {
            'fields': ('is_active', 'rate_limit', 'expires_at')
        }),
        ('Seguridad', {
            'fields': ('allowed_ips',),
            'description': 'IPs permitidas separadas por coma. Dejar vacío para permitir todas.'
        }),
        ('Tracking', {
            'fields': ('created_at', 'updated_at', 'last_used_at'),
            'classes': ('collapse',)
        }),
    )

    def prefix_display(self, obj):
        return f"{obj.prefix}..."
    prefix_display.short_description = "Prefijo"

    def status_display(self, obj):
        if not obj.is_active:
            return format_html('<span style="color: red;">✗ Inactiva</span>')
        
        if obj.expires_at and obj.expires_at < timezone.now():
            return format_html('<span style="color: orange;">⚠ Expirada</span>')
        
        return format_html('<span style="color: green;">✓ Activa</span>')
    status_display.short_description = "Estado"

    def last_used_display(self, obj):
        if not obj.last_used_at:
            return "Nunca"
        
        delta = timezone.now() - obj.last_used_at
        if delta.days > 30:
            return format_html('<span style="color: orange;">{}</span>', obj.last_used_at.strftime('%Y-%m-%d'))
        return obj.last_used_at.strftime('%Y-%m-%d %H:%M')
    last_used_display.short_description = "Último Uso"

    def save_model(self, request, obj, form, change):
        """
        Al crear una nueva API Key desde el admin, generar la key
        y mostrar un mensaje con la key completa
        """
        if not change:  # Solo al crear
            key, prefix, key_hash = APIKey.generate_key()
            obj.prefix = prefix
            obj.key_hash = key_hash
            super().save_model(request, obj, form, change)
            
            # Agregar mensaje con la API Key generada
            self.message_user(
                request,
                format_html(
                    '<strong>⚠ IMPORTANTE: Guarda esta API Key, no podrás verla de nuevo:</strong><br/>'
                    '<code style="background: #f0f0f0; padding: 10px; display: block; margin: 10px 0;">{}</code>'
                    '<br/>Úsala en el header: <code>X-API-Key: {}</code>',
                    key, key
                )
            )
        else:
            super().save_model(request, obj, form, change)

