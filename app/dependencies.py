from app.database import get_db_session


async def get_db():
    async for session in get_db_session():
        yield session
