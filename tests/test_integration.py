import sqlite3
import pytest

from notification_engine import (
    NotificationEngine,
    WalletRepository,
    SMSGatewayClient
)


class SQLiteRepository(WalletRepository):

    def __init__(self, connection):
        self.connection = connection


    def get_status(self, msg_id):

        cursor = self.connection.cursor()

        cursor.execute(
            "SELECT status FROM messages WHERE msg_id=?",
            (msg_id,)
        )

        result = cursor.fetchone()

        if result:
            return result[0]

        return None


    def save_status(self, msg_id, phone, status):

        self.connection.execute(
            """
            INSERT INTO messages
            VALUES (?, ?, ?)
            """,
            (msg_id, phone, status)
        )

        self.connection.commit()



class FakeGateway(SMSGatewayClient):

    def send_sms(self, phone, message):
        return True



@pytest.fixture
def database():

    connection = sqlite3.connect(":memory:")

    connection.execute(
        """
        CREATE TABLE messages(
            msg_id TEXT,
            phone TEXT,
            status TEXT
        )
        """
    )

    yield connection

    connection.close()

    # ------------------------------
# Successful Dispatch Integration Test
# ------------------------------

def test_successful_dispatch(database):

    # Create real repository connected to SQLite
    repo = SQLiteRepository(database)

    # Create fake SMS gateway
    gateway = FakeGateway()

    # Create notification engine
    engine = NotificationEngine(
        repo,
        gateway
    )

    # Send notification
    result = engine.dispatch(
        "101",
        "+250780000000",
        "Hello"
    )

    # Verify returned result
    assert result == "SENT_PRIMARY"


    # Check real database content
    cursor = database.cursor()

    cursor.execute(
        """
        SELECT status
        FROM messages
        WHERE msg_id='101'
        """
    )

    row = cursor.fetchone()


    # Verify database saved SENT
    assert row[0] == "SENT"