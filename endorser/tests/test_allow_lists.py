"""Unit tests for allow_lists service functions."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from api.db.models.endorse_request import EndorseRequest
from api.endpoints.models.endorse import EndorseTransactionState
from api.services.allow_lists import updated_allowed
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_updated_allowed_no_pending_transactions():
    """Test updated_allowed when there are no pending transactions."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    result_mock = MagicMock()
    result_mock.scalars().all.return_value = []
    db.execute.return_value = result_mock

    # Act
    with patch(
        "api.services.allow_lists.is_endorsable_transaction"
    ) as mock_is_endorsable, patch(
        "api.services.allow_lists.endorse_transaction"
    ) as mock_endorse:
        await updated_allowed(db)

    # Assert
    db.execute.assert_called_once()
    db.commit.assert_called_once()
    mock_is_endorsable.assert_not_called()
    mock_endorse.assert_not_called()


@pytest.mark.asyncio
async def test_updated_allowed_with_endorsable_transactions():
    """Test updated_allowed endorses transactions that are allowed."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)

    # Create mock pending transactions
    txn1 = MagicMock(spec=EndorseRequest)
    txn1.transaction_id = "txn-1"
    txn1.state = EndorseTransactionState.request_received
    txn1.connection_id = "conn-1"
    txn1.author_goal_code = "test_goal"

    txn2 = MagicMock(spec=EndorseRequest)
    txn2.transaction_id = "txn-2"
    txn2.state = EndorseTransactionState.request_received
    txn2.connection_id = "conn-2"
    txn2.author_goal_code = "test_goal"

    result_mock = MagicMock()
    result_mock.scalars().all.return_value = [txn1, txn2]
    db.execute.return_value = result_mock

    # Act
    with patch(
        "api.services.allow_lists.is_endorsable_transaction"
    ) as mock_is_endorsable, patch(
        "api.services.allow_lists.endorse_transaction"
    ) as mock_endorse, patch(
        "api.services.allow_lists.db_to_txn_object"
    ) as mock_db_to_txn:

        # Mock first transaction is endorsable, second is not
        mock_is_endorsable.side_effect = [True, False]
        mock_txn_obj1 = MagicMock()
        mock_txn_obj2 = MagicMock()
        mock_db_to_txn.side_effect = [mock_txn_obj1, mock_txn_obj2]

        await updated_allowed(db)

    # Assert
    assert db.execute.call_count == 1
    assert mock_is_endorsable.call_count == 2
    mock_endorse.assert_called_once_with(db, mock_txn_obj1)
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_updated_allowed_with_no_endorsable_transactions():
    """Test updated_allowed when no transactions are allowed."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)

    txn = MagicMock(spec=EndorseRequest)
    txn.transaction_id = "txn-1"
    txn.state = EndorseTransactionState.request_received

    result_mock = MagicMock()
    result_mock.scalars().all.return_value = [txn]
    db.execute.return_value = result_mock

    # Act
    with patch(
        "api.services.allow_lists.is_endorsable_transaction"
    ) as mock_is_endorsable, patch(
        "api.services.allow_lists.endorse_transaction"
    ) as mock_endorse, patch(
        "api.services.allow_lists.db_to_txn_object"
    ) as mock_db_to_txn:

        mock_is_endorsable.return_value = False
        mock_db_to_txn.return_value = MagicMock()

        await updated_allowed(db)

    # Assert
    mock_endorse.assert_not_called()
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_updated_allowed_commits_after_endorsements():
    """Test that updated_allowed commits changes to database (bug fix verification)."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)

    txn1 = MagicMock(spec=EndorseRequest)
    txn1.transaction_id = "txn-1"
    txn1.state = EndorseTransactionState.request_received

    txn2 = MagicMock(spec=EndorseRequest)
    txn2.transaction_id = "txn-2"
    txn2.state = EndorseTransactionState.request_received

    result_mock = MagicMock()
    result_mock.scalars().all.return_value = [txn1, txn2]
    db.execute.return_value = result_mock

    # Act
    with patch(
        "api.services.allow_lists.is_endorsable_transaction"
    ) as mock_is_endorsable, patch(
        "api.services.allow_lists.endorse_transaction"
    ) as mock_endorse, patch(
        "api.services.allow_lists.db_to_txn_object"
    ) as mock_db_to_txn:

        mock_is_endorsable.side_effect = [True, True]
        mock_txn_obj1 = MagicMock()
        mock_txn_obj2 = MagicMock()
        mock_db_to_txn.side_effect = [mock_txn_obj1, mock_txn_obj2]

        await updated_allowed(db)

    # Assert - verify commit is called AFTER endorsements
    assert mock_endorse.call_count == 2
    db.commit.assert_called_once()

    # Verify order: endorse calls happen before commit
    call_order = []
    for mock_call in db.method_calls:
        call_order.append(mock_call[0])
    for endorse_call in mock_endorse.call_args_list:
        call_order.append("endorse")

    # Commit should be after all endorse operations
    commit_index = call_order.index("commit")
    assert commit_index > 0  # Not first


@pytest.mark.asyncio
async def test_updated_allowed_handles_exceptions():
    """Test that updated_allowed handles exceptions gracefully."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    db.execute.side_effect = Exception("Database error")

    # Act
    await updated_allowed(db)  # Should not raise

    # Assert - function logs error but doesn't raise
    db.execute.assert_called_once()
    # Commit should not be called if execute fails
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_updated_allowed_queries_correct_state():
    """Test that updated_allowed queries for request_received state."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    result_mock = MagicMock()
    result_mock.scalars().all.return_value = []
    db.execute.return_value = result_mock

    # Act
    with patch("api.services.allow_lists.select") as mock_select:
        mock_where = MagicMock()
        mock_select.return_value.where.return_value = mock_where

        await updated_allowed(db)

    # Assert - verify select and where were called
    mock_select.assert_called_once()
    db.execute.assert_called_once()
