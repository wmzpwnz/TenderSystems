from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.models.user import User
from app.api.v1 import tenders as tenders_module


SQLALCHEMY_DATABASE_URL = "sqlite:///./test_live_tender_detail.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def test_live_tender_detail_route_returns_eis_tender(monkeypatch):
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    try:
        user = User(
            email="live-tender@example.com",
            hashed_password=get_password_hash("testpass123"),
            full_name="Live Tender User",
            subscription_status="active",
            subscription_expires_at=datetime.utcnow() + timedelta(days=30),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        def override_get_db():
            try:
                yield db
            finally:
                pass

        async def fake_get_tender_details(tender_id: str):
            return {"id": tender_id}

        def fake_parse_tender_data(_detail_data):
            return {
                "number": "0338200002226000318",
                "title": "Тестовый live тендер",
                "status": "active",
            }

        app.dependency_overrides[get_db] = override_get_db
        monkeypatch.setattr(tenders_module.eis_client, "get_tender_details", fake_get_tender_details)
        monkeypatch.setattr(tenders_module.eis_client, "parse_tender_data", fake_parse_tender_data)

        token = create_access_token(user.id)
        client = TestClient(app)
        client.headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/v1/tenders/0338200002226000318")

        assert response.status_code == 200
        payload = response.json()
        assert payload["eis_id"] == "0338200002226000318"
        assert payload["title"] == "Тестовый live тендер"
        assert payload["status"] == "active"
    finally:
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(bind=engine)
