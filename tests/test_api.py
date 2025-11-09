"""API tests for AgentPay FastAPI layer."""

import pytest
from fastapi.testclient import TestClient
from agentpay.api.app import app


@pytest.fixture
def client():
    # Ensure clean SDK state before each test
    app.state.sdk.clear_all()
    return TestClient(app)


class TestAgents:
    def test_register_and_get_agent(self, client: TestClient):
        r = client.post("/v1/agents", json={"agent_id": "alice", "metadata": {"name": "Alice"}})
        assert r.status_code == 200
        body = r.json()
        assert body["agent_id"] == "alice"
        assert body["balance"] == 0

        r2 = client.get("/v1/agents/alice")
        assert r2.status_code == 200
        assert r2.json()["agent_id"] == "alice"

    def test_list_agents(self, client: TestClient):
        client.post("/v1/agents", json={"agent_id": "alice"})
        client.post("/v1/agents", json={"agent_id": "bob"})
        r = client.get("/v1/agents")
        assert r.status_code == 200
        agent_ids = {a["agent_id"] for a in r.json()}
        assert agent_ids == {"alice", "bob"}

    def test_update_policy(self, client: TestClient):
        client.post("/v1/agents", json={"agent_id": "alice"})
        r = client.patch("/v1/agents/alice/policy", json={"paused": True, "max_per_transaction": 5000})
        assert r.status_code == 200
        data = r.json()
        assert data["paused"] is True


class TestWallet:
    def test_fund_and_get_wallet(self, client: TestClient):
        client.post("/v1/agents", json={"agent_id": "alice"})
        r = client.post("/v1/agents/alice/fund", json={"amount": 10000, "memo": "Initial"})
        assert r.status_code == 200
        data = r.json()
        assert data["balance"] == 10000

        r2 = client.get("/v1/agents/alice/wallet")
        assert r2.status_code == 200
        assert r2.json()["total"] == 10000


class TestPayments:
    def test_make_payment_and_status(self, client: TestClient):
        client.post("/v1/agents", json={"agent_id": "alice"})
        client.post("/v1/agents", json={"agent_id": "bob"})
        client.post("/v1/agents/alice/fund", json={"amount": 10000})

        r = client.post(
            "/v1/payments",
            json={"from_agent": "alice", "to_agent": "bob", "amount": 5000, "memo": "Test"},
        )
        assert r.status_code == 200
        pay = r.json()
        assert pay["success"] is True
        intent_id = pay["intent_id"]

        status = client.get(f"/v1/payments/{intent_id}")
        assert status.status_code == 200
        assert status.json()["status"] == "completed"

        # Balances
        a = client.get("/v1/agents/alice/wallet").json()
        b = client.get("/v1/agents/bob/wallet").json()
        assert a["balance"] == 5000
        assert b["balance"] == 5000


class TestEscrow:
    def test_create_release_escrow(self, client: TestClient):
        client.post("/v1/agents", json={"agent_id": "alice"})
        client.post("/v1/agents", json={"agent_id": "bob"})
        client.post("/v1/agents/alice/fund", json={"amount": 10000})

        # Create escrow
        r = client.post(
            "/v1/escrows",
            json={"from_agent": "alice", "to_agent": "bob", "amount": 3000},
        )
        assert r.status_code == 200
        esc = r.json()
        assert esc["success"] is True
        escrow_id = esc["escrow_id"]

        # Release escrow
        r2 = client.post(f"/v1/escrows/{escrow_id}/release")
        assert r2.status_code == 200
        assert r2.json()["status"] == "released"

        # Balances
        a = client.get("/v1/agents/alice/wallet").json()
        b = client.get("/v1/agents/bob/wallet").json()
        assert a["balance"] == 7000
        assert a["hold"] == 0
        assert b["balance"] == 3000

    def test_create_cancel_escrow(self, client: TestClient):
        client.post("/v1/agents", json={"agent_id": "alice"})
        client.post("/v1/agents", json={"agent_id": "bob"})
        client.post("/v1/agents/alice/fund", json={"amount": 5000})

        r = client.post(
            "/v1/escrows",
            json={"from_agent": "alice", "to_agent": "bob", "amount": 2000},
        )
        escrow_id = r.json()["escrow_id"]

        r2 = client.post(f"/v1/escrows/{escrow_id}/cancel")
        assert r2.status_code == 200
        assert r2.json()["status"] == "cancelled"

        a = client.get("/v1/agents/alice/wallet").json()
        assert a["balance"] == 5000
        assert a["hold"] == 0


class TestHistory:
    def test_agent_ledger_and_reference(self, client: TestClient):
        client.post("/v1/agents", json={"agent_id": "alice"})
        client.post("/v1/agents", json={"agent_id": "bob"})
        client.post("/v1/agents/alice/fund", json={"amount": 10000})
        pay = client.post(
            "/v1/payments",
            json={"from_agent": "alice", "to_agent": "bob", "amount": 2500},
        ).json()
        intent_id = pay["intent_id"]

        # Ledger by agent
        ledger = client.get("/v1/agents/alice/ledger").json()
        assert len(ledger) == 2
        assert any(e["entry_type"] == "payment" for e in ledger)

        # By reference
        entries = client.get(f"/v1/transactions/{intent_id}").json()
        assert len(entries) == 2
        assert sum(e["delta_amount"] for e in entries) == 0