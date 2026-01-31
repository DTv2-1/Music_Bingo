"""
Google Cloud Storage Service
Handles file uploads, downloads, and management with GCS
"""

import logging
from typing import Optional, BinaryIO
from pathlib import Path

from google.cloud import storage

from ..utils.config import GCS_BUCKET_NAME

logger = logging.getLogger(__name__)


class GCSStorageService:
    """
    Service for Google Cloud Storage operations
    
    Features:
    - File upload with public URLs
    - Automatic bucket configuration
    - Error handling and logging
    - Support for both file paths and bytes
    """
    
    def __init__(self, bucket_name: Optional[str] = None):
        """
        Initialize GCS Storage Service
        
        Args:
            bucket_name: GCS bucket name (defaults to config value)
        """
        self.bucket_name = bucket_name or GCS_BUCKET_NAME
        self.client = None
        self.bucket = None
    
    def _get_client(self):
        """Lazy initialization of storage client"""
        if self.client is None:
            self.client = storage.Client()
        return self.client
    
    def _get_bucket(self):
        """Lazy initialization of bucket"""
        if self.bucket is None:
            client = self._get_client()
            self.bucket = client.bucket(self.bucket_name)
        return self.bucket
    
    def upload_file(self, local_file_path: str, destination_blob_name: str, make_public: bool = True) -> str:
        """
        Upload a file to Google Cloud Storage and return a public URL
        Files are auto-deleted after 7 days via bucket lifecycle policy
        
        Args:
            local_file_path: Path to local file to upload
            destination_blob_name: Destination path in GCS bucket
            make_public: Whether to make the blob publicly readable (default: True)
        
        Returns:
            str: Public URL of uploaded file
            
        Raises:
            Exception: If upload fails
            
        Example:
            >>> service = GCSStorageService()
            >>> url = service.upload_file('/tmp/file.pdf', 'cards/file.pdf')
            >>> print(url)
            'https://storage.googleapis.com/bucket/cards/file.pdf'
        """
        try:
            bucket = self._get_bucket()
            blob = bucket.blob(destination_blob_name)
            
            # Upload the file
            blob.upload_from_filename(local_file_path)
            logger.info(f"✅ Uploaded {local_file_path} to gs://{self.bucket_name}/{destination_blob_name}")
            
            # Make blob publicly readable if requested
            if make_public:
                blob.make_public()
                logger.info(f"✅ Made blob public: {blob.public_url}")
            
            # Return public URL
            return blob.public_url
            
        except Exception as e:
            logger.error(f"❌ Failed to upload to GCS: {e}")
            raise
    
    def upload_bytes(
        self, 
        file_bytes: bytes, 
        destination_blob_name: str, 
        content_type: str = 'application/octet-stream',
        make_public: bool = True
    ) -> str:
        """
        Upload bytes directly to GCS without saving to disk
        
        Args:
            file_bytes: File content as bytes
            destination_blob_name: Destination path in GCS bucket
            content_type: MIME type of the file
            make_public: Whether to make the blob publicly readable
        
        Returns:
            str: Public URL of uploaded file
            
        Example:
            >>> service = GCSStorageService()
            >>> url = service.upload_bytes(b'data', 'file.txt', 'text/plain')
        """
        try:
            bucket = self._get_bucket()
            blob = bucket.blob(destination_blob_name)
            blob.content_type = content_type
            
            # Upload bytes
            blob.upload_from_string(file_bytes)
            logger.info(f"✅ Uploaded {len(file_bytes)} bytes to gs://{self.bucket_name}/{destination_blob_name}")
            
            # Make public if requested
            if make_public:
                blob.make_public()
                logger.info(f"✅ Made blob public: {blob.public_url}")
            
            return blob.public_url
            
        except Exception as e:
            logger.error(f"❌ Failed to upload bytes to GCS: {e}")
            raise
    
    def delete_file(self, blob_name: str) -> bool:
        """
        Delete a file from GCS
        
        Args:
            blob_name: Name of the blob to delete
            
        Returns:
            bool: True if deleted successfully
            
        Example:
            >>> service = GCSStorageService()
            >>> service.delete_file('cards/old_file.pdf')
        """
        try:
            bucket = self._get_bucket()
            blob = bucket.blob(blob_name)
            blob.delete()
            logger.info(f"✅ Deleted {blob_name} from gs://{self.bucket_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to delete from GCS: {e}")
            return False
    
    def file_exists(self, blob_name: str) -> bool:
        """
        Check if a file exists in GCS
        
        Args:
            blob_name: Name of the blob to check
            
        Returns:
            bool: True if file exists
        """
        try:
            bucket = self._get_bucket()
            blob = bucket.blob(blob_name)
            return blob.exists()
        except Exception as e:
            logger.error(f"❌ Error checking file existence: {e}")
            return False
    
    def get_signed_url(self, blob_name: str, expiration_seconds: int = 3600) -> str:
        """
        Generate a signed URL with expiration time
        
        Args:
            blob_name: Name of the blob
            expiration_seconds: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            str: Signed URL
            
        Example:
            >>> service = GCSStorageService()
            >>> url = service.get_signed_url('private/file.pdf', 7200)
        """
        try:
            from datetime import timedelta
            
            bucket = self._get_bucket()
            blob = bucket.blob(blob_name)
            
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=expiration_seconds),
                method="GET"
            )
            
            logger.info(f"✅ Generated signed URL for {blob_name} (expires in {expiration_seconds}s)")
            return url
            
        except Exception as e:
            logger.error(f"❌ Failed to generate signed URL: {e}")
            raise


# Convenience function for backward compatibility with existing code
def upload_to_gcs(local_file_path: str, destination_blob_name: str) -> str:
    """
    Legacy function wrapper for backward compatibility
    Upload a file to Google Cloud Storage and return a public URL
    
    Args:
        local_file_path: Path to local file
        destination_blob_name: Destination path in bucket
        
    Returns:
        str: Public URL of uploaded file
    """
    service = GCSStorageService()
    return service.upload_file(local_file_path, destination_blob_name)
