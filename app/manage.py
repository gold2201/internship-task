import asyncio
import re
import uuid
from getpass import getpass

import click
from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.session import db_manager
from app.models.db_models import User


async def createsuperuser() -> None:
    session = None

    try:
        click.echo("Создание суперпользователя")

        async for session in db_manager.get_async_session():
            while True:
                email = await asyncio.to_thread(input, "Email: ")
                email = email.strip()

                if not email:
                    click.echo("Email не может быть пустым")
                    continue
                if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                    click.echo("Введите корректный email")
                    continue

                result = await session.execute(select(User).where(User.email == email))
                existing_user = result.scalars().first()

                if existing_user:
                    click.echo("Пользователь с таким email уже существует")
                    continue
                break

            while True:
                password = getpass("Пароль: ")
                if len(password) < 8:
                    click.echo("Пароль должен быть минимум 8 символов")
                    continue

                password2 = getpass("Пароль (еще раз): ")
                if password != password2:
                    click.echo("Пароли не совпадают")
                    continue
                break

            user = User(
                id=uuid.uuid4(),
                email=email,
                hashed_password=get_password_hash(password),
                is_superuser=True,
                status="ACTIVE",
            )

            session.add(user)
            await session.commit()

            click.echo("Суперпользователь создан успешно!")
            click.echo(f"  Email: {user.email}")
            click.echo(f"  ID: {user.id}")
            break

    except Exception as e:
        await session.rollback()
        click.echo(f"Oшибка: {e!s}")


if __name__ == "__main__":
    asyncio.run(createsuperuser())