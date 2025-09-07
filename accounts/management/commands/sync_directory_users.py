import os
import sys
import fcntl
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from google.oauth2 import service_account
from googleapiclient.discovery import build

User = get_user_model()

SCOPES = ["https://www.googleapis.com/auth/admin.directory.user.readonly"]
DEFAULT_GROUP_NAME = os.environ.get("DEFAULT_PARTICIPANT_GROUP", "Participant")

class Command(BaseCommand):
    help = "Sync Google Workspace users into Django (pre-provision)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--only-domain", default=os.environ.get("ALLOWED_EMAIL_DOMAIN"))
        parser.add_argument("--deactivate-suspended", action="store_true",
                            help="If set, mark suspended Google users as inactive in Django.")
        parser.add_argument("--lockfile", default="/tmp/sync_workspace_users.lock",
                            help="Prevent concurrent runs.")

    def handle(self, *args, **opts):
        # --- single-run lock (avoid overlapping cron jobs) ---
        lockpath = opts["lockfile"]
        lockfh = open(lockpath, "w")
        try:
            fcntl.flock(lockfh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.stdout.write(self.style.WARNING("Another sync is already running; exiting."))
            return

        sa_path = os.environ["GOOGLE_SA_JSON"]
        admin_email = os.environ["GOOGLE_ADMIN_EMAIL"]
        only_domain = (opts["only_domain"] or "").lower()
        dry = opts["dry_run"]
        deactivate_suspended = opts["deactivate_suspended"]

        # Ensure default group exists
        participant_group, _ = Group.objects.get_or_create(name=DEFAULT_GROUP_NAME)

        creds = service_account.Credentials.from_service_account_file(sa_path, scopes=SCOPES)
        delegated = creds.with_subject(admin_email)
        service = build("admin", "directory_v1", credentials=delegated, cache_discovery=False)

        page_token = None
        total = created = updated = linked = grouped = deactivated = 0

        while True:
            resp = service.users().list(
                customer="my_customer", maxResults=500, pageToken=page_token, orderBy="email"
            ).execute()
            users = resp.get("users", [])
            for gu in users:
                total += 1
                primary_email = (gu.get("primaryEmail") or "").lower()
                if not primary_email or (only_domain and not primary_email.endswith(f"@{only_domain}")):
                    continue

                suspended = bool(gu.get("suspended"))
                first = gu.get("name", {}).get("givenName") or ""
                last  = gu.get("name", {}).get("familyName") or ""
                google_uid = gu.get("id")

                obj, was_created = User.objects.get_or_create(
                    email=primary_email,
                    defaults={
                        "username": primary_email,   # safe even if you don’t use username
                        "first_name": first,
                        "last_name": last,
                        "is_active": not suspended,
                    },
                )

                if not was_created:
                    changed = False
                    if first and obj.first_name != first:
                        obj.first_name = first; changed = True
                    if last and obj.last_name != last:
                        obj.last_name = last; changed = True
                    desired_active = not suspended if deactivate_suspended else True
                    if obj.is_active != desired_active:
                        obj.is_active = desired_active; changed = True
                        if not desired_active:
                            deactivated += 1
                    if changed and not dry:
                        obj.save()
                        updated += 1
                else:
                    if not dry:
                        obj.save()
                    created += 1

                # Email verified so allauth won’t nag
                if not dry:
                    EmailAddress.objects.update_or_create(
                        user=obj, email=primary_email,
                        defaults={"verified": True, "primary": True}
                    )

                # Pre-link SocialAccount by Google Directory UID
                if not dry:
                    SocialAccount.objects.get_or_create(
                        user=obj, provider="google", uid=str(google_uid),
                        defaults={"extra_data": {"source": "directory_sync"}}
                    )
                    linked += 1

                # Ensure default 'Participant' group membership
                if not dry:
                    if not obj.groups.filter(id=participant_group.id).exists():
                        obj.groups.add(participant_group)
                        grouped += 1

                # IMPORTANT: do not modify any other groups (department/team remain manual)

            page_token = resp.get("nextPageToken")
            if not page_token:
                break

        self.stdout.write(self.style.SUCCESS(
            f"Processed={total} created={created} updated={updated} "
            f"social_links_touched={linked} default_group_added={grouped} "
            f"deactivated={deactivated} dry_run={dry}"
        ))