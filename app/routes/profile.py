import re

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.dependencies import verify_api_key
from app.linkedin.client import LinkedInClient
from app.models import ErrorResponse, ProfileResponse

router = APIRouter(prefix="/api", tags=["Profile"])

LINKEDIN_URL_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?linkedin\.com/in/([^/?#]+)"
)
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9\-]+$")

def _extract_username(value: str) -> str:
    username = value.strip().rstrip("/")

    url_match = LINKEDIN_URL_PATTERN.search(username)
    if url_match:
        return url_match.group(1).lower()

    if USERNAME_PATTERN.match(username):
        return username.lower()

    raise HTTPException(
        status_code=400,
        detail=f"Invalid username or LinkedIn URL: {value}",
    )


@router.get(
    "/profile",
    response_model=ProfileResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
    summary="Get LinkedIn profile data",
    description="Fetches structured profile data for a LinkedIn user.",
)
async def get_profile(
    request: Request,
    username: str = Query(
        ...,
        description="LinkedIn vanity name (e.g. 'satyanadella')",
    ),
    api_key: str = Depends(verify_api_key),
):
    from app.main import cache, linkedin_client
    from app.linkedin.parser import parse_profile

    vanity_name = _extract_username(username)

    cached = cache.get(vanity_name)
    if cached is not None:
        return cached

    raw = await linkedin_client.get_profile(vanity_name)
    parsed = parse_profile(raw, requested_identifier=vanity_name)
    cache[vanity_name] = parsed

    return parsed


@router.get(
    "/profile/with-cookies",
    response_model=ProfileResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
    summary="Get LinkedIn profile data using caller-supplied cookies",
    description=(
        "Fetches structured profile data using the provided `li_at` and "
        "`jsessionid` cookies instead of the server environment session."
    ),
)
async def get_profile_with_cookies(
    request: Request,
    username: str = Query(
        ...,
        description="LinkedIn vanity name (e.g. 'satyanadella')",
    ),
    li_at: str = Query(..., description="LinkedIn `li_at` session cookie"),
    jsessionid: str = Query(
        ...,
        description="LinkedIn `JSESSIONID` cookie (quotes optional)",
    ),
    api_key: str = Depends(verify_api_key),
):
    from app.linkedin.parser import parse_profile

    vanity_name = _extract_username(username)
    li_at = li_at.strip()
    jsessionid = jsessionid.strip().strip('"')

    if not li_at or not jsessionid:
        raise HTTPException(
            status_code=400,
            detail="Both li_at and jsessionid cookies are required",
        )

    client = LinkedInClient(li_at=li_at, jsessionid=jsessionid)
    try:
        raw = await client.get_profile(vanity_name)
        return parse_profile(raw, requested_identifier=vanity_name)
    finally:
        await client.close()
