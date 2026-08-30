from pydantic import BaseModel


class Experience(BaseModel):
    title: str | None = None
    company: str | None = None
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None
    company_logo_url: str | None = None


class Education(BaseModel):
    school: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    start_year: int | None = None
    end_year: int | None = None
    description: str | None = None
    school_logo_url: str | None = None


class Certification(BaseModel):
    name: str | None = None
    authority: str | None = None
    url: str | None = None


class Language(BaseModel):
    name: str | None = None
    proficiency: str | None = None


class Publication(BaseModel):
    name: str | None = None
    publisher: str | None = None
    url: str | None = None
    description: str | None = None
    published_date: str | None = None
    authors: list[str] = []


class Volunteering(BaseModel):
    organization: str | None = None
    role: str | None = None
    cause: str | None = None
    cause_label: str | None = None
    description: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class Honor(BaseModel):
    title: str | None = None
    issuer: str | None = None
    description: str | None = None
    issued_date: str | None = None


class ProfileResponse(BaseModel):
    name: str | None = None
    headline: str | None = None
    profile_url: str | None = None
    profile_slug: str | None = None
    profile_id: str | None = None
    profile_urn: str | None = None
    location: str | None = None
    about: str | None = None
    profile_image_url: str | None = None
    background_image_url: str | None = None
    connections_count: int | None = None
    followers_count: int | None = None
    experience: list[Experience] = []
    education: list[Education] = []
    skills: list[str] = []
    certifications: list[Certification] = []
    languages: list[Language] = []
    publications: list[Publication] = []
    volunteering: list[Volunteering] = []
    honors: list[Honor] = []


class ErrorResponse(BaseModel):
    detail: str
