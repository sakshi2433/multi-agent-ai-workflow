#!/usr/bin/env python3
"""Initialize the database for the Multi-Agent AI Workflow system."""
import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

# Get database URL
database_url = "postgresql+asyncpg://user:password@localhost:5432/multi_agent_db"
if sys.argv[1:]:
    database_url = sys.argv[1]

engine = create_async_engine(database_url)

async def init_database():
    """Initialize database tables."""
    from app.models import Base
    
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    print("Database tables created successfully!")
    
    # Verify tables
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'"))
        tables = result.scalars().all()
        print(f"Tables created: {tables}")

async def main():
    await init_database()

if __name__ == "__main__":
    asyncio.run(main())