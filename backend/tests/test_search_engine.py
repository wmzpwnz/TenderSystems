"""
Unit тесты для SearchEngine
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.services.search_engine import SearchEngine
from app.models.tender import Tender
from app.core.database import Base

# Тестовая БД в памяти
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Создаем тестовую БД для каждого теста"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_tenders(db):
    """Создаем тестовые тендеры"""
    tenders = [
        Tender(
            eis_id="test-001",
            title="Поставка медицинского оборудования",
            description="Поставка медицинского оборудования для больницы",
            customer_name="ГБУЗ Городская больница №1",
            customer_region="Москва",
            initial_price=1000000.00,
            status="active"
        ),
        Tender(
            eis_id="test-002",
            title="Ремонт здания школы",
            description="Капитальный ремонт здания школы",
            customer_name="Департамент образования",
            customer_region="Санкт-Петербург",
            initial_price=5000000.00,
            status="active"
        ),
    ]
    for tender in tenders:
        db.add(tender)
    db.commit()
    return tenders


def test_search_by_query(db, sample_tenders):
    """Тест поиска по запросу"""
    engine = SearchEngine(db)
    result = engine.search(query="медицин")
    
    assert result["total"] >= 1
    assert any("медицин" in t.title.lower() for t in result["items"])


def test_search_by_region(db, sample_tenders):
    """Тест поиска по региону"""
    engine = SearchEngine(db)
    result = engine.search(regions=["Москва"])
    
    assert result["total"] >= 1
    assert all(t.customer_region == "Москва" for t in result["items"])


def test_search_by_price_range(db, sample_tenders):
    """Тест поиска по диапазону цен"""
    engine = SearchEngine(db)
    result = engine.search(price_from=2000000, price_to=6000000)
    
    assert result["total"] >= 1
    for tender in result["items"]:
        if tender.initial_price:
            assert 2000000 <= float(tender.initial_price) <= 6000000


def test_search_empty_result(db):
    """Тест поиска без результатов"""
    engine = SearchEngine(db)
    result = engine.search(query="несуществующий запрос xyz123")
    
    assert result["total"] == 0
    assert len(result["items"]) == 0




