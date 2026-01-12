"""
Data models for location management.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple


@dataclass
class Coordinates:
    """3D coordinates in a world or map."""
    x: int
    y: int
    z: int
    
    def __iter__(self):
        """Allow unpacking: x, y, z = coordinates"""
        return iter((self.x, self.y, self.z))
    
    def __str__(self) -> str:
        return f"{self.x}, {self.y}, {self.z}"
    
    @property
    def teleport_command(self) -> str:
        """Generate teleport command for these coordinates."""
        return f"/tp {self.x} {self.y} {self.z}"
    
    @classmethod
    def from_list(cls, coords: List[int]) -> 'Coordinates':
        """Create coordinates from list [x, y, z]."""
        if len(coords) != 3:
            raise ValueError("Coordinates must have exactly 3 values")
        return cls(x=coords[0], y=coords[1], z=coords[2])


@dataclass
class LocationInstance:
    """A single instance of a location (e.g., one ocean monument)."""
    coordinates: Coordinates
    looted: bool = False
    
    @property
    def status_emoji(self) -> str:
        """Get emoji representation of loot status."""
        return "🏴‍☠️" if self.looted else "💎"
    
    @property
    def status_text(self) -> str:
        """Get text representation of loot status."""
        return "Looted" if self.looted else "Available"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "coords": [self.coordinates.x, self.coordinates.y, self.coordinates.z],
            "looted": self.looted
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'LocationInstance':
        """Create from dictionary (JSON deserialization)."""
        coords = Coordinates.from_list(data["coords"])
        looted = data.get("looted", False)
        return cls(coordinates=coords, looted=looted)


@dataclass
class Location:
    """A location type with multiple instances (e.g., all ocean monuments)."""
    name: str
    instances: List[LocationInstance] = field(default_factory=list)
    
    @property
    def key(self) -> str:
        """Normalized key for storage."""
        return self.name.lower().replace(" ", "_")
    
    @property
    def display_name(self) -> str:
        """Human-readable display name."""
        return self.name.replace("_", " ").title()
    
    @property
    def instance_count(self) -> int:
        """Total number of instances."""
        return len(self.instances)
    
    @property
    def available_count(self) -> int:
        """Number of unlooted instances."""
        return sum(1 for instance in self.instances if not instance.looted)
    
    @property
    def looted_count(self) -> int:
        """Number of looted instances."""
        return sum(1 for instance in self.instances if instance.looted)
    
    def add_instance(self, coordinates: Coordinates, looted: bool = False) -> int:
        """Add new instance and return its index (1-based)."""
        instance = LocationInstance(coordinates=coordinates, looted=looted)
        self.instances.append(instance)
        return len(self.instances)
    
    def get_instance(self, index: int) -> LocationInstance:
        """Get instance by 1-based index."""
        if index < 1 or index > len(self.instances):
            raise IndexError(f"Index {index} out of range for {self.name}")
        return self.instances[index - 1]
    
    def remove_instance(self, index: int) -> LocationInstance:
        """Remove and return instance by 1-based index."""
        if index < 1 or index > len(self.instances):
            raise IndexError(f"Index {index} out of range for {self.name}")
        return self.instances.pop(index - 1)
    
    def to_dict(self) -> List[Dict]:
        """Convert to list of dictionaries for JSON serialization."""
        return [instance.to_dict() for instance in self.instances]
    
    @classmethod
    def from_dict(cls, name: str, data: List[Dict]) -> 'Location':
        """Create from dictionary list (JSON deserialization)."""
        instances = [LocationInstance.from_dict(item) for item in data]
        return cls(name=name, instances=instances)
