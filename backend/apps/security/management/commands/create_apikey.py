from django.core.management.base import BaseCommand
from apps.security.models import APIKey
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = 'Crea una nueva API Key para una aplicación externa'

    def add_arguments(self, parser):
        parser.add_argument('name', type=str, help='Nombre de la aplicación')
        parser.add_argument('--description', type=str, default='', help='Descripción de la aplicación')
        parser.add_argument('--email', type=str, default='', help='Email de contacto')
        parser.add_argument('--rate-limit', type=int, default=1000, help='Requests por hora (default: 1000)')
        parser.add_argument('--allowed-ips', type=str, default='', help='IPs permitidas separadas por coma')
        parser.add_argument('--expires-days', type=int, help='Días hasta la expiración')

    def handle(self, *args, **options):
        name = options['name']
        description = options['description']
        email = options['email']
        rate_limit = options['rate_limit']
        allowed_ips = options['allowed_ips']
        expires_days = options['expires_days']

        # Generar la API Key
        key, prefix, key_hash = APIKey.generate_key()

        # Calcular fecha de expiración si se especificó
        expires_at = None
        if expires_days:
            expires_at = timezone.now() + timedelta(days=expires_days)

        # Crear el registro
        api_key = APIKey.objects.create(
            name=name,
            key_hash=key_hash,
            prefix=prefix,
            description=description,
            contact_email=email,
            rate_limit=rate_limit,
            allowed_ips=allowed_ips,
            expires_at=expires_at,
            is_active=True
        )

        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('✓ API Key creada exitosamente'))
        self.stdout.write(self.style.SUCCESS('='*70 + '\n'))
        
        self.stdout.write(f"Nombre:       {api_key.name}")
        self.stdout.write(f"ID:           {api_key.id}")
        self.stdout.write(f"Rate Limit:   {api_key.rate_limit} requests/hora")
        
        if api_key.allowed_ips:
            self.stdout.write(f"IPs Permitidas: {api_key.allowed_ips}")
        
        if api_key.expires_at:
            self.stdout.write(f"Expira:       {api_key.expires_at.strftime('%Y-%m-%d %H:%M')}")
        
        self.stdout.write(self.style.WARNING('\n⚠ IMPORTANTE: Guarda esta API Key de forma segura.'))
        self.stdout.write(self.style.WARNING('No podrás verla de nuevo.\n'))
        
        self.stdout.write(self.style.SUCCESS('API Key:'))
        self.stdout.write(self.style.SUCCESS(f'{key}\n'))
        
        self.stdout.write('Uso en requests:')
        self.stdout.write('  Header: X-API-Key: ' + key)
        self.stdout.write('\n' + '='*70 + '\n')
