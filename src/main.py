from contextlib import asynccontextmanager
from src.config.redis_client import client as redis_client
from starlette.middleware.sessions import SessionMiddleware
from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from src.config.http import limiter, unexpected
from src.api.v1 import router
from src.config.env import env, production
from src.db import init_db
from src.config.http import too_many_request, allowed_origins


@asynccontextmanager
async def lifespan(app: FastAPI):
    # runs on startup
    try:
        await init_db()
        pong = await redis_client.ping()  # type: ignore
        print(pong)
        app.state.redis = redis_client
        yield
    except Exception:
        print("startup failed")
        raise
    finally:
        # runs on shutdown
        await app.state.redis.aclose()


app = FastAPI(lifespan=lifespan)


app.state.limit = limiter


# required for oauth2
app.add_middleware(
    SessionMiddleware,
    same_site="lax",
    secret_key=env.starlette_session_secret,
    https_only=False,
)

if production:
    app.add_middleware(HTTPSRedirectMiddleware)


app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router=router)


app.add_exception_handler(RateLimitExceeded, too_many_request)  # type:ignore

if production:
    app.add_exception_handler(Exception, unexpected)
