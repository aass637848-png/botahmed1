import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.models.user import User
from bot.models.target import Target
from bot.models.campaign import Campaign
from bot.models.message_log import MessageLog
from bot.models.setting import Setting


@pytest.mark.asyncio
async def test_user_and_target_creation(test_session: AsyncSession):
    # 1. Create User
    user = User(
        user_id=12345678,
        username="test_user",
        full_name="Test User",
        is_admin=False,
    )
    test_session.add(user)
    await test_session.commit()

    # 2. Create Target
    target = Target(
        owner_id=user.user_id,
        chat_id=-100123456789,
        username="@test_channel",
        title="Test Channel",
        chat_type="channel",
        can_post_messages=True,
    )
    test_session.add(target)
    await test_session.commit()

    # 3. Query
    stmt = select(Target).where(Target.chat_id == -100123456789)
    res = await test_session.execute(stmt)
    retrieved_target = res.scalar_one_or_none()

    assert retrieved_target is not None
    assert retrieved_target.title == "Test Channel"
    assert retrieved_target.can_post_messages is True


@pytest.mark.asyncio
async def test_campaign_and_logs(test_session: AsyncSession):
    # Create User
    user = User(user_id=999, username="camp_owner", full_name="Camp Owner")
    test_session.add(user)
    await test_session.commit()

    # Create Campaign
    campaign = Campaign(
        owner_id=user.user_id,
        name="Test Campaign",
        content_type="text",
        text_content="Hello World",
        target_ids=[1, 2],
        repeat_count=2,
    )
    test_session.add(campaign)
    await test_session.commit()
    await test_session.refresh(campaign)

    # Add MessageLog
    log = MessageLog(
        campaign_id=campaign.id,
        chat_id=-100123,
        target_title="Target 1",
        iteration=1,
        status="success",
    )
    test_session.add(log)
    await test_session.commit()

    stmt = select(MessageLog).where(MessageLog.campaign_id == campaign.id)
    res = await test_session.execute(stmt)
    logs = res.scalars().all()

    assert len(logs) == 1
    assert logs[0].status == "success"


@pytest.mark.asyncio
async def test_account_creation_and_upsert(test_session: AsyncSession):
    from bot.models.account import Account

    # 1. Create Account
    acc = Account(
        phone="+201012345678",
        session_string="test_session_str",
        first_name="Ahmed",
        username="ahmed_tg",
        user_id=11223344,
        added_by=999,
        is_active=True,
    )
    test_session.add(acc)
    await test_session.commit()

    # 2. Query and verify
    stmt = select(Account).where(Account.phone == "+201012345678")
    res = await test_session.execute(stmt)
    found = res.scalar_one_or_none()
    assert found is not None
    assert found.first_name == "Ahmed"

    # 3. Simulate Upsert (Update existing record)
    found.session_string = "new_session_str_updated"
    found.first_name = "Ahmed Updated"
    await test_session.commit()

    res2 = await test_session.execute(stmt)
    updated = res2.scalar_one_or_none()
    assert updated is not None
    assert updated.session_string == "new_session_str_updated"
    assert updated.first_name == "Ahmed Updated"

