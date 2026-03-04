from django.core.management.base import BaseCommand
from apps.security.models import APIKey
from django.utils import timezone


class Command(BaseCommand):
    help = 'Lista todas las API Keys registradas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--active-only',
            action='store_true',
            help='Mostrar solo API Keys activas'
        )

    def handle(self, *args, **options):
        queryset = APIKey.objects.all()
        
        if options['active_only']:
            queryset = queryset.filter(is_active=True)

        if not queryset.exists():
            self.stdout.write(self.style.WARNING('No hay API Keys registradas'))
            return

        self.stdout.write(self.style.SUCCESS('\n' + '='*100))
        self.stdout.write(self.style.SUCCESS('API Keys Registradas'))
        self.stdout.write(self.style.SUCCESS('='*100 + '\n'))

        header = f"{'ID':<5} {'Nombre':<25} {'Prefijo':<15} {'Activa':<8} {'Rate Limit':<12} {'Último Uso':<20} {'Expira':<20}"
        self.stdout.write(self.style.SUCCESS(header))
        self.stdout.write('-'*100)

        for api_key in queryset:
            status_icon = '✓' if api_key.is_active else '✗'
            status_color = self.style.SUCCESS if api_key.is_active else self.style.ERROR
            
            last_used = api_key.last_used_at.strftime('%Y-%m-%d %H:%M') if api_key.last_used_at else 'Nunca'
            expires = api_key.expires_at.strftime('%Y-%m-%d %H:%M') if api_key.expires_at else 'Sin expiración'
            
            # Verificar si está expirada
            if api_key.expires_at and api_key.expires_at < timezone.now():
                expires = f"{expires} (EXPIRADA)"
            
            row = f"{api_key.id:<5} {api_key.name:<25} {api_key.prefix:<15} {status_icon:<8} {api_key.rate_limit:<12} {last_used:<20} {expires:<20}"
            self.stdout.write(status_color(row))

        self.stdout.write('\n' + '='*100 + '\n')
        self.stdout.write(f"Total: {queryset.count()} API Keys\n")
