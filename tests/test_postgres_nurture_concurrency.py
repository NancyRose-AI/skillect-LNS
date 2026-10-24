import os
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch

os.environ.setdefault("DB_USERNAME", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")

from fastapi.testclient import TestClient
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from models import Lead, NurtureContentIdentity, NurtureMessage
from ai.nurture_service import get_current_time


POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_DATABASE_URL")
ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(
    POSTGRES_TEST_URL,
    "Set POSTGRES_TEST_DATABASE_URL to a disposable PostgreSQL database",
)
class PostgresNurtureConcurrencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parsed_url = make_url(POSTGRES_TEST_URL)
        if not parsed_url.database or "test" not in parsed_url.database.lower():
            raise RuntimeError(
                "POSTGRES_TEST_DATABASE_URL database name must contain 'test'"
            )

        cls.admin_engine = create_engine(POSTGRES_TEST_URL, pool_pre_ping=True)
        cls.schema_name = f"nurture_test_{uuid4().hex}"
        with cls.admin_engine.begin() as connection:
            connection.execute(
                text(f'CREATE SCHEMA "{cls.schema_name}"')
            )

        alembic_config = Config(str(ROOT / "alembic.ini"))
        postgres_schema_url = parsed_url.update_query_dict(
            {"options": [f"-csearch_path={cls.schema_name}"]}
        )
        alembic_config.set_main_option(
            "sqlalchemy.url",
            str(postgres_schema_url).replace("%", "%%"),
        )
        command.upgrade(alembic_config, "head")

        cls.engine = create_engine(
            POSTGRES_TEST_URL,
            pool_pre_ping=True,
            connect_args={
                "options": f"-csearch_path={cls.schema_name}",
            },
        )
        cls.session_factory = sessionmaker(
            bind=cls.engine,
            expire_on_commit=False,
        )

        from ai import main as ai_api

        cls.api = ai_api

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()
        with cls.admin_engine.begin() as connection:
            connection.execute(
                text(f'DROP SCHEMA "{cls.schema_name}" CASCADE')
            )
        cls.admin_engine.dispose()

    def setUp(self):
        self.email = f"concurrent-{uuid4().hex}@example.test"
        with self.session_factory() as session:
            lead = Lead(
                name="Concurrency Test Lead",
                phone="1234567890",
                email=self.email,
                source="Test",
                status="new",
                ai_temperature="cold",
                interest="AWS Cloud Engineering",
            )
            session.add(lead)
            session.commit()
            self.lead_id = lead.id

        def override_get_db():
            with self.session_factory() as session:
                yield session

        self.api.app.dependency_overrides[self.api.get_db] = override_get_db
        self.client = TestClient(self.api.app)
        self.addCleanup(self.client.close)
        self.addCleanup(
            lambda: self.api.app.dependency_overrides.pop(
                self.api.get_db,
                None,
            )
        )

    def test_concurrent_api_requests_generate_only_one_same_day_nurture(self):
        barrier = threading.Barrier(2)

        def post_nurture():
            barrier.wait(timeout=10)
            with TestClient(self.api.app) as client:
                return client.post(f"/ai/nurture/{self.lead_id}")

        with patch(
            "ai.nurture_service.decide_engagement",
            return_value={
                "eligible": True,
                "reason": "engagement_allowed",
                "content_type": "educational",
                "topic": "AWS Cloud Engineering",
            },
        ):
            with ThreadPoolExecutor(max_workers=2) as executor:
                responses = list(executor.map(lambda _: post_nurture(), range(2)))

        self.assertEqual([response.status_code for response in responses], [200, 200])
        payloads = [response.json() for response in responses]
        self.assertEqual(
            sum(bool(payload.get("ready_to_send")) for payload in payloads),
            1,
        )
        self.assertEqual(
            sum(
                payload.get("reason") == "already_generated_today"
                for payload in payloads
            ),
            1,
        )

        with self.session_factory() as session:
            nurtures = (
                session.query(NurtureMessage)
                .filter(NurtureMessage.lead_id == self.lead_id)
                .all()
            )
            identities = (
                session.query(NurtureContentIdentity)
                .filter(NurtureContentIdentity.lead_id == self.lead_id)
                .all()
            )

        self.assertEqual(len(nurtures), 1)
        self.assertTrue(identities)

    def test_identity_records_persist_across_postgresql_sessions(self):
        with self.session_factory() as session:
            lead = Lead(
                name="Persistence Test Lead",
                phone="1234567890",
                email=f"persistence-{uuid4().hex}@example.test",
                source="Test",
                status="new",
                ai_temperature="cold",
            )
            session.add(lead)
            session.flush()
            nurture = NurtureMessage(
                lead_id=lead.id,
                message="Approved source content",
                content_type="industry_update",
                topic="AWS Cloud Engineering",
                stage=1,
                status="generated",
            )
            session.add(nurture)
            session.flush()
            session.add_all(
                [
                    NurtureContentIdentity(
                        lead_id=lead.id,
                        nurture_id=nurture.id,
                        identity=identity,
                    )
                    for identity in (
                        "article:id:postgres-article",
                        "image:id:postgres-image",
                        "batch:id:postgres-batch",
                    )
                ]
            )
            lead_id = lead.id
            session.commit()

        with self.session_factory() as verification_session:
            saved = {
                row.identity
                for row in verification_session.query(NurtureContentIdentity)
                .filter(NurtureContentIdentity.lead_id == lead_id)
                .all()
            }

        self.assertEqual(
            saved,
            {
                "article:id:postgres-article",
                "image:id:postgres-image",
                "batch:id:postgres-batch",
            },
        )


if __name__ == "__main__":
    unittest.main()
