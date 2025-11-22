# Initial CoreBox CRM backend entrypoint – minimal FastAPI app.

from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"app": "CoreBox CRM backend", "status": "ok"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
