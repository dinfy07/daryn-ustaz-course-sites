import os
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
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


VALID_COURSES = {f"course-{i}" for i in range(1, 7)}

app = FastAPI(title="Daryn Ustaz Reviews API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(engine)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
