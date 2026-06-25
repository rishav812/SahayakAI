from fastapi import FastAPI
from app.routes import router

app = FastAPI()


@app.get("/")
def root():
    return {"status": "ok"}


app.include_router(router)
