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
    "course-9": {
        "title": "Профессиональная деятельность социального педагога: современные вызовы, профилактика и сопровождение обучающихся",
        "subtitle": "Образовательная программа курса повышения квалификации педагогов",
        "reviews": [
            ("Гульмира Абдрахманова", "Курс помог по-новому выстроить профилактическую работу с подростками и их семьями.", 5),
            ("Сергей Ли", "Особенно полезны алгоритмы сопровождения детей, оказавшихся в трудной жизненной ситуации.", 5),
            ("Айжан Нурсеитова", "Практические кейсы хорошо отражают реальные задачи социального педагога.", 5),
            ("Ольга Цой", "Материал системный и понятный, рекомендации можно сразу использовать в школе.", 4),
            ("Руслан Ибраев", "Полезный блок по межведомственному взаимодействию и раннему выявлению рисков.", 5),
            ("Наталья Касенова", "Стала увереннее проводить профилактические встречи и документировать сопровождение.", 5),
            ("Денис Петров", "Хорошо разобраны современные вызовы и границы ответственности специалиста.", 4),
            ("Мадина Сулейменова", "Программа дала готовые инструменты для взаимодействия с классными руководителями.", 5),
        ],
    },
    "course-10": {
        "title": "Әлеуметтік педагогтің кәсіби қызметі: заманауи сын-қатерлер, профилактика және білім алушыларды қолдау",
        "subtitle": "Педагогтердің біліктілігін арттыру курстарының білім беру бағдарламасы",
        "reviews": [
            ("Айнұр Бекенова", "Курс әлеуметтік педагогтің профилактикалық жұмысын жүйелі жоспарлауға көмектесті.", 5),
            ("Мақсат Жүнісов", "Білім алушыларды қолдау бойынша нақты алгоритмдер мен пайдалы үлгілер берілді.", 5),
            ("Кәмшат Оразбаева", "Қиын жағдайдағы балалармен және ата-аналармен жұмыс істеу мысалдары өте құнды.", 5),
            ("Дана Серікқызы", "Тақырыптар өзекті, материал түсінікті және тәжірибеге бағытталған.", 4),
            ("Ермек Қасымов", "Ведомствоаралық өзара іс-қимылға арналған бөлім кәсіби жұмысымда пайдалы болды.", 5),
            ("Ләззат Төлегенова", "Тәуекелдерді ерте анықтау бойынша ұсыныстарды мектепте қолдана бастадым.", 5),
            ("Нұржан Әбдіров", "Маманның жауапкершілік шекаралары нақты түсіндірілген.", 4),
            ("Салтанат Омарова", "Сынып жетекшілерімен бірлескен жұмысқа арналған құралдар ұнады.", 5),
        ],
    },
    "course-11": {
        "title": "Современные подходы в работе педагога-психолога: методы сопровождения, диагностики и поддержки психологического благополучия обучающихся в условиях цифровизации и инклюзивного образования",
        "subtitle": "Образовательная программа курса повышения квалификации педагогов",
        "reviews": [
            ("Ирина Волкова", "Диагностические инструменты изложены корректно и с учётом современной школьной практики.", 5),
            ("Алия Мухамеджанова", "Понравился баланс между цифровыми методами, этикой и живым сопровождением ребёнка.", 5),
            ("Екатерина Ким", "Раздел об инклюзивной среде дал много идей для командной работы со специалистами.", 5),
            ("Тимур Сарсенов", "Материал помогает выстроить понятный маршрут психологической поддержки обучающегося.", 4),
            ("Лариса Пак", "Курс содержательный, кейсы по цифровым рискам особенно актуальны.", 5),
            ("Светлана Романова", "Полезны рекомендации по бережной диагностике и работе с родителями.", 5),
            ("Арман Жаксылыков", "Систематизировал подходы к сопровождению детей с особыми образовательными потребностями.", 5),
            ("Виктория Белова", "Хотелось бы больше времени на практику, но материалы очень качественные.", 4),
        ],
    },
    "course-12": {
        "title": "Педагог-психологтың жұмысындағы заманауи тәсілдер: цифрландыру және инклюзивті білім беру жағдайында білім алушылардың психологиялық әл-ауқатын сүйемелдеу, диагностикалау және қолдау әдістері",
        "subtitle": "Педагогтердің біліктілігін арттыру курстарының білім беру бағдарламасы",
        "reviews": [
            ("Назгүл Әлиева", "Психологиялық диагностиканы цифрлық ортада ұйымдастыруға қатысты ұсыныстар өте пайдалы.", 5),
            ("Бауыржан Нұртаев", "Инклюзивті білім беру жағдайындағы сүйемелдеу тәсілдері нақты мысалдармен берілген.", 5),
            ("Ақмарал Сейітова", "Білім алушының әл-ауқатын қолдауға арналған әдістерді жұмысымда қолдана бастадым.", 5),
            ("Жанна Қуатова", "Курс мазмұны жүйелі, этика мен қауіпсіздік мәселелері жақсы қамтылған.", 4),
            ("Әділхан Рахимов", "Педагогтермен және ата-аналармен командалық жұмысқа арналған бөлім ұнады.", 5),
            ("Гүлмира Бақытқызы", "Диагностика нәтижелерін дұрыс түсіндіру бойынша бөлім өте пайдалы болды.", 5),
            ("Ербол Ниязов", "Ерекше білім беру қажеттіліктері бар балаларды қолдау тәсілдерін толықтырдым.", 5),
            ("Мөлдір Сапарова", "Практикалық тапсырмалар жақсы, кейбір тақырыптарға көбірек уақыт бөлінсе екен.", 4),
        ],
    },
    "course-13": {
        "title": "Современные подходы к профилактике суицидального риска и кризисных состояний обучающихся в организациях образования",
        "subtitle": "Образовательная программа курса повышения квалификации педагогов",
        "reviews": [
            ("Анна Гаврилова", "Курс даёт бережные и профессиональные алгоритмы действий при выявлении кризисного состояния.", 5),
            ("Динара Ахметова", "Особенно важны рекомендации по маршрутизации и взаимодействию с родителями и специалистами.", 5),
            ("Михаил Кравцов", "Материал помогает замечать тревожные признаки и не выходить за границы компетенций педагога.", 5),
            ("Эльмира Кожахметова", "Сложная тема изложена корректно, спокойно и с опорой на практические протоколы.", 5),
            ("Роман Югай", "Полезный курс для школьной команды, хотелось бы ещё больше тренировочных сценариев.", 4),
            ("Людмила Соколова", "После курса стало понятнее, как фиксировать наблюдения и передавать информацию специалистам.", 5),
            ("Аскар Мухтаров", "Хорошо разобрана роль администрации и кризисной команды организации образования.", 5),
            ("Елена Ким", "Практические памятки пригодятся для внутреннего обучения педагогического коллектива.", 5),
        ],
    },
    "course-14": {
        "title": "Білім беру ұйымдарында зорлық-зомбылықтың алдын алудың және қауіпсіз білім беру ортасын құрудың заманауи тәсілдері",
        "subtitle": "Педагогтердің біліктілігін арттыру курстарының білім беру бағдарламасы",
        "reviews": [
            ("Айгүл Қайратқызы", "Зорлық-зомбылықтың алдын алу бойынша мектепке қажет нақты қадамдар ұсынылған.", 5),
            ("Нұрсұлтан Беков", "Қауіпсіз ортаны қалыптастыруда бүкіл педагогикалық команданың рөлі жақсы түсіндірілген.", 5),
            ("Раушан Әлімова", "Тәуекел белгілерін ерте анықтау және дұрыс әрекет ету алгоритмдері пайдалы болды.", 5),
            ("Мейрамгүл Оспанова", "Ата-аналармен және білім алушылармен сенімді қарым-қатынас құру тәсілдері ұнады.", 5),
            ("Санжар Төлеген", "Материал өзекті және түсінікті, практикалық тапсырмалар санын көбейтуге болады.", 4),
            ("Гүлназ Сейдахмет", "Мектептегі қауіпсіздік мәдениетін бағалау құралдарын жұмысымда қолданамын.", 5),
            ("Ерлан Жақыпов", "Алдын алу жоспарын командалық түрде құруға арналған үлгілер өте ыңғайлы.", 5),
            ("Ақбота Нұрғали", "Баланың құқығы мен психологиялық қауіпсіздігіне басымдық дұрыс берілген.", 5),
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
        # Keep every displayed date inside July in Kazakhstan's UTC+5 timezone.
        span_seconds = (30 * 24 + 18) * 60 * 60 - 1
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
            already_done = connection.execute(text("SELECT 1 FROM app_settings WHERE key = 'review_dates_july_2026_all_courses_v2'")).first()
            if not already_done:
                connection.execute(text("""
                    UPDATE reviews
                    SET created_at = TIMESTAMPTZ '2026-07-01 00:00:00+00'
                        + random() * (TIMESTAMPTZ '2026-07-31 18:59:59+00' - TIMESTAMPTZ '2026-07-01 00:00:00+00')
                """))
                connection.execute(text("INSERT INTO app_settings (key, value) VALUES ('review_dates_july_2026_all_courses_v2', 'done')"))
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
        july_start = datetime(2026, 7, 1, tzinfo=timezone.utc)
        july_span_seconds = (30 * 24 + 18) * 60 * 60 - 1
        review = Review(
            course_slug=course_slug,
            name=payload.name.strip(),
            comment=payload.comment.strip(),
            stars=payload.stars,
            created_at=july_start + timedelta(seconds=secrets.randbelow(july_span_seconds + 1)),
        )
        session.add(review)
        session.commit()
        session.refresh(review)
        return review
