from fastapi import APIRouter, FastAPI

from src.router import router as router_user
from src.router_ws import router as ws_router

app = FastAPI(title="oauth2")

main_router = APIRouter(prefix="/oauth2/api/v1")

main_router.include_router(router_user)
main_router.include_router(ws_router)


app.include_router(main_router)
