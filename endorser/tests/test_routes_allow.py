"""Unit tests for allow routes, specifically update_full_config functionality."""

from io import BytesIO
from unittest.mock import AsyncMock, patch

import pytest
from api.endpoints.routes.allow import update_full_config
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession


def create_mock_upload_file(filename: str, content: str) -> UploadFile:
    """Create a mock UploadFile for testing."""
    file_like = BytesIO(content.encode())
    return UploadFile(filename=filename, file=file_like)


@pytest.mark.asyncio
async def test_update_full_config_rejects_no_files():
    """Test that update_full_config raises 400 when no files are provided."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await update_full_config(
            log_entry=None,
            publish_did=None,
            schema=None,
            credential_definition=None,
            db=db,
            delete_contents=True,
        )

    assert exc_info.value.status_code == 400
    assert "At least one configuration file must be provided" in exc_info.value.detail


@pytest.mark.asyncio
async def test_update_full_config_single_file_replace():
    """Test uploading a single config file in replace mode."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    csv_content = "registered_did,details\ndid:example:123,test"
    publish_did_file = create_mock_upload_file("publish_did.csv", csv_content)

    # Act
    with (
        patch("api.endpoints.routes.allow.update_allowed_config") as mock_update,
        patch("api.endpoints.routes.allow.updated_allowed") as mock_updated,
    ):
        mock_update.return_value = {"added": 1}

        result = await update_full_config(
            log_entry=None,
            publish_did=publish_did_file,
            schema=None,
            credential_definition=None,
            db=db,
            delete_contents=True,
        )

    # Assert
    assert "AllowedPublicDid" in result
    db.execute.assert_called_once()  # Only delete for AllowedPublicDid
    mock_update.assert_called_once()
    db.commit.assert_called_once()
    mock_updated.assert_called_once_with(db)


@pytest.mark.asyncio
async def test_update_full_config_multiple_files_replace():
    """Test uploading multiple config files in replace mode."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)

    did_content = "registered_did,details\ndid:example:123,test"
    schema_content = (
        "author_did,schema_name,version,details\ndid:example:456,TestSchema,1.0,note"
    )

    publish_did_file = create_mock_upload_file("publish_did.csv", did_content)
    schema_file = create_mock_upload_file("schema.csv", schema_content)

    # Act
    with (
        patch("api.endpoints.routes.allow.update_allowed_config") as mock_update,
        patch("api.endpoints.routes.allow.updated_allowed") as mock_updated,
    ):
        mock_update.side_effect = [{"added": 1}, {"added": 1}]

        result = await update_full_config(
            log_entry=None,
            publish_did=publish_did_file,
            schema=schema_file,
            credential_definition=None,
            db=db,
            delete_contents=True,
        )

    # Assert
    assert "AllowedPublicDid" in result
    assert "AllowedSchema" in result
    assert db.execute.call_count == 2  # Delete for both tables
    assert mock_update.call_count == 2
    db.commit.assert_called_once()
    mock_updated.assert_called_once_with(db)


@pytest.mark.asyncio
async def test_update_full_config_single_file_append():
    """Test uploading a single config file in append mode."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    csv_content = "author_did,schema_name,version,details\n*,*,*,allow all"
    schema_file = create_mock_upload_file("schema.csv", csv_content)

    # Act
    with (
        patch("api.endpoints.routes.allow.update_allowed_config") as mock_update,
        patch("api.endpoints.routes.allow.updated_allowed") as mock_updated,
    ):
        mock_update.return_value = {"added": 1}

        result = await update_full_config(
            log_entry=None,
            publish_did=None,
            schema=schema_file,
            credential_definition=None,
            db=db,
            delete_contents=False,
        )

    # Assert
    assert "AllowedSchema" in result
    db.execute.assert_not_called()  # No delete in append mode
    mock_update.assert_called_once()
    db.commit.assert_called_once()
    mock_updated.assert_called_once_with(db)


