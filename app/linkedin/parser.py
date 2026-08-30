from app.models import (
    Certification,
    Education,
    Experience,
    Honor,
    Language,
    ProfileResponse,
    Publication,
    Volunteering,
)


CAUSE_LABELS = {
    "ARTS_AND_CULTURE": "Arts & Culture",
    "CHILDREN": "Children",
    "CIVIC_AND_SOCIAL": "Civic & Social",
    "CIVIL_RIGHTS_AND_SOCIAL_ACTION": "Civil Rights & Social Action",
    "DISASTER_AND_HUMANITARIAN_RELIEF": "Disaster & Humanitarian Relief",
    "EDUCATION": "Education",
    "ENVIRONMENT": "Environment",
    "HEALTH": "Health",
    "HUMAN_RIGHTS": "Human Rights",
    "POVERTY_ALLEVIATION": "Poverty Alleviation",
    "SCIENCE_AND_TECHNOLOGY": "Science & Technology",
    "SOCIAL_SERVICES": "Social Services",
}


def _extract_image_url(image_data: dict | None) -> str | None:
    if not image_data:
        return None
    try:
        vector = image_data["displayImageReference"]["vectorImage"]
        root_url = vector["rootUrl"]
        artifacts = vector.get("artifacts", [])
        if not artifacts:
            return None
        largest = max(artifacts, key=lambda artifact: artifact.get("width", 0))
        return root_url + largest["fileIdentifyingUrlPathSegment"]
    except (KeyError, TypeError):
        return None


def _format_date(date_obj: dict | None) -> str | None:
    if not date_obj:
        return None
    year = date_obj.get("year")
    month = date_obj.get("month")
    if year and month:
        return f"{year}-{month:02d}"
    if year:
        return str(year)
    return None


def _date_sort_value(value) -> int | None:
    """Return a comparable int for a date value (descending sort).

    Handles ISO-ish strings ('YYYY-MM', 'YYYY') and int years.
    Returns None when there is no usable date.
    """
    if value is None:
        return None
    if isinstance(value, int):
        return value * 100
    text = str(value).strip()
    if not text:
        return None
    parts = text.split("-")
    try:
        year = int(parts[0])
        if len(parts) > 1 and parts[1]:
            month = int(parts[1])
            return year * 100 + month
        return year * 100
    except ValueError:
        return None


def _sort_desc_by_date(items: list, date_fields: tuple[str, ...]) -> list:
    """Sort items most-recent-first by the first present date field.

    Items with no date sort last.
    """

    def sort_value(item):
        for field in date_fields:
            value = _date_sort_value(getattr(item, field, None))
            if value is not None:
                return value
        return -1

    return sorted(items, key=sort_value, reverse=True)


def _find_entities(included: list[dict], type_suffix: str) -> list[dict]:
    return [
        item for item in included if item.get("$type", "").endswith(type_suffix)
    ]


def _select_target_profile(
    included: list[dict], data: dict | None, requested_identifier: str | None = None
) -> dict:
    """Pick the actual person's Profile entity.

    A FullProfileWithEntities response can contain several Profile entities in
    `included` (e.g. profiles linked from positions/publications), so using the
    first one is unreliable. The real profile matches the URN in
    `data['*elements']`; if that's unavailable we fall back to matching
    `publicIdentifier` against the requested username, and finally to the
    first Profile entity.
    """
    profiles = _find_entities(included, "Profile")
    if not profiles:
        return {}

    # 1) The viewed profile is the only fully-decorated Profile entity: it is
    #    the one that carries an objectUrn (member URN) and richer fields
    #    (industryUrn, premium, influencer). Profiles pulled in from other
    #    segments (e.g. Publication co-authors) are minimal cards lacking it.
    for profile in profiles:
        if profile.get("objectUrn"):
            return profile

    # 2) Match by the data element URN.
    try:
        elements = (data or {}).get("*elements", [])
        data_urn = elements[0] if elements else None
        for profile in profiles:
            if profile.get("entityUrn") == data_urn:
                return profile
    except (KeyError, IndexError, TypeError):
        pass

    # 2) Match by publicIdentifier against the requested username.
    if requested_identifier:
        req = str(requested_identifier).strip().lower()
        for profile in profiles:
            pub = (profile.get("publicIdentifier") or "").strip().lower()
            if pub == req:
                return profile

    # 3) Fall back to the first Profile entity.
    return profiles[0]


def _parse_experience(included: list[dict]) -> list[Experience]:
    positions = _find_entities(included, "Position")
    experiences = []
    for pos in positions:
        date_range = pos.get("dateRange", {}) or {}
        company_logo = None
        company_data = pos.get("company", {}) or {}
        logo = company_data.get("logo", {}) or {}
        if logo:
            company_logo = _extract_image_url(
                {"displayImageReference": {"vectorImage": logo.get("vectorImage")}}
            ) if logo.get("vectorImage") else None

        experiences.append(
            Experience(
                title=pos.get("title"),
                company=pos.get("companyName"),
                location=pos.get("locationName"),
                start_date=_format_date(date_range.get("start")),
                end_date=_format_date(date_range.get("end")),
                description=pos.get("description"),
                company_logo_url=company_logo,
            )
        )
    return experiences


