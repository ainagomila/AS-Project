from oauth2_provider.oauth2_validators import OAuth2Validator


class KofreOAuth2Validator(OAuth2Validator):
    # The "dni" claim is released together with the "openid" scope.
    oidc_claim_scope = {**OAuth2Validator.oidc_claim_scope, "dni": "openid"}

    def get_additional_claims(self):
        return {"dni": lambda request: request.user.dni}
