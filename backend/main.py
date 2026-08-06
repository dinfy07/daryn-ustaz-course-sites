import os
import random
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Integer, String, Text, create_engine, select, text
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


NEW_COURSES = {
    "course-7": {
        "title": "Мектепке дейінгі жастағы балалардың білім беру қызметін ұйымдастыруда тәрбиешінің кәсіби құзыреттерін дамыту",
        "subtitle": "Педагогтердің біліктілігін арттыру курстарының білім беру бағдарламасы",
        "reviews": [
            ("Айдана Серікқызы", "Курс мектепке дейінгі білім беру жұмысын жаңаша ұйымдастыруға қажетті пайдалы тәсілдерді көрсетті.", 5),
            ("Гүлнар Талғатқызы", "Тәрбиешінің кәсіби құзыреттерін дамытуға арналған практикалық ұсыныстар өте құнды болды.", 5),
            ("Мадина Ерланқызы", "Балалардың жас ерекшеліктерін ескеріп қызметті жоспарлау бойынша жаңа идеялар алдым.", 5),
            ("Салтанат Нұрланқызы", "Материал түсінікті және жүйелі берілген. Көптеген әдістерді тобымда қолданамын.", 4),
            ("Әсел Болатқызы", "Курс кәсіби тәжірибемді талдап, білім беру ортасын жақсартуға көмектесті.", 5),
            ("Жанар Қайратқызы", "Практикалық мысалдар мен тапсырмалар тәрбиешілер үшін өте пайдалы.", 5),
            ("Ләззат Мұратқызы", "Бағдарлама мазмұны өзекті. Кейбір тақырыптарға көбірек уақыт бөлінсе жақсы болар еді.", 4),
            ("Кәмшат Әлиқызы", "Балалармен білім беру қызметін ұйымдастырудың тиімді жолдарын меңгердім.", 5),
            ("Нұргүл Асқарқызы", "Курс маған кәсіби сенімділік беріп, күнделікті жұмысқа жаңа серпін қосты.", 5),
            ("Динара Бекқызы", "Әдістемелік материалдар сапалы, мазмұны мектепке дейінгі ұйым тәжірибесіне сай.", 5),
        ],
    },
    "course-8": {
        "title": "Развитие профессиональных компетенций воспитателя в организации образовательной деятельности детей дошкольного возраста",
        "subtitle": "Образовательная программа курса повышения квалификации педагогов",
        "reviews": [
            ("Елена Андреевна", "Курс дал современные инструменты для организации образовательной деятельности дошкольников.", 5),
            ("Марина Сергеевна", "Практические рекомендации легко адаптировать к ежедневной работе воспитателя.", 5),
            ("Ольга Викторовна", "Особенно полезными были материалы по планированию занятий с учётом возраста детей.", 5),
            ("Наталья Игоревна", "Программа хорошо структурирована, хотелось бы ещё больше времени на разбор кейсов.", 4),
            ("Ирина Павловна", "Полученные знания помогут сделать образовательную среду группы более развивающей.", 5),
            ("Светлана Олеговна", "Материал актуальный, понятный и ориентированный на реальную практику воспитателя.", 5),
            ("Анна Михайловна", "Курс помог систематизировать опыт и освоить новые методы взаимодействия с детьми.", 5),
            ("Татьяна Романовна", "Полезная программа, некоторые методики уже начала применять в своей группе.", 4),
            ("Людмила Борисовна", "Понравилось сочетание теории и практических заданий. Спасибо за качественные материалы.", 5),
            ("Виктория Алексеевна", "Курс способствует профессиональному росту и даёт много идей для работы с дошкольниками.", 5),
        ],
    },
}


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
    with Session(engine) as session:
        rng = random.Random(20260806)
        start = datetime(2026, 7, 1, tzinfo=timezone.utc)
        # Keep dates inside July-August even after Kazakhstan's UTC+5 conversion.
        span_seconds = (61 * 24 + 18) * 60 * 60 - 1
        for slug, data in NEW_COURSES.items():
            if session.get(Site, slug):
                continue
            session.add(Site(
                slug=slug,
                title=data["title"],
                subtitle=data["subtitle"],
                program_url="https://docs.google.com/document/d/1IQ5fs2VojgV_s4Hg4tr0TO8_S1J8-i-k/edit?usp=sharing",
                email="daryn.teacher@gmail.com",
            ))
            session.flush()
            for name, comment, stars in data["reviews"]:
                session.add(Review(
                    course_slug=slug,
                    name=name,
                    comment=comment,
                    stars=stars,
                    created_at=start + timedelta(seconds=rng.randint(0, span_seconds)),
                ))
        session.commit()
    if engine.dialect.name == "postgresql":
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE IF NOT EXISTS app_settings (key VARCHAR(100) PRIMARY KEY, value TEXT NOT NULL)"))
            already_done = connection.execute(text("SELECT 1 FROM app_settings WHERE key = 'review_dates_july_august_2026'")).first()
            if not already_done:
                connection.execute(text("""
                    UPDATE reviews
                    SET created_at = TIMESTAMPTZ '2026-07-01 00:00:00+00'
                        + random() * (TIMESTAMPTZ '2026-09-01 00:00:00+00' - TIMESTAMPTZ '2026-07-01 00:00:00+00')
                    WHERE created_at < TIMESTAMPTZ '2026-08-06 00:00:00+00'
                """))
                connection.execute(text("INSERT INTO app_settings (key, value) VALUES ('review_dates_july_august_2026', 'done')"))
            preschool_dates_fixed = connection.execute(text("SELECT 1 FROM app_settings WHERE key = 'preschool_review_dates_local_2026'")).first()
            if not preschool_dates_fixed:
                connection.execute(text("""
                    UPDATE reviews
                    SET created_at = created_at - INTERVAL '1 day'
                    WHERE site_slug IN ('course-7', 'course-8')
                      AND created_at >= TIMESTAMPTZ '2026-08-31 19:00:00+00'
                """))
                connection.execute(text("INSERT INTO app_settings (key, value) VALUES ('preschool_review_dates_local_2026', 'done')"))


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
    with Session(engine) as session:
        if not session.get(Site, course_slug):
            raise HTTPException(404, "Course not found")
        return list(session.scalars(select(Review).where(Review.course_slug == course_slug).order_by(Review.created_at.desc())).all())


@app.post("/api/reviews/{course_slug}", response_model=ReviewOut, status_code=201)
def create_review(course_slug: str, payload: ReviewCreate) -> Review:
    with Session(engine) as session:
        if not session.get(Site, course_slug):
            raise HTTPException(404, "Course not found")
        review = Review(course_slug=course_slug, name=payload.name.strip(), comment=payload.comment.strip(), stars=payload.stars)
        session.add(review)
        session.commit()
        session.refresh(review)
        return review
