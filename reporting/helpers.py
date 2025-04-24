from .models import LogReporting


def create_entry_log(user, reporting, action):
    log = LogReporting.objects.create(
        user=user,
        reporting=reporting,
        action=action,
    )
    log.save()
