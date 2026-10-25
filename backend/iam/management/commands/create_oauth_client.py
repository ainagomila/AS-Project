from django.conf import settings
from django.core.management.base import BaseCommand
from oauth2_provider.models import Application

CLIENT_ID = "kofre-web"


class Command(BaseCommand):
    help = (
        "Create or update the OAuth client used by the Vue app. "
        "Safe to run on every start: it never creates duplicates."
    )

    def handle(self, *args, **options):
        redirect_uri = f"{settings.FRONTEND_URL.rstrip('/')}/callback"
        _, created = Application.objects.update_or_create(
            client_id=CLIENT_ID,
            defaults={
                "name": "Kofre web",
                "client_type": Application.CLIENT_PUBLIC,  # a browser app cannot keep a secret
                "authorization_grant_type": Application.GRANT_AUTHORIZATION_CODE,
                "redirect_uris": redirect_uri,
                "algorithm": Application.RS256_ALGORITHM,  # needed to sign the ID token
                "skip_authorization": True,  # first-party app: no consent screen
            },
        )
        action = "Created" if created else "Updated"
        self.stdout.write(f"{action} OAuth client '{CLIENT_ID}' (redirect: {redirect_uri})")
