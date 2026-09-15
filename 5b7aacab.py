from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="ANNAPURNA 360 API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BatchCreate(BaseModel):
    food_name: str = Field(min_length=1)
    quantity: float = Field(gt=0)
    unit: str = "meals"
    prepared_at: Optional[datetime] = None
    expiry_at: Optional[datetime] = None
    temperature_c: Optional[float] = None
    source: str = "manual"

class Batch(BatchCreate):
    id: str
    priority: int
    status: str
    created_at: datetime

class ForecastRequest(BaseModel):
    planned_quantity: float = Field(gt=0)
    expected_demand: float = Field(ge=0)

batches: List[Batch] = []

@app.get("/")
def root():
    return {"name": "ANNAPURNA 360 API", "status": "running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/batches", response_model=List[Batch])
def list_batches():
    return batches

@app.post("/api/batches", response_model=Batch, status_code=201)
def create_batch(payload: BatchCreate):
    surplus = max(payload.quantity - (payload.quantity * 0.8), 0)
    urgency = 50
    if payload.expiry_at:
        hours = (payload.expiry_at - datetime.now(timezone.utc)).total_seconds() / 3600
        urgency = 95 if hours <= 6 else 75 if hours <= 24 else 50
    priority = min(100, round(urgency * 0.7 + min(surplus / payload.quantity * 100, 100) * 0.3))
    item = Batch(
        **payload.model_dump(), id=f"ANN-{uuid4().hex[:8].upper()}",
        priority=priority, status="Rescue first" if priority >= 80 else "Partner review",
        created_at=datetime.now(timezone.utc)
    )
    batches.append(item)
    return item

@app.post("/api/forecast")
def forecast(payload: ForecastRequest):
    surplus = max(payload.planned_quantity - payload.expected_demand, 0)
    surplus_percent = round(surplus / payload.planned_quantity * 100, 2)
    recommendation = "Reduce preparation quantity" if surplus_percent >= 15 else "Preparation quantity is aligned"
    return {"surplus": surplus, "surplus_percent": surplus_percent, "recommendation": recommendation}

@app.get("/api/metrics")
def metrics():
    total = sum(item.quantity for item in batches)
    return {"total_batches": len(batches), "total_quantity": total, "rescued_quantity": 0, "prevented_quantity": 0}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend_main:app", host="0.0.0.0", port=8000, reload=True)
