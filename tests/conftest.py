import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data_engine import HMDataEngine
from src.orchestrator import FashopOrchestrator
from src.agents.critic_guardrail import CriticGuardrailAgent

@pytest.fixture(scope="session")
def db():
    return HMDataEngine()

@pytest.fixture(scope="session")
def orchestrator(db):
    return FashopOrchestrator(data_engine=db)

@pytest.fixture(scope="session")
def critic():
    return CriticGuardrailAgent()

@pytest.fixture(scope="session")
def customer_id(db):
    return db.get_random_active_customer()

