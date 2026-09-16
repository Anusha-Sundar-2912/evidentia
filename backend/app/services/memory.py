import json
from uuid import uuid4

import redis

from app.core.config import settings


_redis_client = None

MAX_HISTORY_MESSAGES = 10
CONVERSATION_TTL = 60 * 60 * 24


def get_redis_client():
    global _redis_client

    if _redis_client is None:
        _redis_client = (
            redis.Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
        )

    return _redis_client


def create_conversation_id() -> str:
    return str(
        uuid4()
    )


def get_conversation_key(
    conversation_id: str,
) -> str:
    return (
        f"evidentia:conversation:"
        f"{conversation_id}"
    )


def get_history(
    conversation_id: str,
) -> list[dict]:
    """
    Retrieve conversation history.

    Redis failure is non-fatal: Evidentia simply
    behaves as if no conversational history exists.
    """

    try:
        client = get_redis_client()

        key = get_conversation_key(
            conversation_id
        )

        messages = client.lrange(
            key,
            -MAX_HISTORY_MESSAGES,
            -1,
        )

    except redis.RedisError as exc:
        print(
            "Redis history unavailable: "
            f"{exc}"
        )
        return []

    history = []

    for message in messages:
        try:
            history.append(
                json.loads(
                    message
                )
            )
        except (
            json.JSONDecodeError,
            TypeError,
        ):
            continue

    return history


def add_message(
    conversation_id: str,
    role: str,
    content: str,
) -> bool:
    """
    Store one conversation message.

    Returns False rather than failing the RAG request
    when Redis is unavailable.
    """

    if role not in {
        "user",
        "assistant",
    }:
        raise ValueError(
            "Role must be 'user' or 'assistant'."
        )

    try:
        client = get_redis_client()

        key = get_conversation_key(
            conversation_id
        )

        message = {
            "role": role,
            "content": content,
        }

        client.rpush(
            key,
            json.dumps(
                message
            ),
        )

        client.ltrim(
            key,
            -MAX_HISTORY_MESSAGES,
            -1,
        )

        client.expire(
            key,
            CONVERSATION_TTL,
        )

        return True

    except redis.RedisError as exc:
        print(
            "Redis message write unavailable: "
            f"{exc}"
        )
        return False


def save_turn(
    conversation_id: str,
    user_message: str,
    assistant_message: str,
) -> bool:
    """
    Store a complete turn without allowing Redis
    failure to break answer delivery.
    """

    user_saved = add_message(
        conversation_id=conversation_id,
        role="user",
        content=user_message,
    )

    assistant_saved = add_message(
        conversation_id=conversation_id,
        role="assistant",
        content=assistant_message,
    )

    return (
        user_saved
        and assistant_saved
    )


def clear_history(
    conversation_id: str,
) -> bool:
    try:
        client = get_redis_client()

        key = get_conversation_key(
            conversation_id
        )

        client.delete(
            key
        )

        return True

    except redis.RedisError as exc:
        print(
            "Redis history deletion "
            f"unavailable: {exc}"
        )

        return False