@pytest.mark.asyncio
async def test_update_full_config_all_files_replace():
    """Test uploading all four config files in replace mode."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)

    log_entry_content = (
        "scid,domain,namespace,identifier,log_updates\ntest_scid,test.com,ns,id1,true"
    )
    did_content = "registered_did,details\ndid:example:123,test"
    schema_content = (
        "author_did,schema_name,version,details\ndid:example:456,TestSchema,1.0,note"
    )
    creddef_content = "creddef_author_did,schema_issuer_did,schema_name,version,tag,details\ndid:ex:1,did:ex:2,Schema,1.0,default,test"

    log_entry_file = create_mock_upload_file("log_entry.csv", log_entry_content)
    publish_did_file = create_mock_upload_file("publish_did.csv", did_content)
    schema_file = create_mock_upload_file("schema.csv", schema_content)
    creddef_file = create_mock_upload_file("creddef.csv", creddef_content)

    # Act
    with (
        patch("api.endpoints.routes.allow.update_allowed_config") as mock_update,
        patch("api.endpoints.routes.allow.updated_allowed") as mock_updated,
    ):
        mock_update.side_effect = [
            {"added": 1},
            {"added": 1},
            {"added": 1},
            {"added": 1},
        ]

        result = await update_full_config(
            log_entry=log_entry_file,
            publish_did=publish_did_file,
            schema=schema_file,
            credential_definition=creddef_file,
            db=db,
            delete_contents=True,
        )

    # Assert
    assert len(result) == 4
    assert "AllowedLogEntry" in result
    assert "AllowedPublicDid" in result
    assert "AllowedSchema" in result
    assert "AllowedCredentialDefinition" in result
    assert db.execute.call_count == 4  # Delete for all tables
    assert mock_update.call_count == 4
    db.commit.assert_called_once()
    mock_updated.assert_called_once_with(db)


@pytest.mark.asyncio
async def test_update_full_config_calls_updated_allowed():
    """Test that update_full_config calls updated_allowed to reprocess pending transactions."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    csv_content = "registered_did,details\ndid:example:123,test"
    publish_did_file = create_mock_upload_file("publish_did.csv", csv_content)

    # Act
    with (
        patch("api.endpoints.routes.allow.update_allowed_config") as mock_update,
        patch("api.endpoints.routes.allow.updated_allowed") as mock_updated,
    ):
        mock_update.return_value = {"added": 1}

        await update_full_config(
            log_entry=None,
            publish_did=publish_did_file,
            schema=None,
            credential_definition=None,
            db=db,
            delete_contents=True,
        )

    # Assert - verify updated_allowed is called AFTER commit
    db.commit.assert_called_once()
    mock_updated.assert_called_once_with(db)

    # Verify order: commit happens before updated_allowed
    # Check the order of method calls
    call_names = [call[0] for call in db.method_calls]
    commit_idx = call_names.index("commit")
    assert commit_idx >= 0  # Commit was called
    mock_updated.assert_called()  # updated_allowed was called


@pytest.mark.asyncio
async def test_update_full_config_only_deletes_provided_tables():
    """Test that only tables for provided files are deleted in replace mode."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)

    # Only provide schema file
    schema_content = "author_did,schema_name,version,details\n*,*,*,allow all"
    schema_file = create_mock_upload_file("schema.csv", schema_content)

    # Act
    with (
        patch("api.endpoints.routes.allow.update_allowed_config") as mock_update,
        patch("api.endpoints.routes.allow.updated_allowed") as mock_updated,
    ):
        mock_update.return_value = {"added": 1}

        await update_full_config(
            log_entry=None,
            publish_did=None,
            schema=schema_file,
            credential_definition=None,
            db=db,
            delete_contents=True,
        )

    # Assert - verify only one delete executed (for AllowedSchema)
    assert db.execute.call_count == 1
    mock_update.assert_called_once()


@pytest.mark.asyncio
async def test_update_full_config_mixed_files():
    """Test uploading a subset of files (log_entry and credential_definition)."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)

    log_entry_content = (
        "scid,domain,namespace,identifier,log_updates\ntest_scid,test.com,ns,id1,false"
    )
    creddef_content = "creddef_author_did,schema_issuer_did,schema_name,version,tag,details\ndid:ex:1,did:ex:2,Schema,1.0,default,test"

    log_entry_file = create_mock_upload_file("log_entry.csv", log_entry_content)
    creddef_file = create_mock_upload_file("creddef.csv", creddef_content)

    # Act
    with (
        patch("api.endpoints.routes.allow.update_allowed_config") as mock_update,
        patch("api.endpoints.routes.allow.updated_allowed") as mock_updated,
    ):
        mock_update.side_effect = [{"added": 1}, {"added": 1}]

        result = await update_full_config(
            log_entry=log_entry_file,
            publish_did=None,
            schema=None,
            credential_definition=creddef_file,
            db=db,
            delete_contents=True,
        )

    # Assert
    assert len(result) == 2
    assert "AllowedLogEntry" in result
    assert "AllowedCredentialDefinition" in result
    assert "AllowedPublicDid" not in result
    assert "AllowedSchema" not in result
    assert db.execute.call_count == 2


@pytest.mark.asyncio
async def test_update_full_config_rolls_back_on_error():
    """Test that update_full_config rolls back transaction if processing fails."""
    # Arrange
    db = AsyncMock(spec=AsyncSession)
    csv_content = "registered_did,details\ndid:example:123,test"
    publish_did_file = create_mock_upload_file("publish_did.csv", csv_content)

    # Act & Assert
    with (
        patch("api.endpoints.routes.allow.update_allowed_config") as mock_update,
        patch("api.endpoints.routes.allow.updated_allowed") as mock_updated,
    ):
        # Make update_allowed_config fail
        mock_update.side_effect = Exception("Processing failed")

        with pytest.raises(Exception) as exc_info:
            await update_full_config(
                log_entry=None,
                publish_did=publish_did_file,
                schema=None,
                credential_definition=None,
                db=db,
                delete_contents=True,
            )

        assert "Processing failed" in str(exc_info.value)
        db.rollback.assert_called_once()
        db.commit.assert_not_called()
        mock_updated.assert_not_called()  # Should not reprocess if commit failed
