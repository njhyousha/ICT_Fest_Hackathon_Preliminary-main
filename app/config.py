"""Application configuration.

Values are read from the environment so the same image can run in different
deployments. Sensible defaults are provided for local development.
"""
import os

# Secrets / crypto
JWT_SECRET = os.getenv("JWT_SECRET", "cowork-dev-secret-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# Token expiry (read from env as integers)
try:
	ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
except ValueError:
	ACCESS_TOKEN_EXPIRE_MINUTES = 15

try:
	REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
except ValueError:
	REFRESH_TOKEN_EXPIRE_DAYS = 7

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cowork.db")
