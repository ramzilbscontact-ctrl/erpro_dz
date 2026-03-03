"""
Django management command to create a user in MongoDB Atlas.

Usage (run on Render via Shell tab, or locally):
    python manage.py create_user --email admin@example.com --password secret123 --role admin
    python manage.py create_user --email user@example.com --password pass1234 --role sales --first-name Ali --last-name Bensalem
"""
from django.core.management.base import BaseCommand, CommandError
from apps.authentication.models import User, ROLE_CHOICES
from apps.authentication.serializers import hash_password


class Command(BaseCommand):
    help = 'Create a user in MongoDB with a bcrypt-hashed password'

    def add_arguments(self, parser):
        parser.add_argument('--email',      required=True,  help='User email address')
        parser.add_argument('--password',   required=True,  help='Plain-text password (will be bcrypt-hashed)')
        parser.add_argument('--role',       default='viewer', choices=ROLE_CHOICES, help='User role')
        parser.add_argument('--first-name', default='',     dest='first_name')
        parser.add_argument('--last-name',  default='',     dest='last_name')
        parser.add_argument('--inactive',   action='store_true', help='Create user as inactive')

    def handle(self, *args, **options):
        email = options['email'].lower().strip()

        if User.objects(email=email).first():
            raise CommandError(f'User with email "{email}" already exists.')

        hashed = hash_password(options['password'])
        user = User(
            email=email,
            password=hashed,
            role=options['role'],
            first_name=options['first_name'],
            last_name=options['last_name'],
            is_active=not options['inactive'],
        )
        user.save()

        self.stdout.write(self.style.SUCCESS(
            f'User created: {email} | role={options["role"]} | id={user.id}'
        ))
