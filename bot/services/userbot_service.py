import logging
from typing import Tuple, Optional, Dict, Any
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    FloodWaitError,
)
from config import settings

logger = logging.getLogger(__name__)

# Temporary store for ongoing authentication clients in memory: user_id -> dict
auth_sessions: Dict[int, Dict[str, Any]] = {}


async def start_phone_login(user_id: int, phone: str) -> Tuple[bool, str]:
    """Start Telethon login by sending confirmation code to user's Telegram."""
    if not settings.TELEGRAM_API_ID or not settings.TELEGRAM_API_HASH:
        return False, "❌ لم يتم ضبط API_ID أو API_HASH في المتغيرات البيئية!"

    phone_clean = phone.strip().replace(" ", "").replace("-", "")
    client = TelegramClient(StringSession(), settings.TELEGRAM_API_ID, settings.TELEGRAM_API_HASH)
    await client.connect()

    try:
        sent_code = await client.send_code_request(phone_clean)
        auth_sessions[user_id] = {
            "client": client,
            "phone": phone_clean,
            "phone_code_hash": sent_code.phone_code_hash,
        }
        return True, "تم إرسال كود التحقق بنجاح!"
    except Exception as e:
        await client.disconnect()
        return False, f"فشل إرسال الكود: {str(e)}"


async def verify_login_code(user_id: int, code: str) -> Tuple[bool, bool, Optional[str], str]:
    """
    Verify received SMS/Telegram code.
    Returns: (success, needs_2fa, session_string, message)
    """
    auth_data = auth_sessions.get(user_id)
    if not auth_data:
        return False, False, None, "انتهت مهلة الجلسة، يرجى إعادة البدء."

    client: TelegramClient = auth_data["client"]
    phone = auth_data["phone"]
    code_hash = auth_data["phone_code_hash"]

    try:
        await client.sign_in(phone=phone, code=code.strip(), phone_code_hash=code_hash)
        session_str = client.session.save()
        me = await client.get_me()
        await client.disconnect()
        auth_sessions.pop(user_id, None)
        return True, False, session_str, f"تم تسجيل الدخول بنجاح بحساب: {me.first_name} (@{me.username})"
    except SessionPasswordNeededError:
        return True, True, None, "الحساب محمي بكلمة سر للتحقق بخطوتين (2FA). أرسل كلمة السر:"
    except (PhoneCodeInvalidError, PhoneCodeExpiredError) as e:
        return False, False, None, f"كود غير صحيح أو منتهي الصلاحية: {str(e)}"
    except Exception as e:
        return False, False, None, f"خطأ أثناء تسجيل الدخول: {str(e)}"


async def verify_2fa_password(user_id: int, password: str) -> Tuple[bool, Optional[str], str]:
    """Verify 2FA password."""
    auth_data = auth_sessions.get(user_id)
    if not auth_data:
        return False, None, "انتهت مهلة الجلسة، يرجى إعادة البدء."

    client: TelegramClient = auth_data["client"]
    try:
        await client.sign_in(password=password.strip())
        session_str = client.session.save()
        me = await client.get_me()
        await client.disconnect()
        auth_sessions.pop(user_id, None)
        return True, session_str, f"تم تسجيل الدخول بنجاح بحساب: {me.first_name} (@{me.username})"
    except Exception as e:
        return False, None, f"فشل التحقق من كلمة السر: {str(e)}"


async def send_via_userbot(
    session_str: str,
    target_identifier: str | int,
    content_type: str,
    text_content: Optional[str],
    file_path_or_bytes: Any = None,
) -> Tuple[bool, Optional[str], Optional[int]]:
    """Send message/media using connected Userbot account."""
    client = TelegramClient(StringSession(session_str), settings.TELEGRAM_API_ID, settings.TELEGRAM_API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            return False, "جلسة الحساب غير مسجلة أو ملغاة.", None

        # Resolve entity (chat or username)
        entity = await client.get_input_entity(target_identifier)

        if content_type == "text" or not file_path_or_bytes:
            await client.send_message(entity, text_content or "")
        else:
            await client.send_file(entity, file_path_or_bytes, caption=text_content)

        return True, None, None

    except FloodWaitError as e:
        logger.warning(f"Userbot FloodWait: {e.seconds}s")
        return False, f"FloodWait ({e.seconds} ثانية)", e.seconds
    except Exception as e:
        logger.error(f"Userbot send error: {str(e)}")
        return False, str(e), None
    finally:
        await client.disconnect()
