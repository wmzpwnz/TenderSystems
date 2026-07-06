"""
Unit тесты для Company Profile API
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import Base, get_db
from app.models.user import User
from app.models.company_profile import CompanyProfile
from app.core.security import get_password_hash

# Тестовая БД
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Создаем тестовую БД"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user(db):
    """Создаем тестового пользователя"""
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Test User"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def client(db, test_user):
    """Создаем тестовый клиент с авторизацией"""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Получаем токен для авторизации
    from app.core.security import create_access_token
    token = create_access_token(test_user.id)
    
    client = TestClient(app)
    client.headers = {"Authorization": f"Bearer {token}"}
    
    yield client
    
    app.dependency_overrides.clear()


def test_create_company_profile(client, test_user):
    """Тест создания профиля компании"""
    profile_data = {
        "name": "Тестовая компания",
        "inn": "1234567890",
        "region": "Москва",
        "okpd2_codes": ["25.11", "25.12"]
    }
    
    response = client.post("/api/v1/profile", json=profile_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == profile_data["name"]
    assert data["inn"] == profile_data["inn"]


def test_get_company_profile(client, test_user, db):
    """Тест получения профиля компании"""
    # Сначала создаем профиль
    profile = CompanyProfile(
        user_id=test_user.id,
        name="Тестовая компания",
        inn="1234567890"
    )
    db.add(profile)
    db.commit()
    
    # Получаем профиль
    response = client.get("/api/v1/profile")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Тестовая компания"


def test_update_company_profile(client, test_user, db):
    """Тест обновления профиля компании"""
    # Создаем профиль
    profile = CompanyProfile(
        user_id=test_user.id,
        name="Старое название",
        inn="1234567890"
    )
    db.add(profile)
    db.commit()
    
    # Обновляем
    update_data = {"name": "Новое название"}
    response = client.post("/api/v1/profile", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Новое название"




