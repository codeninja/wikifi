from fastapi import FastAPI

app = FastAPI(title="Wikifi")

@app.get("/health")
def health():
    return {"status": "ok"}
