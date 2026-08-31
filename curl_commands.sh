# =============================================================================
#  parserapp — curl commands for the LinkedIn profile API
#
#  Base URL (edit if you run on a different host/port):
BASE="http://127.0.0.1:8000"

# API key required for protected endpoints (set in parserapp/.env -> API_KEYS).
# Replace with your real key before hosting.
API_KEY="your-api-key-1"

# URL-encoded example vanity names:
USERNAME="satyanadella"
PROFILE_URL="https://www.linkedin.com/in/satyanadella"
# =============================================================================


# -----------------------------------------------------------------------------
# 1) Health check (no API key required)
# -----------------------------------------------------------------------------
curl -s "$BASE/health" | python3 -m json.tool


# -----------------------------------------------------------------------------
# 2) Get a profile by LinkedIn vanity username (API key required)
# -----------------------------------------------------------------------------
curl -s "$BASE/api/profile?username=$USERNAME" \
     -H "X-API-Key: $API_KEY" | python3 -m json.tool


# -----------------------------------------------------------------------------
# 3) Get a profile by full LinkedIn URL (API key required)
#    The API accepts a full profile URL in place of the username.
# -----------------------------------------------------------------------------
curl -s "$BASE/api/profile?username=$PROFILE_URL" \
     -H "X-API-Key: $API_KEY" | python3 -m json.tool


# -----------------------------------------------------------------------------
# 4) Get a profile using caller-supplied LinkedIn cookies (API key required)
#    Uses li_at + jsessionid instead of the server .env session.
# -----------------------------------------------------------------------------
LI_AT="your-li-at-cookie"
JSESSIONID="ajax:your-jsessionid"

curl -s -G "$BASE/api/profile/with-cookies" \
     --data-urlencode "username=$USERNAME" \
     --data-urlencode "li_at=$LI_AT" \
     --data-urlencode "jsessionid=$JSESSIONID" \
     -H "X-API-Key: $API_KEY" | python3 -m json.tool


# -----------------------------------------------------------------------------
# 5) Pretty-print with a tool (e.g. jq, if installed)
# -----------------------------------------------------------------------------
curl -s "$BASE/api/profile?username=$USERNAME" \
     -H "X-API-Key: $API_KEY" | jq .


# -----------------------------------------------------------------------------
# Error cases (for testing)
# -----------------------------------------------------------------------------

# 4.1) Missing / invalid API key  -> HTTP 401
curl -s -o /dev/null -w "no-key -> %{http_code}\n" \
     "$BASE/api/profile?username=$USERNAME"

curl -s -o /dev/null -w "bad-key -> %{http_code}\n" \
     "$BASE/api/profile?username=$USERNAME" -H "X-API-Key: not-a-real-key"

# 4.2) Invalid username / URL    -> HTTP 400
#      (spaces/underscores are not valid vanity names)
curl -s -o /dev/null -w "bad-username -> %{http_code}\n" \
     "$BASE/api/profile?username=bad%20name" -H "X-API-Key: $API_KEY"

# 4.3) Rate limit (10 req/min by default) -> HTTP 429
for i in $(seq 1 12); do
  curl -s -o /dev/null -w "req $i -> %{http_code}\n" \
       "$BASE/api/profile?username=$USERNAME" -H "X-API-Key: $API_KEY"
done

# 4.4) LinkedIn session/auth failure  -> HTTP 502
#      (returns {"detail":"LinkedIn session expired and auto-login failed"})


# -----------------------------------------------------------------------------
# Save a profile to a file (useful for scripting)
# -----------------------------------------------------------------------------
curl -s "$BASE/api/profile?username=$USERNAME" \
     -H "X-API-Key: $API_KEY" -o "$USERNAME.json"
