import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.api.api import api_router
from app.api.triggers import trigger_router

# Initialize Sentry (User must provide SENTRY_DSN in env vars)
sentry_sdk.init(
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
)

# Initialize Rate Limiter
limiter = Limiter(key_func=get_remote_address)

# Create the main FastAPI application
app = FastAPI(title="AIF Scraper Backend", version="2.0.0")

# Setup Rate Limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Setup CORS (Strictly locked down to frontend URL in production, allow localhost for dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://aif-tracker.vercel.app", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the API routers
app.include_router(api_router)
app.include_router(trigger_router, prefix="/api")

@app.get("/health")
@limiter.limit("5/minute")
def health_check(request):
    """Health check endpoint for Uptime monitoring."""
    return {"status": "healthy"}
