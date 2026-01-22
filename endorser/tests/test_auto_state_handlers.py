"""Unit tests for auto_state_handlers endorsement logic."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from api.db.models.allow import (
    AllowedCredentialDefinition,
    AllowedPublicDid,
    AllowedSchema,
)
from api.endpoints.models.endorse import EndorseTransaction, EndorseTransactionType
from api.services.auto_state_handlers import (
    CreddefCriteria,
    SchemaCriteria,
    allowed_creddef,
    allowed_publish_did,
    allowed_schema,
    check_auto_endorse,
    is_endorsable_transaction,
)
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_check_auto_endorse_found():
    """Test check_auto_endorse when a matching record is found."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    result_mock = MagicMock()
    result_mock.one_or_none.return_value = MagicMock()  # Non-None means found
    db.execute.return_value = result_mock

    # Act
    result = await check_auto_endorse(
        db,
        AllowedPublicDid,
        [(AllowedPublicDid.registered_did, "did:example:123")],
    )

    # Assert
    assert result is True
    db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_check_auto_endorse_not_found():
    """Test check_auto_endorse when no matching record is found."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    result_mock = MagicMock()
    result_mock.one_or_none.return_value = None
    db.execute.return_value = result_mock

    # Act
    result = await check_auto_endorse(
        db,
        AllowedPublicDid,
        [(AllowedPublicDid.registered_did, "did:example:unknown")],
    )

    # Assert
    assert result is False


@pytest.mark.asyncio
async def test_allowed_publish_did():
    """Test allowed_publish_did calls check_auto_endorse correctly."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)

    with patch("api.services.auto_state_handlers.check_auto_endorse") as mock_check:
        mock_check.return_value = True

        # Act
        result = await allowed_publish_did(db, "did:example:123")

    # Assert
    assert result is True
    mock_check.assert_called_once()
    call_args = mock_check.call_args
    assert call_args[0][0] == db
    assert call_args[0][1] == AllowedPublicDid


@pytest.mark.asyncio
async def test_allowed_schema():
    """Test allowed_schema calls check_auto_endorse with correct criteria."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    schema_criteria = SchemaCriteria(
        DID="did:example:123", Name="TestSchema", Version="1.0"
    )

    with patch("api.services.auto_state_handlers.check_auto_endorse") as mock_check:
        mock_check.return_value = True

        # Act
        result = await allowed_schema(db, schema_criteria)

    # Assert
    assert result is True
    mock_check.assert_called_once()
    call_args = mock_check.call_args
    assert call_args[0][1] == AllowedSchema


@pytest.mark.asyncio
async def test_allowed_creddef():
    """Test allowed_creddef calls check_auto_endorse with correct criteria."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    creddef_criteria = CreddefCriteria(
        DID="did:example:123",
        Schema_Issuer_DID="did:example:issuer",
        Schema_Name="TestSchema",
        Schema_Version="1.0",
        Tag="default",
    )

    with patch("api.services.auto_state_handlers.check_auto_endorse") as mock_check:
        mock_check.return_value = True

        # Act
        result = await allowed_creddef(db, creddef_criteria)

    # Assert
    assert result is True
    mock_check.assert_called_once()
    call_args = mock_check.call_args
    assert call_args[0][1] == AllowedCredentialDefinition


@pytest.mark.asyncio
async def test_is_endorsable_transaction_did_registration():
    """Test is_endorsable_transaction for DID registration with author_goal_code."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    transaction = MagicMock(spec=EndorseTransaction)
    transaction.author_goal_code = "aries.transaction.register_public_did"
    transaction.transaction_request = {"did": "did:example:123"}
    transaction.transaction_type = EndorseTransactionType.did

    with patch("api.services.auto_state_handlers.allowed_publish_did") as mock_allowed:
        mock_allowed.return_value = True

        # Act
        result = await is_endorsable_transaction(db, transaction)

    # Assert
    assert result is True
    mock_allowed.assert_called_once_with(db, "did:example:123")


@pytest.mark.asyncio
async def test_is_endorsable_transaction_did_type():
    """Test is_endorsable_transaction for DID transaction type."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    transaction = MagicMock(spec=EndorseTransaction)
    transaction.author_goal_code = None
    transaction.transaction_type = EndorseTransactionType.did
    transaction.transaction = {"dest": "did:example:456"}
    transaction.transaction_request = {}

    with patch("api.services.auto_state_handlers.allowed_publish_did") as mock_allowed:
        mock_allowed.return_value = True

        # Act
        result = await is_endorsable_transaction(db, transaction)

    # Assert
    assert result is True
    mock_allowed.assert_called_once_with(db, "did:example:456")


