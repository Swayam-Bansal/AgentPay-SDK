"""FastAPI application for AgentPay HTTP API."""

from fastapi import FastAPI
from agentpay.sdk import AgentPaySDK
from agentpay.api.routes import router

# Singleton SDK instance for the process
sdk = AgentPaySDK()

app = FastAPI(
    title="AgentPay SDK API",
    version="0.1.0",
    description="HTTP API for AgentPay – payment infrastructure for AI agents",
)

# Inject SDK into app state for route access
app.state.sdk = sdk

# Mount routes
app.include_router(router, prefix="/v1")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": app.version}

