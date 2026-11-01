from django.apps import AppConfig


class AuthzConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "authz"
    verbose_name = "Authorization (XACML)"

    def ready(self):
        # Load the policy at start-up: a policy the engine cannot fully
        # understand stops the server instead of failing open later.
        from . import pdp

        pdp.policy()