@pytest.mark.asyncio
async def test_is_endorsable_transaction_attrib_type():
    """Test is_endorsable_transaction for attrib transaction type."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    transaction = MagicMock(spec=EndorseTransaction)
    transaction.author_goal_code = None
    transaction.transaction_type = EndorseTransactionType.attrib
    transaction.transaction = {"dest": "did:example:789"}
    transaction.transaction_request = {}

    with patch("api.services.auto_state_handlers.allowed_publish_did") as mock_allowed:
        mock_allowed.return_value = False

        # Act
        result = await is_endorsable_transaction(db, transaction)

    # Assert
    assert result is False
    mock_allowed.assert_called_once_with(db, "did:example:789")


@pytest.mark.asyncio
async def test_is_endorsable_transaction_schema():
    """Test is_endorsable_transaction for schema transaction."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    transaction = MagicMock(spec=EndorseTransaction)
    transaction.author_goal_code = None
    transaction.transaction_type = EndorseTransactionType.schema
    transaction.author_did = "did:example:author"
    transaction.transaction = {"data": {"name": "TestSchema", "version": "1.0"}}

    with patch("api.services.auto_state_handlers.allowed_schema") as mock_allowed:
        mock_allowed.return_value = True

        # Act
        result = await is_endorsable_transaction(db, transaction)

    # Assert
    assert result is True
    mock_allowed.assert_called_once()
    call_args = mock_allowed.call_args[0]
    assert call_args[0] == db
    schema_criteria = call_args[1]
    assert schema_criteria.DID == "did:example:author"
    assert schema_criteria.Name == "TestSchema"
    assert schema_criteria.Version == "1.0"


@pytest.mark.asyncio
async def test_is_endorsable_transaction_cred_def():
    """Test is_endorsable_transaction for credential definition transaction."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    transaction = MagicMock(spec=EndorseTransaction)
    transaction.author_goal_code = None
    transaction.transaction_type = EndorseTransactionType.cred_def
    transaction.author_did = "did:example:author"
    transaction.transaction = {"ref": 12345, "tag": "default"}

    # Mock the schema lookup response
    # The code extracts: schema_id[0], schema_id[2], schema_id[3]
    # So if we want Schema_Issuer_DID="did", Schema_Name="TestSchema", Schema_Version="1.0"
    # We need: index[0]="did", index[2]="TestSchema", index[3]="1.0"
    # Format: did:placeholder:TestSchema:1.0
    mock_schema_response = {"schema": {"id": "did:placeholder:TestSchema:1.0"}}

    with (
        patch("api.services.auto_state_handlers.allowed_creddef") as mock_allowed,
        patch("api.services.auto_state_handlers.au.acapy_GET") as mock_acapy,
    ):
        mock_allowed.return_value = True
        mock_acapy.return_value = mock_schema_response

        # Act
        result = await is_endorsable_transaction(db, transaction)

    # Assert
    assert result is True
    mock_acapy.assert_called_once_with("schemas/12345")
    mock_allowed.assert_called_once()
    call_args = mock_allowed.call_args[0]
    creddef_criteria = call_args[1]
    assert creddef_criteria.DID == "did:example:author"
    assert creddef_criteria.Schema_Issuer_DID == "did"
    assert creddef_criteria.Schema_Name == "TestSchema"
    assert creddef_criteria.Schema_Version == "1.0"
    assert creddef_criteria.Tag == "default"


@pytest.mark.asyncio
async def test_is_endorsable_transaction_missing_author_did():
    """Test is_endorsable_transaction returns False when author_did is missing."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    transaction = MagicMock(spec=EndorseTransaction)
    transaction.author_goal_code = None
    transaction.transaction_type = EndorseTransactionType.schema
    transaction.author_did = None  # Missing
    transaction.transaction = {"data": {"name": "Test", "version": "1.0"}}

    # Act
    result = await is_endorsable_transaction(db, transaction)

    # Assert
    assert result is False


@pytest.mark.asyncio
async def test_is_endorsable_transaction_missing_transaction():
    """Test is_endorsable_transaction returns False when transaction is missing."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    transaction = MagicMock(spec=EndorseTransaction)
    transaction.author_goal_code = None
    transaction.transaction_type = EndorseTransactionType.schema
    transaction.author_did = "did:example:author"
    transaction.transaction = None  # Missing

    # Act
    result = await is_endorsable_transaction(db, transaction)

    # Assert
    assert result is False


@pytest.mark.asyncio
async def test_is_endorsable_transaction_unknown_type():
    """Test is_endorsable_transaction returns False for unknown transaction type."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    transaction = MagicMock(spec=EndorseTransaction)
    transaction.author_goal_code = None
    # Use a type that isn't explicitly handled
    transaction.transaction_type = "unknown_type"
    transaction.author_did = "did:example:author"
    transaction.transaction = {"some": "data"}

    # Act
    result = await is_endorsable_transaction(db, transaction)

    # Assert
    assert result is False
