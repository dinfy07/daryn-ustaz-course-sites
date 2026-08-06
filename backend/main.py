import os
import secrets
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./reviews.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)


class Base(DeclarativeBase):
    pass


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_slug: Mapped[str] = mapped_column("site_slug", String(30), index=True)
    name: Mapped[str] = mapped_column(String(100))
    comment: Mapped[str] = mapped_column("message", Text)
    stars: Mapped[int] = mapped_column("rating", Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Site(Base):
    __tablename__ = "sites"

    slug: Mapped[str] = mapped_column(String(30), primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    subtitle: Mapped[str] = mapped_column(Text)
    program_url: Mapped[str] = mapped_column(Text)
    email: Mapped[str] = mapped_column(String(254))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ReviewCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    comment: str = Field(min_length=3, max_length=1500)
    stars: int = Field(ge=1, le=5)


class ReviewOut(BaseModel):
    id: int
    name: str
    comment: str
    stars: int
    created_at: datetime


class SiteOut(BaseModel):
    slug: str
    title: str
    program_url: str


class ProgramUrlUpdate(BaseModel):
    program_url: str = Field(min_length=8, max_length=2000, pattern=r"^https://")


VALID_COURSES = {f"course-{i}" for i in range(1, 7)}


def require_admin(authorization: str | None = Header(default=None)) -> None:
    password = os.getenv("ADMIN_PASSWORD")
    if not password:
        raise HTTPException(503, "Admin access is not configured")
    if not authorization or not secrets.compare_digest(authorization, f"Bearer {password}"):
        raise HTTPException(401, "Invalid admin password")

app = FastAPI(title="Daryn Ustaz Reviews API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(engine)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/sites/{course_slug}", response_model=SiteOut)
def get_site(course_slug: str) -> Site:
    with Session(engine) as session:
        site = session.get(Site, course_slug)
        if not site:
            raise HTTPException(404, "Course not found")
        return site


@app.get("/api/admin/sites", response_model=list[SiteOut], dependencies=[Depends(require_admin)])
def admin_sites() -> list[Site]:
    with Session(engine) as session:
        return list(session.scalars(select(Site).order_by(Site.slug)).all())


@app.patch("/api/admin/sites/{course_slug}", response_model=SiteOut, dependencies=[Depends(require_admin)])
def update_program_url(course_slug: str, payload: ProgramUrlUpdate) -> Site:
    with Session(engine) as session:
        site = session.get(Site, course_slug)
        if not site:
            raise HTTPException(404, "Course not found")
        site.program_url = payload.program_url.strip()
        site.updated_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(site)
        return site


@app.get("/api/reviews/{course_slug}", response_model=list[ReviewOut])
def get_reviews(course_slug: str) -> list[Review]:
    if course_slug not in VALID_COURSES:
        raise HTTPException(404, "Course not found")
    with Session(engine) as session:
        return list(session.scalars(select(Review).where(Review.course_slug == course_slug).order_by(Review.created_at.desc())).all())


@app.post("/api/reviews/{course_slug}", response_model=ReviewOut, status_code=201)
def create_review(course_slug: str, payload: ReviewCreate) -> Review:
    if course_slug not in VALID_COURSES:
        raise HTTPException(404, "Course not found")
    review = Review(course_slug=course_slug, name=payload.name.strip(), comment=payload.comment.strip(), stars=payload.stars)
    with Session(engine) as session:
        session.add(review)
        session.commit()
        session.refresh(review)
        return review
