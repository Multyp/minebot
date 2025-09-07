"""
Location management service with persistent storage.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional

from ..models.location import Location, Coordinates
from ..services.storage import StorageService
from ..utils.exceptions import LocationNotFoundError, InvalidLocationIndexError
from ..ipc.events import EventBus


class LocationManager:
    """Manages location data with persistent storage and event integration."""
    
    def __init__(self, data_dir: Path, event_bus: EventBus):
        self.data_dir = data_dir
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)
        
        self.storage = StorageService(data_dir / "locations.json")
        self._locations: Dict[str, Location] = {}
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize the location manager and load existing data."""
        try:
            data = await self.storage.load()
            await self._load_locations(data)
            
            total_instances = sum(loc.instance_count for loc in self._locations.values())
            self.logger.info(
                f'📍 Loaded {len(self._locations)} location types with {total_instances} total instances'
            )
            
            self.event_bus.emit('locations_loaded', {
                'location_count': len(self._locations),
                'total_instances': total_instances
            })
            
        except Exception as e:
            self.logger.error(f"Failed to initialize location manager: {e}")
            # Initialize with default data
            await self._create_default_locations()
    
    async def cleanup(self):
        """Cleanup resources."""
        await self._save_all()
    
    async def _create_default_locations(self):
        """Create default spider farm location."""
        default_coords = Coordinates(-135, 106, 408)
        spider_farm = Location("spider_farm")
        spider_farm.add_instance(default_coords, looted=False)
        
        self._locations["spider_farm"] = spider_farm
        await self._save_all()
        
        self.logger.info("Created default spider farm location")
    
    async def _load_locations(self, data: Dict):
        """Load locations from storage data."""
        async with self._lock:
            for name, location_data in data.items():
                # Handle legacy format conversion
                if isinstance(location_data, list) and len(location_data) > 0:
                    if isinstance(location_data[0], int):
                        # Legacy format: [x, y, z] -> New format
                        coords = Coordinates.from_list(location_data)
                        location = Location(name)
                        location.add_instance(coords, looted=False)
                        location_data = [{"coords": location_data, "looted": False}]
                
                location = Location.from_dict(name, location_data)
                self._locations[location.key] = location
    
    async def _save_all(self):
        """Save all locations to storage."""
        data = {name: loc.to_dict() for name, loc in self._locations.items()}
        await self.storage.save(data)
        
        self.event_bus.emit('locations_saved', {
            'location_count': len(self._locations)
        })
    
    # Public API methods
    
    async def get_location(self, name: str) -> Location:
        """Get location by name."""
        key = name.lower().replace(" ", "_")
        if key not in self._locations:
            raise LocationNotFoundError(name)
        return self._locations[key]
    
    async def get_all_locations(self) -> List[Location]:
        """Get all locations."""
        return list(self._locations.values())
    
    async def get_location_names(self) -> List[str]:
        """Get all location names."""
        return [loc.display_name for loc in self._locations.values()]
    
    async def location_exists(self, name: str) -> bool:
        """Check if location exists."""
        key = name.lower().replace(" ", "_")
        return key in self._locations
    
    async def add_location_instance(self, name: str, coordinates: Coordinates, looted: bool = False) -> int:
        """Add a new location instance."""
        async with self._lock:
            key = name.lower().replace(" ", "_")
            
            if key not in self._locations:
                self._locations[key] = Location(name)
            
            location = self._locations[key]
            instance_index = location.add_instance(coordinates, looted)
            
            await self._save_all()
            
            self.event_bus.emit('location_instance_added', {
                'location_name': name,
                'instance_index': instance_index,
                'coordinates': coordinates,
                'looted': looted
            })
            
            return instance_index
    
    async def remove_location_instance(self, name: str, index: Optional[int] = None) -> tuple:
        """Remove location instance(s). Returns (removed_instances, remaining_count)."""
        async with self._lock:
            location = await self.get_location(name)
            
            if index is not None:
                # Remove specific instance
                if index < 1 or index > location.instance_count:
                    raise InvalidLocationIndexError(name, index, location.instance_count)
                
                removed_instance = location.remove_instance(index)
                
                # Remove entire location if no instances left
                if location.instance_count == 0:
                    del self._locations[location.key]
                
                await self._save_all()
                
                self.event_bus.emit('location_instance_removed', {
                    'location_name': name,
                    'instance_index': index,
                    'coordinates': removed_instance.coordinates
                })
                
                return ([removed_instance], location.instance_count)
            
            else:
                # Remove entire location
                removed_instances = location.instances.copy()
                instance_count = location.instance_count
                del self._locations[location.key]
                
                await self._save_all()
                
                self.event_bus.emit('location_removed', {
                    'location_name': name,
                    'instance_count': instance_count
                })
                
                return (removed_instances, 0)
    
    async def update_location_status(self, name: str, looted: bool, index: Optional[int] = None) -> tuple:
        """Update location loot status. Returns (old_status, new_status)."""
        async with self._lock:
            location = await self.get_location(name)
            
            # Determine target instance
            if location.instance_count > 1 and index is None:
                raise ValueError("Index required for locations with multiple instances")
            
            target_index = index if index is not None else 1
            
            if target_index < 1 or target_index > location.instance_count:
                raise InvalidLocationIndexError(name, target_index, location.instance_count)
            
            instance = location.get_instance(target_index)
            old_status = instance.looted
            instance.looted = looted
            
            await self._save_all()
            
            self.event_bus.emit('location_status_updated', {
                'location_name': name,
                'instance_index': target_index,
                'old_looted': old_status,
                'new_looted': looted,
                'coordinates': instance.coordinates
            })
            
            return (old_status, looted)
    
    async def get_location_stats(self) -> Dict:
        """Get overall location statistics."""
        total_locations = len(self._locations)
        total_instances = sum(loc.instance_count for loc in self._locations.values())
        total_available = sum(loc.available_count for loc in self._locations.values())
        total_looted = sum(loc.looted_count for loc in self._locations.values())
        
        return {
            'location_types': total_locations,
            'total_instances': total_instances,
            'available': total_available,
            'looted': total_looted
        }
    
    async def search_locations(self, query: str) -> List[Location]:
        """Search locations by name (case-insensitive)."""
        query_lower = query.lower()
        matching_locations = []
        
        for location in self._locations.values():
            if query_lower in location.display_name.lower():
                matching_locations.append(location)
        
        return matching_locations
    
    async def get_available_locations(self) -> List[Location]:
        """Get locations that have at least one available (unlooted) instance."""
        available_locations = []
        
        for location in self._locations.values():
            if location.available_count > 0:
                available_locations.append(location)
        
        return available_locations
    
    async def backup_data(self) -> bool:
        """Create a backup of location data."""
        try:
            await self.storage.backup()
            self.event_bus.emit('locations_backed_up', {
                'location_count': len(self._locations)
            })
            return True
        except Exception as e:
            self.logger.error(f"Failed to backup location data: {e}")
            return False