def _parse_education(included: list[dict]) -> list[Education]:
    educations = _find_entities(included, "Education")
    result = []
    for edu in educations:
        date_range = edu.get("dateRange", {}) or {}
        start = date_range.get("start", {}) or {}
        end = date_range.get("end", {}) or {}

        school_logo = None
        school_data = edu.get("school", {}) or {}
        logo = school_data.get("logo", {}) or {}
        if logo:
            school_logo = _extract_image_url(
                {"displayImageReference": {"vectorImage": logo.get("vectorImage")}}
            ) if logo.get("vectorImage") else None

        result.append(
            Education(
                school=edu.get("schoolName"),
                degree=edu.get("degreeName"),
                field_of_study=edu.get("fieldOfStudy"),
                start_year=start.get("year"),
                end_year=end.get("year"),
                description=edu.get("description"),
                school_logo_url=school_logo,
            )
        )
    return result


def _parse_skills(included: list[dict]) -> list[str]:
    skills = _find_entities(included, "Skill")
    return [skill.get("name") for skill in skills if skill.get("name")]


def _parse_certifications(included: list[dict]) -> list[Certification]:
    certs = _find_entities(included, "Certification")
    return [
        Certification(
            name=cert.get("name"),
            authority=cert.get("authority"),
            url=cert.get("url"),
        )
        for cert in certs
    ]


def _parse_languages(included: list[dict]) -> list[Language]:
    langs = _find_entities(included, "Language")
    return [
        Language(
            name=lang.get("name"),
            proficiency=lang.get("proficiency"),
        )
        for lang in langs
    ]


def _parse_publications(included: list[dict]) -> list[Publication]:
    publications = _find_entities(included, "Publication")
    profiles = _find_entities(included, "Profile")
    profile_names = {
        profile.get("entityUrn"): f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip()
        for profile in profiles
    }

    result = []
    for pub in publications:
        authors = []
        for author in pub.get("authors", []) or []:
            contributor = author.get("standardizedContributor", {}) or {}
            urn = contributor.get("profileUrn") or contributor.get("*profile")
            name = profile_names.get(urn)
            if name:
                authors.append(name)
        result.append(
            Publication(
                name=pub.get("name"),
                publisher=pub.get("publisher"),
                url=pub.get("url"),
                description=pub.get("description"),
                published_date=_format_date(pub.get("publishedOn")),
                authors=authors,
            )
        )
    return result


def _parse_volunteering(included: list[dict]) -> list[Volunteering]:
    experiences = _find_entities(included, "VolunteerExperience")
    result = []
    for exp in experiences:
        date_range = exp.get("dateRange", {}) or {}
        cause = exp.get("cause")
        result.append(
            Volunteering(
                organization=exp.get("companyName"),
                role=exp.get("role"),
                cause=cause,
                cause_label=CAUSE_LABELS.get(cause) if cause else None,
                description=exp.get("description"),
                start_date=_format_date(date_range.get("start")),
                end_date=_format_date(date_range.get("end")),
            )
        )
    return result


def _parse_honors(included: list[dict]) -> list[Honor]:
    honors = _find_entities(included, "Honor")
    result = []
    for honor in honors:
        result.append(
            Honor(
                title=honor.get("title"),
                issuer=honor.get("issuer"),
                description=honor.get("description"),
                issued_date=_format_date(honor.get("issuedOn")),
            )
        )
    return result


def parse_profile(raw: dict, requested_identifier: str | None = None) -> ProfileResponse:
    included = raw.get("included", [])
    data = raw.get("data")

    profile = _select_target_profile(included, data, requested_identifier)

    first_name = profile.get("firstName", "")
    last_name = profile.get("lastName", "")
    name = f"{first_name} {last_name}".strip() or None

    profile_slug = profile.get("publicIdentifier") or None
    profile_url = (
        f"https://www.linkedin.com/in/{profile_slug}" if profile_slug else None
    )
    profile_id = profile.get("entityUrn") or None
    profile_urn = profile.get("objectUrn") or None

    geo_location = profile.get("geoLocation", {}) or {}
    geo = geo_location.get("geo", {}) or {}
    location = (
        profile.get("geoLocationName")
        or geo.get("defaultLocalizedName")
        or None
    )

    profile_picture = _extract_image_url(profile.get("profilePicture"))
    background_picture = _extract_image_url(profile.get("backgroundPicture"))

    network_info = {}
    network_entities = _find_entities(included, "NetworkInfo")
    if network_entities:
        network_info = network_entities[0]

    connections_count = network_info.get("connectionsCount")
    followers_count = network_info.get("followersCount") or network_info.get("followerCount")

    experience = _sort_desc_by_date(
        _parse_experience(included), ("start_date", "end_date")
    )
    education = _sort_desc_by_date(
        _parse_education(included), ("start_year", "end_year")
    )
    publications = _sort_desc_by_date(
        _parse_publications(included), ("published_date",)
    )
    volunteering = _sort_desc_by_date(
        _parse_volunteering(included), ("start_date", "end_date")
    )
    honors = _sort_desc_by_date(_parse_honors(included), ("issued_date",))

    return ProfileResponse(
        name=name,
        headline=profile.get("headline"),
        profile_url=profile_url,
        profile_slug=profile_slug,
        profile_id=profile_id,
        profile_urn=profile_urn,
        location=location,
        about=profile.get("summary"),
        profile_image_url=profile_picture,
        background_image_url=background_picture,
        connections_count=connections_count,
        followers_count=followers_count,
        experience=experience,
        education=education,
        skills=_parse_skills(included),
        certifications=_parse_certifications(included),
        languages=_parse_languages(included),
        publications=publications,
        volunteering=volunteering,
        honors=honors,
    )
