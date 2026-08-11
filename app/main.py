from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Item


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Fluid AI DevOps Challenge",
    lifespan=lifespan,
)

Instrumentator().instrument(app).expose(app)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "not ready"},
        )


@app.get("/items")
def get_items(db: Session = Depends(get_db)):
    return db.query(Item).all()


@app.post("/items")
def create_item(
    name: str,
    db: Session = Depends(get_db),
):
    item = Item(name=name)

    db.add(item)
    db.commit()
    db.refresh(item)

    return item
