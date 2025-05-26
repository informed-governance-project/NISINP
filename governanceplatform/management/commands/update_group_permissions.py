from django.core.management.base import BaseCommand

from governanceplatform.permissions import update_all_group_permissions


class Command(BaseCommand):
    help = "Updates group permissions as defined in the permissions.py file"

    def handle(self, *args, **kwargs):
        update_all_group_permissions()
        self.stdout.write(self.style.SUCCESS("Permissions updated successfully."))
