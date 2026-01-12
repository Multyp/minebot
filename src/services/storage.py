"""
File storage service for persistent data management.
"""
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any


class StorageError(Exception):
    """Storage-related errors."""
    pass


class StorageService:
    """Handles file I/O operations for persistent data storage."""
    
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.logger = logging.getLogger(__name__)
        self._lock = asyncio.Lock()
    
    async def load(self) -> Dict[str, Any]:
        """Load data from file."""
        async with self._lock:
            try:
                if not self.file_path.exists():
                    self.logger.info(f"Storage file {self.file_path} does not exist, returning empty data")
                    return {}
                
                # Use asyncio to prevent blocking
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, self._read_file)
                
                self.logger.debug(f"Loaded data from {self.file_path}")
                return data
                
            except Exception as e:
                self.logger.error(f"Failed to load from {self.file_path}: {e}")
                raise StorageError(f"Failed to load data: {e}")
    
    async def save(self, data: Dict[str, Any]):
        """Save data to file."""
        async with self._lock:
            try:
                # Ensure directory exists
                self.file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Use asyncio to prevent blocking
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._write_file, data)
                
                self.logger.debug(f"Saved data to {self.file_path}")
                
            except Exception as e:
                self.logger.error(f"Failed to save to {self.file_path}: {e}")
                raise StorageError(f"Failed to save data: {e}")
    
    def _read_file(self) -> Dict[str, Any]:
        """Synchronous file read operation."""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _write_file(self, data: Dict[str, Any]):
        """Synchronous file write operation."""
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    async def backup(self, suffix: str = None):
        """Create a backup of the current file."""
        if not self.file_path.exists():
            return
        
        if suffix is None:
            from datetime import datetime
            suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        backup_path = self.file_path.with_suffix(f'.{suffix}.backup')
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._copy_file, backup_path)
            self.logger.info(f"Created backup: {backup_path}")
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            raise StorageError(f"Backup failed: {e}")
    
    def _copy_file(self, destination: Path):
        """Copy file to destination."""
        import shutil
        shutil.copy2(self.file_path, destination)
