from django.core.management.base import BaseCommand
from apps.security.models import APIKey


class Command(BaseCommand):
    help = 'Reactiva una API Key previamente revocada'

    def add_arguments(self, parser):
        parser.add_argument('api_key_id', type=int, help='ID de la API Key a reactivar')

    def handle(self, *args, **options):
        api_key_id = options['api_key_id']

        try:
            api_key = APIKey.objects.get(id=api_key_id)
        except APIKey.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'✗ API Key con ID {api_key_id} no encontrada'))
            return

        if api_key.is_active:
            self.stdout.write(self.style.WARNING(f'⚠ La API Key "{api_key.name}" ya está activa'))
            return

        api_key.is_active = True
        api_key.save()
        self.stdout.write(self.style.SUCCESS(f'✓ API Key "{api_key.name}" reactivada exitosamente'))
