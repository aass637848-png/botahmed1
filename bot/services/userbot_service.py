import logging
import re
from typing import Tuple, Optional, Dict, Any, List
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import MessageService
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    FloodWaitError,
    UserAlreadyParticipantError,
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


async def verify_login_code(user_id: int, code: str) -> Tuple[bool, bool, Optional[str], str, Optional[Dict[str, Any]]]:
    """
    Verify received SMS/Telegram code.
    Returns: (success, needs_2fa, session_string, message, me_info)
    """
    auth_data = auth_sessions.get(user_id)
    if not auth_data:
        return False, False, None, "انتهت مهلة الجلسة، يرجى إعادة البدء.", None

    client: TelegramClient = auth_data["client"]
    phone = auth_data["phone"]
    code_hash = auth_data["phone_code_hash"]

    # Extract digits only (in case user pasted with spaces or dashes)
    clean_code = re.sub(r"\D", "", code.strip())
    if not clean_code:
        clean_code = code.strip()

    try:
        await client.sign_in(phone=phone, code=clean_code, phone_code_hash=code_hash)
        session_str = client.session.save()
        me = await client.get_me()
        await client.disconnect()
        auth_sessions.pop(user_id, None)
        me_info = {
            "first_name": me.first_name or "",
            "username": me.username,
            "id": me.id,
        }
        return True, False, session_str, f"تم تسجيل الدخول بنجاح بحساب: {me.first_name} (@{me.username})", me_info
    except SessionPasswordNeededError:
        return True, True, None, "الحساب محمي بكلمة سر للتحقق بخطوتين (2FA). أرسل كلمة السر:", None
    except (PhoneCodeInvalidError, PhoneCodeExpiredError) as e:
        return False, False, None, f"كود غير صحيح أو منتهي الصلاحية: {str(e)}", None
    except Exception as e:
        return False, False, None, f"خطأ أثناء تسجيل الدخول: {str(e)}", None


async def verify_2fa_password(user_id: int, password: str) -> Tuple[bool, Optional[str], str, Optional[Dict[str, Any]]]:
    """Verify 2FA password."""
    auth_data = auth_sessions.get(user_id)
    if not auth_data:
        return False, None, "انتهت مهلة الجلسة، يرجى إعادة البدء.", None

    client: TelegramClient = auth_data["client"]
    try:
        await client.sign_in(password=password.strip())
        session_str = client.session.save()
        me = await client.get_me()
        await client.disconnect()
        auth_sessions.pop(user_id, None)
        me_info = {
            "first_name": me.first_name or "",
            "username": me.username,
            "id": me.id,
        }
        return True, session_str, f"تم تسجيل الدخول بنجاح بحساب: {me.first_name} (@{me.username})", me_info
    except Exception as e:
        return False, None, f"فشل التحقق من كلمة السر: {str(e)}", None


