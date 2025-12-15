# Solving the Auth0 API Rate Limit Issue

We ran into a tricky `429 Too Many Requests` issue after integrating Auth0. This document chronicles how we discovered the problem and solved it elegantly by introducing a caching mechanism.

## 1. What Happened?

### The Symptom
The frontend application became unstable after user login. Sometimes, requests to fetch the conversation list would fail, and the browser console showed that the network requests returned a `429` status code. This means we were sending requests too fast and were being rejected by the server.

### Root Cause Analysis
By checking the logs in the Auth0 Dashboard, we found a key error message:
```
"description": "You passed the limit of allowed calls to /userinfo with the same user."
```
This meant our backend service was calling Auth0's `/userinfo` endpoint too frequently within a short period.

**Why did this happen?**
According to our security design, the backend does two things when processing every protected API request (like "fetch conversations", "send message"):
1.  Verifies if the Token is valid.
2.  **Calls Auth0's `/userinfo` endpoint** to ensure the latest user email is retrieved (because the Token sometimes doesn't contain the email).

When a user opens the frontend page, the frontend concurrently sends multiple requests (fetch user info, fetch history conversations, etc.). This causes the backend to bombard Auth0's endpoint multiple times in an instant. The Auth0 free plan limits each user to 10 calls per minute, so we easily exceeded the quota.

## 2. How to Solve It?

Since the bottleneck lies in "frequently and repeatedly calling an external API", the solution is obvious: **Add Caching**.

*   **Idea**: If we have already queried trusted information for this user in the recent past, use the copy stored in memory directly instead of bothering Auth0 again.
*   **Tool**: We used Python's `cachetools` library, specifically `TTLCache` (Time-To-Live Cache).
*   **Strategy**: We set the cache expiration time to **1 hour**. This means that within 1 hour, subsequent requests from the same user will respond in milliseconds (reading from memory) and consume zero Auth0 quota.

### Flowchart

```mermaid
flowchart TD
    A[Backend receives API request] --> B{Token in Cache?};
    B -- Yes --> C[Return cached User Info];
    B -- No --> D[Call Auth0 /userinfo API];
    D --> E{Call Successful?};
    E -- Yes --> F[Store result in Cache (TTL=1hr)];
    F --> G[Use new User Info];
    E -- No --> H[Return Error (429/500)];
    C --> I[Continue Business Logic];
    G --> I;
    H --> I[End];
```

## 3. Code Implementation

We only modified one file: `src/services/auth_service.py`.

### Step 1: Initialize Cache

We created a cache object during the initialization of the `AuthService` class.

```python
# src/services/auth_service.py
from cachetools import TTLCache

class AuthService:
    def _initialize(self):
        # ...
        
        # Create a TTL cache
        # maxsize=1024: Store token info for up to 1024 users
        # ttl=3600: Each record lives for 3600 seconds (1 hour)
        self.userinfo_cache = TTLCache(maxsize=1024, ttl=3600)
```

### Step 2: Revamp User Info Retrieval Logic

We modified the `get_user_info` method to teach it to check the cache first.

```python
    async def get_user_info(self, token: str) -> dict:
        # 1. Check cache first! If found, return directly, saving a network call
        if token in self.userinfo_cache:
            return self.userinfo_cache[token]

        # 2. Not in cache? Then we have to call Auth0
        # ... (omitted some config check code) ...
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(...)
                user_info = response.json()
                
                # 3. After getting the result, save it to cache immediately for next use
                self.userinfo_cache[token] = user_info
                
                return user_info
            except httpx.HTTPStatusError as e:
                # ... (error handling) ...
```

With these few lines of code changes, we completely solved the 429 rate limiting issue and also significantly improved the API response speed.
