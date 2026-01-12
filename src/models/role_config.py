"""
Data models for role configuration.
"""
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class RoleConfig:
    """Configuration for a single assignable role."""
    role_id: int
    role_name: str
    emoji: str
    description: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "role_id": self.role_id,
            "role_name": self.role_name,
            "emoji": self.emoji,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'RoleConfig':
        """Create from dictionary (JSON deserialization)."""
        return cls(
            role_id=data["role_id"],
            role_name=data["role_name"],
            emoji=data["emoji"],
            description=data["description"]
        )


@dataclass
class RoleMessage:
    """Represents a role assignment message."""
    message_id: int
    channel_id: int
    roles: List[RoleConfig]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "message_id": self.message_id,
            "channel_id": self.channel_id,
            "roles": [role.to_dict() for role in self.roles]
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'RoleMessage':
        """Create from dictionary (JSON deserialization)."""
        return cls(
            message_id=data["message_id"],
            channel_id=data["channel_id"],
            roles=[RoleConfig.from_dict(role) for role in data["roles"]]
        )
