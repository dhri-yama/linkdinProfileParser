import asyncio

import requests
from fastapi import HTTPException

from app.linkedin.endpoints import (
    BASE_URL,
    DEFAULT_HEADERS,
    PROFILE_DECORATION_ID,
    PROFILE_ENDPOINT,
)

LOGIN_URL = "https://www.linkedin.com/uas/authenticate"

# LinkedIn's /uas/authenticate is the MOBILE auth-library endpoint. A desktop
# browser UA + loginCsrfParam is rejected with 403; these mobile auth-library
# headers (plus JSESSIONID sent as a form field) are what actually authenticate.
AUTH_HEADERS = {
    "X-Li-User-Agent": "LIAuthLibrary:0.0.3 com.linkedin.android:4.1.881 Asus_ASUS_Z01QD:android_9",
    "User-Agent": "ANDROID OS",
    "X-User-Language": "en",
    "X-User-Locale": "en_US",
    "Accept-Language": "en-us",
}


class LinkedInAuthError(HTTPException):
    def __init__(self, reason: str = ""):
        if reason:
            detail = f"LinkedIn session expired and auto-login failed: {reason}"
        else:
            detail = "LinkedIn session expired and auto-login failed"
        super().__init__(status_code=502, detail=detail)


class LinkedInNotFoundError(HTTPException):
    def __init__(self, username: str):
        super().__init__(
            status_code=404, detail=f"LinkedIn profile not found: {username}"
        )


class LinkedInRateLimitError(HTTPException):
    def __init__(self):
        super().__init__(status_code=429, detail="Rate limited by LinkedIn")


