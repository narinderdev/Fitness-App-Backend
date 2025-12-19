from types import SimpleNamespace

import pytest

from app import main
from app.database import SessionLocal
from app.models.program import Program, ProgramDay
from app.services.auth_middleware import get_current_user


def _dummy_user():
    return SimpleNamespace(id=1, email="test@example.com", is_admin=False, is_active=True)


def _seed_program(session: SessionLocal, slug: str = "test-plan", duration: int = 5) -> Program:
    session.query(ProgramDay).delete()
    session.query(Program).delete()
    program = Program(
        slug=slug,
        title="Test Program",
        subtitle="Demo subtitle",
        description="Demo description",
        duration_days=duration,
        workouts_per_week=5,
        rest_days_per_week=2,
        level="Beginner",
        access_level="free",
        cta_label="Start",
        hero_image_url=None,
        cover_image_url=None,
        is_active=True,
        is_featured=True,
    )
    session.add(program)
    session.flush()
    for index in range(duration):
        session.add(
            ProgramDay(
                program_id=program.id,
                day_number=index + 1,
                title=f"Day {index + 1}",
                focus="Strength",
                description="Demo day",
                is_rest_day=index % 7 in (5, 6),
                workout_summary="Summary",
                duration_minutes=25,
            )
        )
    session.commit()
    return program


@pytest.fixture(autouse=False)
def override_user():
    main.app.dependency_overrides[get_current_user] = _dummy_user
    yield
    main.app.dependency_overrides.pop(get_current_user, None)


def test_list_programs_returns_seeded_programs(client, override_user):
    session = SessionLocal()
    try:
        program = _seed_program(session)
        seeded = {"slug": program.slug, "title": program.title}
    finally:
        session.close()

    response = client.get("/programs")
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["count"] == 1
    returned = payload["programs"][0]
    assert returned["slug"] == seeded["slug"]
    assert returned["title"] == seeded["title"]
    assert "preview_days" in returned
    assert returned["requires_payment"] is False


def test_program_detail_returns_full_schedule(client, override_user):
    session = SessionLocal()
    try:
        program = _seed_program(session, slug="detail-plan", duration=3)
        slug = program.slug
    finally:
        session.close()

    response = client.get(f"/programs/{slug}")
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["program"]["slug"] == program.slug
    assert len(payload["days"]) == 3
    assert payload["timeline"]["total_days"] == 3
    assert payload["timeline"]["rest_days"] >= 0