async def fetch_latest_login_code(session_str: str) -> Tuple[bool, Optional[str], str]:
    """
    Connects to the Telegram user account and reads the latest official login code
    sent by Telegram (service notifications from ID 777000).
    Returns: (success, extracted_code, full_message_text)
    """
    client = TelegramClient(StringSession(session_str), settings.TELEGRAM_API_ID, settings.TELEGRAM_API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            return False, None, "الجلسة غير مسجلة أو تم تسجيل الخروج من الحساب."

        # Fetch recent messages from Telegram Notifications (777000)
        messages = await client.get_messages(777000, limit=3)
        if not messages:
            # Fallback search dialogs if 777000 was empty
            async for dialog in client.iter_dialogs(limit=5):
                if dialog.id == 777000 or (dialog.name and "Telegram" in dialog.name):
                    messages = await client.get_messages(dialog.id, limit=3)
                    break

        if not messages:
            return False, None, "لم يتم العثور على أي رسائل واردة من تيليجرام مؤخرًا."

        latest_msg = messages[0]
        text = latest_msg.text or latest_msg.message or ""

        if not text:
            return False, None, "آخر رسالة واردة من تيليجرام فارغة أو غير نصية."

        # Extract 5 or 6 digit code
        # Example pattern: "Login code: 12345" or "12345 is your code" or standalone 5-6 digits
        match = re.search(r"(?:code|كود|Login code|رمز الدخول|رمز التأكيد)[^\d]{0,10}(\d{5,6})", text, re.IGNORECASE)
        code = None
        if match:
            code = match.group(1)
        else:
            # General fallback: look for any 5-6 consecutive digits in text
            digits = re.findall(r"\b\d{5,6}\b", text)
            if digits:
                code = digits[0]

        return True, code, text

    except Exception as e:
        logger.error(f"Error reading login code: {str(e)}")
        return False, None, f"حدث خطأ أثناء جلب الرسالة: {str(e)}"
    finally:
        await client.disconnect()


async def auto_join_target(client: TelegramClient, target_identifier: str | int) -> None:
    """Automatically join channel, group, or invite link if not already joined."""
    target_str = str(target_identifier).strip()
    try:
        # 1. If it's an invite link (t.me/+hash or t.me/joinchat/hash)
        match_invite = re.search(r"(?:t\.me|telegram\.me)/(?:\+|joinchat/)([a-zA-Z0-9_-]+)", target_str)
        if match_invite:
            invite_hash = match_invite.group(1)
            try:
                await client(ImportChatInviteRequest(invite_hash))
                logger.info(f"Userbot auto-joined via invite link: {invite_hash}")
                return
            except UserAlreadyParticipantError:
                return
            except Exception as e:
                logger.warning(f"Failed to join via invite link: {str(e)}")
                return

        # 2. Try joining by entity
        try:
            entity = await client.get_entity(target_identifier)
            await client(JoinChannelRequest(entity))
            logger.info(f"Userbot auto-joined channel/group: {target_identifier}")
        except UserAlreadyParticipantError:
            pass
        except Exception as e:
            # If entity resolution failed, try joining directly if it's a @username
            if isinstance(target_identifier, str) and target_identifier.startswith("@"):
                try:
                    await client(JoinChannelRequest(target_identifier))
                    logger.info(f"Userbot auto-joined by username: {target_identifier}")
                except UserAlreadyParticipantError:
                    pass
                except Exception as inner_e:
                    logger.debug(f"Direct join attempt info: {str(inner_e)}")
    except Exception as e:
        logger.warning(f"auto_join_target error for {target_identifier}: {str(e)}")


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

        # 1. Automatically join the channel/group first if not joined!
        await auto_join_target(client, target_identifier)

        # 2. Resolve entity (chat or username) with cache warming
        entity = None
        try:
            entity = await client.get_entity(target_identifier)
        except Exception:
            try:
                # Load recent dialogs into memory cache to resolve channel/group IDs
                await client.get_dialogs(limit=50)
                entity = await client.get_entity(target_identifier)
            except Exception:
                try:
                    entity = await client.get_input_entity(target_identifier)
                except Exception:
                    try:
                        # Try stripped integer channel ID if prefixed with -100
                        raw_str = str(target_identifier).strip()
                        if raw_str.startswith("-100"):
                            clean_id = int(raw_str[4:])
                            entity = await client.get_entity(clean_id)
                    except Exception as e:
                        logger.error(f"Entity resolution failed for {target_identifier}: {str(e)}")
                        return False, f"تعذر التعرف على الوجهة ({str(e)})", None

        if not entity:
            return False, f"تعذر إيجاد القناة أو المجموعة: {target_identifier}", None

        # 3. Send file/photo or text message
        if file_path_or_bytes:
            await client.send_file(entity, file_path_or_bytes, caption=text_content or None)
        else:
            if not text_content or not text_content.strip():
                return False, "لا يمكن إرسال رسالة نصية فارغة بدون محتوى أو وسائط.", None
            await client.send_message(entity, text_content)

        return True, None, None

    except FloodWaitError as e:
        logger.warning(f"Userbot FloodWait: {e.seconds}s")
        return False, f"FloodWait ({e.seconds} ثانية)", e.seconds
    except Exception as e:
        logger.error(f"Userbot send error: {str(e)}")
        return False, str(e), None
    finally:
        await client.disconnect()
