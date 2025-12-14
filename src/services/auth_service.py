import os
import jwt
import httpx
from jwt import PyJWKClient
from fastapi import HTTPException, status

class AuthService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AuthService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self.auth0_domain = os.getenv("AUTH0_DOMAIN")
        self.auth0_audience = os.getenv("AUTH0_AUDIENCE")
        
        if not self.auth0_domain or not self.auth0_audience:
            # If env vars are missing, we might be in a test or prod environment where Auth0 is not used.
            # We can log a warning or defer initialization.
            self.jwks_client = None
            return

        self.issuer = f"https://{self.auth0_domain}/"
        jwks_url = f"https://{self.auth0_domain}/.well-known/jwks.json"
        self.jwks_client = PyJWKClient(jwks_url)

    def verify_token(self, token: str) -> dict:
        if not self.jwks_client:
            self._initialize() # Retry initialization if it failed/skipped before
            if not self.jwks_client:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Auth0 configuration missing on server"
                )

        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.auth0_audience,
                issuer=self.issuer
            )
            return payload
        except jwt.PyJWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Could not validate credentials: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    async def get_user_info(self, token: str) -> dict:
        if not self.auth0_domain:
            self._initialize()
            if not self.auth0_domain:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Auth0 domain not configured"
                )
        
        userinfo_url = f"https://{self.auth0_domain}/userinfo"
        headers = {"Authorization": f"Bearer {token}"}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(userinfo_url, headers=headers)
                response.raise_for_status()
                user_info = response.json()
                # Ensure 'email' is present, even if it's null from the provider
                if 'email' not in user_info:
                    user_info['email'] = None
                return user_info
            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Error fetching user info from Auth0: {e.response.text}",
                    headers={"WWW-Authenticate": "Bearer"},
                )

auth_service = AuthService()
