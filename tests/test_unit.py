import pytest
from unittest.mock import Mock

from notification_engine import NotificationEngine


# ------------------------------
# Validation Boundary Test
# ------------------------------

def test_valid_phone():

    # Create fake repository
    repo = Mock()
    repo.get_status.return_value = None

    # Create fake SMS gateway
    gateway = Mock()
    gateway.send_sms.return_value = True

    # Create the notification engine
    engine = NotificationEngine(
        repo,
        gateway
    )

    # Send notification
    result = engine.dispatch(
        "1",
        "+250780000000",
        "Hello"
    )

    # Verify result
    assert result == "SENT_PRIMARY"


@pytest.mark.parametrize("phone", [
    "0780000000",
    "+00012"
])
def test_invalid_phone(phone):

    # Create fake repository
    repo = Mock()

    # Create fake SMS gateway
    gateway = Mock()

    # Create notification engine
    engine = NotificationEngine(
        repo,
        gateway
    )

    # Invalid phone should raise ValueError
    with pytest.raises(ValueError):
        engine.dispatch(
            "1",
            phone,
            "Hello"
        )

    # Repository should not be called
    repo.get_status.assert_not_called()


# ------------------------------
# Idempotency Mock Check
# ------------------------------

def test_already_sent():

    # Fake repository
    repo = Mock()

    # Pretend message was already sent
    repo.get_status.return_value = "SENT"

    # Fake SMS gateway
    gateway = Mock()

    # Create notification engine
    engine = NotificationEngine(
        repo,
        gateway
    )

    # Dispatch message
    result = engine.dispatch(
        "1",
        "+250780000000",
        "Hello"
    )

    # Verify response
    assert result == "ALREADY_SENT"

    # SMS should never be sent again
    gateway.send_sms.assert_not_called()


    # ------------------------------
# Retry Logic Verification
# ------------------------------

def test_retry_then_success():

    # Fake repository
    repo = Mock()
    repo.get_status.return_value = None

    # Fake SMS gateway
    gateway = Mock()

    # First attempt fails, second succeeds
    gateway.send_sms.side_effect = [
        Exception("Network Error"),
        True
    ]

    # Create notification engine
    engine = NotificationEngine(
        repo,
        gateway
    )

    # Dispatch message
    result = engine.dispatch(
        "1",
        "+250780000000",
        "Hello"
    )

    # Verify successful retry
    assert result == "SENT_PRIMARY"

    # Verify gateway was called twice
    assert gateway.send_sms.call_count == 2

    # Verify status was saved
    repo.save_status.assert_called_with(
        "1",
        "+250780000000",
        "SENT"
    )


    # ------------------------------
# Fallback Gateway Failover
# ------------------------------

def test_backup_gateway():

    # Fake repository
    repo = Mock()
    repo.get_status.return_value = None

    # Primary gateway fails twice
    primary_gateway = Mock()
    primary_gateway.send_sms.side_effect = [
        Exception("Primary failed"),
        Exception("Primary failed")
    ]

    # Backup gateway succeeds
    backup_gateway = Mock()
    backup_gateway.send_sms.return_value = True

    # Create notification engine
    engine = NotificationEngine(
        repo,
        primary_gateway,
        backup_gateway
    )

    # Dispatch message
    result = engine.dispatch(
        "1",
        "+250780000000",
        "Hello"
    )

    # Verify backup delivery
    assert result == "SENT_BACKUP"


    # ------------------------------
# Complete Failure Path
# ------------------------------

def test_all_gateways_fail():

    # Fake repository
    repo = Mock()
    repo.get_status.return_value = None

    # Primary gateway fails
    primary_gateway = Mock()
    primary_gateway.send_sms.side_effect = Exception(
        "Primary failed"
    )

    # Backup gateway fails
    backup_gateway = Mock()
    backup_gateway.send_sms.side_effect = Exception(
        "Backup failed"
    )

    # Create notification engine
    engine = NotificationEngine(
        repo,
        primary_gateway,
        backup_gateway
    )

    # RuntimeError should be raised
    with pytest.raises(RuntimeError):
        engine.dispatch(
            "1",
            "+250780000000",
            "Hello"
        )

    # Verify FAILED status was saved
    repo.save_status.assert_called_with(
        "1",
        "+250780000000",
        "FAILED"
    )