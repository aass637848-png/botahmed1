import os
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models.user import User
from bot.models.target import Target
from bot.models.campaign import Campaign
from bot.models.message_log import MessageLog
from bot.services.broadcast_worker import (
    acquire_target_locks,
    release_target_locks,
    is_any_target_locked,
)
from bot.services.report_service import get_user_statistics, generate_user_report_csv


@pytest.mark.asyncio
async def test_target_locks():
    targets = [-1001, -1002]

    # Acquire locks
    acquired = await acquire_target_locks(targets)
    assert acquired is True

    # Check is locked
    locked = await is_any_target_locked([-1001])
    assert locked is True

    # Try acquiring again should fail
    acquired_second = await acquire_target_locks([-1001, -1003])
    assert acquired_second is False

    # Release locks
    await release_target_locks(targets)
    assert await is_any_target_locked([-1001]) is False


@pytest.mark.asyncio
async def test_report_service(test_session: AsyncSession):
    user_id = 777
    user = User(user_id=user_id, username="reporter", full_name="Reporter")
    test_session.add(user)

    target = Target(owner_id=user_id, chat_id=-100777, title="Channel 777")
    test_session.add(target)

    campaign = Campaign(owner_id=user_id, name="Camp 1", target_ids=[1])
    test_session.add(campaign)
    await test_session.commit()
    await test_session.refresh(campaign)

    log1 = MessageLog(campaign_id=campaign.id, chat_id=-100777, target_title="Channel 777", status="success")
    log2 = MessageLog(campaign_id=campaign.id, chat_id=-100777, target_title="Channel 777", status="failed", error_message="Forbidden")
    test_session.add_all([log1, log2])
    await test_session.commit()

    stats = await get_user_statistics(test_session, user_id)
    assert stats["targets_count"] == 1
    assert stats["success_messages"] == 1
    assert stats["failed_messages"] == 1
    assert stats["total_messages"] == 2

    # Test CSV Generation
    csv_file = await generate_user_report_csv(test_session, user_id)
    assert os.path.exists(csv_file)
    assert os.path.getsize(csv_file) > 0

    # Cleanup test csv
    try:
        os.remove(csv_file)
    except Exception:
        pass
