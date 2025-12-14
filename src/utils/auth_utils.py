import os
from fastapi.security import OAuth2AuthorizationCodeBearer

# This file is created to avoid circular dependencies.

auth0_domain = os.getenv("AUTH0_DOMAIN", "")

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"https://{auth0_domain}/authorize",
    tokenUrl=f"https://{auth0_domain}/oauth/token",
    scopes={"openid": "Read OpenID", "profile": "Read Profile", "email": "Read Email"},
)
