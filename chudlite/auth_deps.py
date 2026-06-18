from fastapi import Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_session
from models import User


class LoginRequired(Exception):
    pass


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise LoginRequired()
    user = await db.get(User, user_id)
    if not user:
        request.session.clear()
        raise LoginRequired()
    return user
