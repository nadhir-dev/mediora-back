from contextlib import asynccontextmanager
from starlette.middleware.sessions import SessionMiddleware
from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded
from fastapi.middleware.cors import CORSMiddleware
from src.config.http import limiter, unexpected
from src.api.v1 import router
from src.config.env import env, production
from src.db import init_db
from src.config.http import too_many_request


@asynccontextmanager
async def lifespan(app: FastAPI):
    # runs on startup
    await init_db()
    yield
    # runs on shutdown


app = FastAPI(lifespan=lifespan)


app.state.limit = limiter


# required for oauth2
app.add_middleware(
    SessionMiddleware,
    same_site="lax",
    secret_key=env.starlette_session_secret,
    https_only=False,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router=router)


app.add_exception_handler(RateLimitExceeded, too_many_request)  # type:ignore

if production:
    app.add_exception_handler(Exception, unexpected)
