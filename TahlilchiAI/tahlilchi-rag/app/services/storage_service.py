"""File storage service for managing document uploads."""

from pathlib import Path
from uuid import UUID


class StorageService:
    """
    Handles physical file storage (local filesystem for now, easy to swap to S3 later).

    Files are organized in a tenant/chat hierarchy:
    ./data/uploads/{tenant_id}/{chat_id}/{file_id}_{filename}
    """

    def __init__(self, base_path: str = "./data/uploads"):
        """
        Initialize storage service.

        Args:
            base_path: Base directory for file uploads
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save_file(
        self,
        tenant_id: UUID,
        chat_id: UUID,
        file_id: UUID,
        file_content: bytes,
        filename: str,
    ) -> str:
        """
        Save uploaded file to disk with organized structure.

        Args:
            tenant_id: Tenant ID for isolation
            chat_id: Chat ID the document belongs to
            file_id: Unique file/document ID
            file_content: File bytes
            filename: Original filename

        Returns:
            str: Relative file path (for storing in database)
        """
        # Create tenant/chat directory structure
        tenant_dir = self.base_path / str(tenant_id)
        chat_dir = tenant_dir / str(chat_id)
        chat_dir.mkdir(parents=True, exist_ok=True)

        safe_name = Path(filename).name

        # Save file with UUID prefix to avoid name collisions
        file_path = chat_dir / f"{file_id}_{safe_name}"

        with open(file_path, "wb") as f:
            f.write(file_content)

        # Return relative path for DB storage
        return str(file_path.relative_to(self.base_path))

    def get_file_path(self, relative_path: str) -> Path:
        """
        Convert relative path to absolute path.

        Args:
            relative_path: Relative path from database

        Returns:
            Path: Absolute path to file
        """
        return self.base_path / relative_path

    def delete_file(self, relative_path: str) -> bool:
        """
        Delete a file from storage.

        Args:
            relative_path: Relative path from database

        Returns:
            bool: True if file was deleted, False if not found
        """
        full_path = self.get_file_path(relative_path)
        if full_path.exists():
            full_path.unlink()
            return True
        return False

    def file_exists(self, relative_path: str) -> bool:
        """
        Check if a file exists.

        Args:
            relative_path: Relative path from database

        Returns:
            bool: True if file exists
        """
        return self.get_file_path(relative_path).exists()

    def get_file_size(self, relative_path: str) -> int | None:
        """
        Get file size in bytes.

        Args:
            relative_path: Relative path from database

        Returns:
            int | None: File size in bytes, or None if not found
        """
        full_path = self.get_file_path(relative_path)
        if full_path.exists():
            return full_path.stat().st_size
        return None
