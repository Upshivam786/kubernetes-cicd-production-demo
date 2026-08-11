from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Item


app = FastAPI(
    title="Fluid AI DevOps Challenge",
)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


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
