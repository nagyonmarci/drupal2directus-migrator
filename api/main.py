from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import connections, jobs

app = FastAPI(
    title="Drupal → Directus Migrator API",
    description="HTTP API to manage migration connections and jobs.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(connections.router)
app.include_router(jobs.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
