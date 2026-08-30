from cachetools import TTLCache
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.linkedin.client import LinkedInClient
from app.routes.profile import router as profile_router

cache = TTLCache(maxsize=1_000, ttl=settings.CACHE_TTL)
linkedin_client = LinkedInClient(
    li_at=settings.LI_AT,
    jsessionid=settings.jsessionid_clean,
    email=settings.LI_EMAIL,
    password=settings.LI_PASSWORD,
)

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT}/minute"],
)
app = FastAPI()

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profile_router)


@app.get("/health", tags=["Health"])
async def health_check():
    healthy = await linkedin_client.check_health()
    return {
        "status": "healthy" if healthy else "unhealthy",
        "linkedin_session_valid": healthy,
        "cache_size": len(cache),
        "cache_max_size": cache.maxsize,
    }
