import os
import jwt
import httpx
from jwt import PyJWKClient
from fastapi import HTTPException, status
from cachetools import TTLCache

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

        from loguru import logger
        self.issuer = f"https://{self.auth0_domain}/"
        jwks_url = f"https://{self.auth0_domain}/.well-known/jwks.json"
        self.jwks_client = PyJWKClient(jwks_url)
        # Initialize a Time-To-Live (TTL) cache for user info.
        # This cache stores up to 1024 user info entries. Each entry expires after
        # 3600 seconds (1 hour) to avoid hitting Auth0's /userinfo rate limits.
        # Expired items are automatically evicted upon access.
        self.userinfo_cache = TTLCache(maxsize=1024, ttl=3600)

    def verify_token(self, token: str) -> dict:
        from loguru import logger
        logger.debug(f"Received token for verification (first 20 chars): {token[:20]}...")
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
        # --- Caching Step 1: Check for existing entry ---
        # Before making an API call, check if the user info for this specific token
        # is already in our cache.
        if token in self.userinfo_cache:
            # If found, return the cached data immediately.
            return self.userinfo_cache[token]

        # --- API Call Step: If not in cache, fetch from Auth0 ---
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
                if 'email' not in user_info:
                    user_info['email'] = None
                
                # --- Caching Step 2: Store the new entry ---
                # After successfully fetching the user info, store it in the cache.
                # The TTLCache will automatically associate it with the current timestamp.
                # It will be valid for the next 1 hour (3600 seconds).
                self.userinfo_cache[token] = user_info
                
                return user_info
            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Error fetching user info from Auth0: {e.response.text}",
                    headers={"WWW-Authenticate": "Bearer"},
                )

auth_service = AuthService()
