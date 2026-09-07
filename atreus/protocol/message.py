from dataclasses import dataclass, field
from typing import Any


@dataclass
class AtreusMessage:
    sender: str
    receiver: str
    command: str
    payload: dict[str, Any] = field(default_factory=dict)

    def encode(self) -> dict:
        return {
            "protocol": "ATREUS/0.2",
            "sender": self.sender,
            "receiver": self.receiver,
            "command": self.command,
            "payload": self.payload,
        }

    @classmethod
    def decode(cls, message: dict) -> "AtreusMessage":
        if message.get("protocol") != "ATREUS/0.2":
            raise ValueError("Invalid Atreus protocol version")

        return cls(
            sender=message["sender"],
            receiver=message["receiver"],
            command=message["command"],
            payload=message.get("payload", {}),
        )
