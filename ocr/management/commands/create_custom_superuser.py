from django.contrib.auth.management.commands import createsuperuser
from django.core.management import CommandError

class Command(createsuperuser.Command):
    help = 'Create a superuser with additional fields'

    def handle(self, *args, **options):
        username = options.get('username')
        email = options.get('email')
        full_name = input('Full Name: ')
        organization = input('Organization: ')

        if not full_name or not organization:
            raise CommandError('Full Name and Organization must be provided.')

        options['full_name'] = full_name
        options['organization'] = organization
        return super().handle(*args, **options)