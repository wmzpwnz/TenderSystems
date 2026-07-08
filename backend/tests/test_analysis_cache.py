from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1 import analysis as analysis_module
from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.analysis import Analysis
from app.models.company_profile import CompanyProfile
from app.models.tender import Tender
from app.models.user import User


def _active_user(email: str) -> User:
    return User(
        email=email,
        hashed_password="test",
        full_name=email,
        subscription_status="active",
        subscription_expires_at=datetime.utcnow() + timedelta(days=30),
    )


@pytest.fixture
def db(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'analysis_cache.db'}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def users(db):
    user_a = _active_user("analysis-a@example.com")
    user_b = _active_user("analysis-b@example.com")
    db.add_all([user_a, user_b])
    db.commit()
    db.refresh(user_a)
    db.refresh(user_b)
    return user_a, user_b


@pytest.fixture
def tender(db):
    tender = Tender(
        eis_id="cache-eis-1",
        number="562",
        title="Cached tender",
        status="active",
        okpd2_codes=["25.11"],
        customer_region="Москва",
        requirements={"licenses": ["ФСБ"]},
    )
    db.add(tender)
    db.commit()
    db.refresh(tender)
    return tender


def _auth_headers(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def _quick_ai_response(summary: str = "cached summary") -> dict:
    return {
        "summary": summary,
        "basic_requirements": {"required": True},
        "application_deadline": None,
        "delivery_deadline": None,
        "delivery_terms": {},
        "quick_assessment": {
            "complexity": "medium",
            "recommendation": "ok",
        },
        "financial_info": {},
    }


def _mock_quick_dependencies(monkeypatch, documents):
    calls = {"analyze": 0}

    async def fake_get_tender_documents(_eis_id):
        return documents() if callable(documents) else documents

    async def fake_download_document(_url):
        return b"document-content"

    async def fake_extract_text(_content, filename):
        return f"text from {filename}"

    async def fake_analyze_tender_documents(**_kwargs):
        calls["analyze"] += 1
        return _quick_ai_response(summary=f"summary {calls['analyze']}")

    monkeypatch.setattr(analysis_module.eis_client, "get_tender_documents", fake_get_tender_documents)
    monkeypatch.setattr(analysis_module.eis_client, "download_document", fake_download_document)
    monkeypatch.setattr(analysis_module.document_processor, "extract_text", fake_extract_text)
    monkeypatch.setattr(
        analysis_module.deepseek_client,
        "analyze_tender_documents",
        fake_analyze_tender_documents,
    )

    return calls


def test_quick_analysis_cache_is_shared_between_users(client, db, users, tender, monkeypatch):
    user_a, user_b = users
    documents = [{"fileName": "tz.pdf", "url": "https://example.test/tz.pdf", "size": 100}]
    calls = _mock_quick_dependencies(monkeypatch, documents)

    first = client.post(
        f"/api/v1/analysis/quick/{tender.id}",
        headers=_auth_headers(user_a),
    )
    second = client.post(
        f"/api/v1/analysis/quick/{tender.id}",
        headers=_auth_headers(user_b),
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert calls["analyze"] == 1

    analyses = db.query(Analysis).filter(Analysis.tender_id == tender.id).all()
    assert len(analyses) == 1
    assert analyses[0].user_id == user_a.id


def test_start_analysis_endpoint_reuses_shared_cache_between_users(
    client,
    db,
    users,
    tender,
    monkeypatch,
):
    user_a, user_b = users
    documents = [{"fileName": "tz.pdf", "url": "https://example.test/tz.pdf", "size": 100}]
    tender.documents_data = documents
    db.commit()
    calls = {"deepseek": 0}

    def fake_analyze_tender_task(tender_id: int, user_id=None):
        calls["deepseek"] += 1
        documents_hash, source_documents_count = analysis_module._documents_fingerprint(documents)
        analysis = Analysis(
            tender_id=tender_id,
            user_id=user_id,
            analysis_type="quick",
            summary="cached background summary",
            risks={"level": "medium"},
            risk_level="medium",
            margin_analysis={"profitability": "ok"},
            win_probability=50,
            documents_analyzed=[{
                "filename": "tz.pdf",
                "size": 100,
                "text_length": 100,
                "has_text": True,
            }],
            documents_hash=documents_hash,
            source_documents_count=source_documents_count,
            raw_ai_response={},
        )
        db.add(analysis)
        db.commit()

    monkeypatch.setattr(analysis_module, "analyze_tender_task", fake_analyze_tender_task)

    first = client.post(
        f"/api/v1/analysis/{tender.id}",
        headers=_auth_headers(user_a),
    )
    second = client.post(
        f"/api/v1/analysis/{tender.id}",
        headers=_auth_headers(user_b),
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert calls["deepseek"] == 1
    assert second.json()["summary"] == "cached background summary"

    analyses = db.query(Analysis).filter(Analysis.tender_id == tender.id).all()
    assert len(analyses) == 1
    assert analyses[0].user_id == user_a.id


def test_cached_response_recalculates_win_probability_without_mutating_row(
    client,
    db,
    users,
    tender,
    monkeypatch,
):
    user_a, user_b = users
    documents = [{"fileName": "tz.pdf", "url": "https://example.test/tz.pdf", "size": 100}]
    _mock_quick_dependencies(monkeypatch, documents)

    db.add(
        CompanyProfile(
            user_id=user_a.id,
            name="Matching company",
            region="Москва",
            okpd2_codes=["25.11"],
            licenses=["ФСБ"],
        )
    )
    db.add(
        CompanyProfile(
            user_id=user_b.id,
            name="Non matching company",
            region="Санкт-Петербург",
            okpd2_codes=["31.01"],
            licenses=[],
        )
    )
    db.commit()

    first = client.post(
        f"/api/v1/analysis/quick/{tender.id}",
        headers=_auth_headers(user_a),
    )
    second = client.post(
        f"/api/v1/analysis/quick/{tender.id}",
        headers=_auth_headers(user_b),
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert float(first.json()["win_probability"]) == 100.0
    assert float(second.json()["win_probability"]) == 50.0

    analysis = db.query(Analysis).filter(Analysis.tender_id == tender.id).one()
    db.refresh(analysis)
    assert float(analysis.win_probability) == 100.0


def test_quick_analysis_cache_invalidates_when_document_set_changes(
    client,
    db,
    users,
    tender,
    monkeypatch,
):
    user_a, user_b = users
    current_documents = [
        {"fileName": "tz.pdf", "url": "https://example.test/tz.pdf", "size": 100}
    ]
    calls = _mock_quick_dependencies(monkeypatch, lambda: current_documents)

    first = client.post(
        f"/api/v1/analysis/quick/{tender.id}",
        headers=_auth_headers(user_a),
    )
    assert first.status_code == 200

    current_documents = [
        {"fileName": "tz.pdf", "url": "https://example.test/tz.pdf", "size": 100},
        {"fileName": "spec.pdf", "url": "https://example.test/spec.pdf", "size": 200},
    ]
    tender.documents_data = current_documents
    db.commit()

    second = client.post(
        f"/api/v1/analysis/quick/{tender.id}",
        headers=_auth_headers(user_b),
    )

    assert second.status_code == 200
    assert calls["analyze"] == 2
    assert db.query(Analysis).filter(Analysis.tender_id == tender.id).count() == 2