class LinkedInClient:
    def __init__(
        self,
        li_at: str = "",
        jsessionid: str = "",
        email: str = "",
        password: str = "",
    ):
        self._email = email
        self._password = password
        self._last_login_reason = ""
        # Plain requests (HTTP/1.1). curl_cffi's HTTP/2 fingerprint got the li_at
        # invalidated; this transport keeps the established session stable.
        self._session = requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)

        if li_at and jsessionid:
            self._set_auth_cookies(li_at, jsessionid)

    def _set_auth_cookies(self, li_at: str, jsessionid: str):
        self._session.cookies.set("li_at", li_at, domain=".linkedin.com")
        self._session.cookies.set("JSESSIONID", f'"{jsessionid}"', domain=".linkedin.com")
        self._session.headers["csrf-token"] = jsessionid

    def _csrf(self) -> str:
        return (self._session.cookies.get("JSESSIONID") or "").strip('"')

    def login_sync(self) -> bool:
        self._last_login_reason = ""
        if not self._email or not self._password:
            self._last_login_reason = "no LinkedIn credentials configured"
            print("No LinkedIn credentials configured — cannot auto-login")
            return False

        try:
            s = requests.Session()

            # 1) Seed JSESSIONID cookies from the auth endpoint.
            s.get(
                LOGIN_URL,
                headers=AUTH_HEADERS,
                allow_redirects=True,
                timeout=15,
            )
            jsessionid = (s.cookies.get("JSESSIONID") or "").strip('"')

            # 2) Authenticate via the mobile auth-library endpoint.
            resp = s.post(
                LOGIN_URL,
                data={
                    "session_key": self._email,
                    "session_password": self._password,
                    "JSESSIONID": jsessionid,
                },
                headers=AUTH_HEADERS,
                allow_redirects=False,
                timeout=20,
            )
            try:
                login_result = resp.json().get("login_result")
            except Exception:
                login_result = None

            if login_result != "PASS":
                if login_result == "CHALLENGE":
                    self._last_login_reason = (
                        "blocked by LinkedIn security challenge (CAPTCHA); "
                        "supply fresh LI_AT / JSESSIONID cookies from a "
                        "logged-in browser"
                    )
                    print(
                        "Auto-login blocked by LinkedIn security challenge "
                        "(CAPTCHA). Update the LI_AT / JSESSIONID cookies in "
                        ".env with fresh values from a logged-in browser."
                    )
                else:
                    self._last_login_reason = f"LinkedIn returned login_result={login_result!r}"
                    print(f"Auto-login failed (login_result={login_result!r})")
                return False

            s.cookies.update(resp.cookies)

            # 3) Establish the session with a warm-up GET to "/" so LinkedIn
            # does not kill the li_at on the first Voyager call.
            jsessionid = (s.cookies.get("JSESSIONID") or "").strip('"')
            s.headers["csrf-token"] = jsessionid
            s.get(BASE_URL, headers=AUTH_HEADERS, allow_redirects=True, timeout=15)

            if not s.cookies.get("li_at"):
                self._last_login_reason = "auto-login succeeded but no li_at cookie returned"
                print("Auto-login failed — no li_at returned")
                return False

            self._session.close()
            self._session = s
            self._last_login_reason = ""
            print("Auto-login successful")
            return True
        except Exception as error:
            self._last_login_reason = f"auto-login raised exception: {error}"
            print(f"Auto-login error: {error}")
            return False

    async def login(self) -> bool:
        return await asyncio.to_thread(self.login_sync)

    def _needs_reauth(self, response) -> bool:
        if response.status_code == 302:
            return True
        if response.status_code in (401, 403):
            return True
        for key, value in response.cookies.items():
            if key == "li_at" and value == "delete me":
                return True
        return False

    def _update_cookies_from_response(self, response):
        li_at = response.cookies.get("li_at")
        js = response.cookies.get("JSESSIONID")
        if li_at and li_at != "delete me":
            self._session.cookies.set("li_at", li_at, domain=".linkedin.com")
            print("LinkedIn rotated li_at cookie (updated)")
        if js and js != "delete me":
            clean = js.strip('"')
            self._session.cookies.set("JSESSIONID", f'"{clean}"', domain=".linkedin.com")
            self._session.headers["csrf-token"] = clean
            print("LinkedIn rotated JSESSIONID cookie (updated)")

    def get_profile_sync(self, vanity_name: str) -> dict:
        url = f"{BASE_URL}{PROFILE_ENDPOINT}"
        params = {
            "q": "memberIdentity",
            "memberIdentity": vanity_name,
            "decorationId": PROFILE_DECORATION_ID,
        }

        # Prefer the existing cookie session. Only fall back to auto-login if
        # that cookie is rejected / expired, so a valid li_at is never
        # overwritten by a failing (often CHALLENGE-blocked) mobile login.
        response = None
        for attempt in range(2):
            response = self._session.get(
                url,
                params=params,
                headers={"csrf-token": self._csrf()},
                allow_redirects=False,
                timeout=15,
            )

            if not self._needs_reauth(response):
                break

            if attempt == 1:
                break
            if not self.login_sync():
                raise LinkedInAuthError(self._last_login_reason)

        self._update_cookies_from_response(response)

        if response.status_code in (401, 403):
            raise LinkedInAuthError()
        if response.status_code == 404:
            raise LinkedInNotFoundError(vanity_name)
        if response.status_code == 429:
            raise LinkedInRateLimitError()
        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"LinkedIn returned unexpected status {response.status_code}",
            )

        return response.json()

    async def get_profile(self, vanity_name: str) -> dict:
        return await asyncio.to_thread(self.get_profile_sync, vanity_name)

    def check_health_sync(self) -> bool:
        try:
            url = f"{BASE_URL}/voyager/api/me"
            response = self._session.get(
                url,
                headers={"csrf-token": self._csrf()},
                allow_redirects=False,
                timeout=10,
            )

            if self._needs_reauth(response):
                return self.login_sync()
            self._update_cookies_from_response(response)
            return response.status_code == 200
        except Exception:
            return False

    async def check_health(self) -> bool:
        return await asyncio.to_thread(self.check_health_sync)

    async def close(self):
        def _close():
            try:
                self._session.close()
            except Exception:
                pass

        await asyncio.to_thread(_close)
