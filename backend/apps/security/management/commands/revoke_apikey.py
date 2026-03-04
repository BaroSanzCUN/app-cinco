from django.core.management.base import BaseCommand
from apps.security.models import APIKey


class Command(BaseCommand):
    help = 'Revoca (desactiva) una API Key'

    def add_arguments(self, parser):
        parser.add_argument('api_key_id', type=int, help='ID de la API Key a revocar')
        parser.add_argument(
            '--permanent',
            action='store_true',
            help='Eliminar permanentemente en lugar de desactivar'
        )

    def handle(self, *args, **options):
        api_key_id = options['api_key_id']
        permanent = options['permanent']

        try:
            api_key = APIKey.objects.get(id=api_key_id)
        except APIKey.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'✗ API Key con ID {api_key_id} no encontrada'))
            return

        if permanent:
            confirm = input(f'¿Estás seguro de eliminar permanentemente la API Key "{api_key.name}"? (s/N): ')
            if confirm.lower() == 's':
                api_key.delete()
                self.stdout.write(self.style.SUCCESS(f'✓ API Key "{api_key.name}" eliminada permanentemente'))
            else:
                self.stdout.write(self.style.WARNING('Operación cancelada'))
        else:
            api_key.is_active = False
            api_key.save()
            self.stdout.write(self.style.SUCCESS(f'✓ API Key "{api_key.name}" revocada (desactivada)'))
            self.stdout.write('Puedes reactivarla con el comando: activate_apikey {}'.format(api_key_id))
