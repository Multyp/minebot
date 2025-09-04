import json
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class LocationEntry:
    """Represents a single location entry with coordinates and loot status"""
    coords: List[int]
    looted: bool = False
    
    def __post_init__(self):
        """Validate coordinates after initialization"""
        if len(self.coords) != 3:
            raise ValueError("Coordinates must have exactly 3 values [x, y, z]")
    
    @property
    def x(self) -> int:
        return self.coords[0]
    
    @property
    def y(self) -> int:
        return self.coords[1]
    
    @property
    def z(self) -> int:
        return self.coords[2]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {"coords": self.coords, "looted": self.looted}
    
    @classmethod
    def from_dict(cls, data: dict) -> "LocationEntry":
        """Create LocationEntry from dictionary"""
        return cls(coords=data["coords"], looted=data.get("looted", False))

class LocationManager:
    """Manages all location data and operations"""
    
    def __init__(self, locations_file: str):
        self.locations_file = locations_file
        self.locations: Dict[str, List[LocationEntry]] = {}
        self.load_locations()
    
    def load_locations(self) -> None:
        """Load locations from file with backward compatibility"""
        if os.path.exists(self.locations_file):
            try:
                with open(self.locations_file, 'r') as f:
                    data = json.load(f)
                
                # Convert data to LocationEntry objects
                converted_data = {}
                for name, coords_data in data.items():
                    if isinstance(coords_data, list):
                        if len(coords_data) > 0 and isinstance(coords_data[0], int):
                            # Old format: [x, y, z] -> New format
                            converted_data[name] = [LocationEntry(coords=coords_data, looted=False)]
                        else:
                            # New format: list of dicts
                            converted_data[name] = [
                                LocationEntry.from_dict(entry) if isinstance(entry, dict)
                                else LocationEntry(coords=entry, looted=False)
                                for entry in coords_data
                            ]
                    else:
                        # Handle other formats gracefully
                        converted_data[name] = [LocationEntry(coords=[0, 0, 0], looted=False)]
                
                self.locations = converted_data
                
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"Error loading locations file: {e}")
                self._create_default_locations()
        else:
            self._create_default_locations()
    
    def _create_default_locations(self) -> None:
        """Create default locations if file doesn't exist or is corrupted"""
        self.locations = {
            "spider_farm": [LocationEntry(coords=[-135, 106, 408], looted=False)]
        }
        self.save_locations()
    
    def save_locations(self) -> None:
        """Save locations to file"""
        try:
            data = {
                name: [entry.to_dict() for entry in entries]
                for name, entries in self.locations.items()
            }
            
            with open(self.locations_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except (IOError, json.JSONEncodeError) as e:
            print(f"Error saving locations file: {e}")
    
    def normalize_name(self, name: str) -> str:
        """Normalize location name for consistent storage"""
        return name.lower().replace(" ", "_")
    
    def get_location(self, name: str) -> Optional[List[LocationEntry]]:
        """Get all entries for a location"""
        normalized_name = self.normalize_name(name)
        return self.locations.get(normalized_name)
    
    def get_location_entry(self, name: str, index: int) -> Optional[LocationEntry]:
        """Get specific location entry by index (1-based)"""
        location_data = self.get_location(name)
        if location_data and 1 <= index <= len(location_data):
            return location_data[index - 1]
        return None
    
    def add_location(self, name: str, x: int, y: int, z: int, looted: bool = False) -> Tuple[int, LocationEntry]:
        """Add a new location entry. Returns (instance_number, entry)"""
        normalized_name = self.normalize_name(name)
        new_entry = LocationEntry(coords=[x, y, z], looted=looted)
        
        if normalized_name in self.locations:
            self.locations[normalized_name].append(new_entry)
        else:
            self.locations[normalized_name] = [new_entry]
        
        self.save_locations()
        return len(self.locations[normalized_name]), new_entry
    
    def remove_location(self, name: str, index: Optional[int] = None) -> Tuple[bool, str, int]:
        """
        Remove location or specific instance.
        Returns (success, message, instances_removed)
        """
        normalized_name = self.normalize_name(name)
        
        if normalized_name not in self.locations:
            return False, f"Location `{name}` doesn't exist", 0
        
        if index is not None:
            # Remove specific instance
            location_data = self.locations[normalized_name]
            if index < 1 or index > len(location_data):
                return False, f"Invalid index. Location has {len(location_data)} instances", 0
            
            location_data.pop(index - 1)
            
            # Remove entire location if no instances left
            if not location_data:
                del self.locations[normalized_name]
            
            self.save_locations()
            return True, f"Removed instance #{index}", 1
        else:
            # Remove entire location
            instance_count = len(self.locations[normalized_name])
            del self.locations[normalized_name]
            self.save_locations()
            return True, f"Removed entire location", instance_count
    
    def update_loot_status(self, name: str, looted: bool, index: Optional[int] = None) -> Tuple[bool, str, Optional[bool]]:
        """
        Update loot status for a location.
        Returns (success, message, old_status)
        """
        normalized_name = self.normalize_name(name)
        
        if normalized_name not in self.locations:
            return False, f"Location `{name}` doesn't exist", None
        
        location_data = self.locations[normalized_name]
        
        # Require index if multiple instances exist
        if len(location_data) > 1 and index is None:
            return False, f"Multiple instances found. Please specify index (1-{len(location_data)})", None
        
        # Determine target index
        target_index = (index - 1) if index is not None else 0
        
        if target_index < 0 or target_index >= len(location_data):
            return False, f"Invalid index. Use 1-{len(location_data)}", None
        
        old_status = location_data[target_index].looted
        location_data[target_index].looted = looted
        self.save_locations()
        
        return True, "Status updated successfully", old_status
    
    def get_all_locations(self) -> Dict[str, List[LocationEntry]]:
        """Get all locations"""
        return self.locations.copy()
    
    def get_statistics(self) -> Tuple[int, int, int, int]:
        """Get location statistics. Returns (location_types, total_instances, available, looted)"""
        location_types = len(self.locations)
        total_instances = sum(len(entries) for entries in self.locations.values())
        available = sum(1 for entries in self.locations.values() for entry in entries if not entry.looted)
        looted = total_instances - available
        
        return location_types, total_instances, available, looted
