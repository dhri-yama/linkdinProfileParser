BASE_URL = "https://www.linkedin.com"

PROFILE_ENDPOINT = "/voyager/api/identity/dash/profiles"

PROFILE_DECORATION_ID = (
    "com.linkedin.voyager.dash.deco.identity.profile.FullProfileWithEntities-93"
)

SKILLS_ENDPOINT = "/voyager/api/graphql"

DEFAULT_HEADERS = {
    "x-restli-protocol-version": "2.0.0",
    "x-li-lang": "en_US",
    "x-li-page-instance": "urn:li:page:d_flagship3_profile_view_base",
    "Accept": "application/vnd.linkedin.normalized+json+2.1",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}
