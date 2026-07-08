from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1 import tenders as tenders_module
from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.analysis import Analysis
from app.models.tender import Tender
from app.models.user import User


def test_tender_search_includes_latest_analysis_verdict_fields(monkeypatch, tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'tender_list_analysis.db'}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    try:
        user = User(
            email="dashboard@example.com",
            hashed_password="test",
            full_name="Dashboard User",
            subscription_status="active",
            subscription_expires_at=datetime.utcnow() + timedelta(days=30),
        )
        tender = Tender(
            eis_id="eis-verdict-1",
            number="562",
            title="Dashboard tender",
            status="active",
        )
        db.add_all([user, tender])
        db.commit()
        db.refresh(user)
        db.refresh(tender)

        db.add(
            Analysis(
                tender_id=tender.id,
                user_id=user.id,
                analysis_type="quick",
                summary="AI summary for dashboard",
                risk_level="high",
                margin_analysis={"profitability": "низкая"},
                win_probability=42,
            )
        )
        db.commit()

        def override_get_db():
            try:
                yield db
            finally:
                pass

        async def fake_search_tenders(_filters):
            return {
                "items": [{
                    "id": tender.id,
                    "eis_id": tender.eis_id,
                    "number": tender.number,
                    "title": tender.title,
                    "description": None,
                    "customer_name": None,
                    "customer_inn": None,
                    "customer_region": None,
                    "initial_price": None,
                    "currency": "RUB",
                    "guarantee_amount": None,
                    "contract_guarantee": None,
                    "publication_date": None,
                    "application_deadline": None,
                    "contract_deadline": None,
                    "status": tender.status,
                    "procedure_type": None,
                    "documents_url": None,
                    "documents_data": None,
                    "okpd2_codes": None,
                    "requirements": None,
                    "platform": None,
                    "prepayment_type": None,
                    "preferences": None,
                    "is_analyzed": False,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                }],
                "total": 1,
                "page": 1,
                "page_size": 20,
                "pages": 1,
            }

        app.dependency_overrides[get_db] = override_get_db
        monkeypatch.setattr(tenders_module.eis_client, "search_tenders", fake_search_tenders)

        client = TestClient(app)
        response = client.post(
            "/api/v1/tenders/search",
            json={"page": 1, "page_size": 20},
            headers={"Authorization": f"Bearer {create_access_token(user.id)}"},
        )

        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["is_analyzed"] is True
        assert item["analysis_risk_level"] == "high"
        assert item["analysis_summary"] == "AI summary for dashboard"
        assert item["analysis_margin_analysis"] == {"profitability": "низкая"}
    finally:
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(bind=engine)
