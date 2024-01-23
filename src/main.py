from fastapi import APIRouter, FastAPI

# write title for your application
app = FastAPI(title="")

# write prefix for your application
main_router = APIRouter(prefix="")

app.include_router(main_router)
