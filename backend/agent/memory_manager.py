"""
Memory management for the financial advisor agent
Implements STM (Short-Term Memory) and LTM (Long-Term Memory)
"""

import json
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class ConversationBuffer:
    """Short-Term Memory - Stores recent conversation context"""

    def __init__(self, max_messages: int = 20):
        self.max_messages = max_messages
        self.messages = []

    def add_message(self, role: str, content: str, metadata: Dict = None):
        """Add message to conversation buffer"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self.messages.append(message)

        # Keep only recent messages
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    def get_conversation_history(self, last_n: int = 10) -> List[Dict]:
        """Get recent conversation history"""
        return self.messages[-last_n:]

    def get_context(self) -> str:
        """Get formatted conversation context for LLM"""
        context = "## Historial de Conversación Reciente:\n"
        for msg in self.messages[-5:]:
            role = "Usuario" if msg["role"] == "user" else "Asistente"
            context += f"\n{role}: {msg['content']}"
        return context

    def clear(self):
        """Clear conversation history"""
        self.messages = []


class ConversationSummary:
    """
    Conversation Summary Memory
    Summarizes long conversations to preserve key information
    """

    def __init__(self):
        self.summary = ""
        self.key_decisions = []
        self.client_preferences = {}
        self.last_updated = None

    def update_summary(self, new_content: str):
        """Update conversation summary"""
        self.summary = new_content
        self.last_updated = datetime.now().isoformat()

    def add_key_decision(self, decision: str, timestamp: datetime = None):
        """Record important decision made in conversation"""
        self.key_decisions.append({
            "decision": decision,
            "timestamp": (timestamp or datetime.now()).isoformat()
        })

    def add_preference(self, key: str, value):
        """Record client preference discovered during conversation"""
        self.client_preferences[key] = value

    def get_summary(self) -> str:
        """Get conversation summary"""
        return self.summary

    def to_dict(self) -> Dict:
        """Serialize to dictionary"""
        return {
            "summary": self.summary,
            "key_decisions": self.key_decisions,
            "client_preferences": self.client_preferences,
            "last_updated": self.last_updated
        }


class ClientProfile:
    """
    Long-Term Memory - Stores client financial profile
    Persisted across conversations
    """

    def __init__(self, client_id: str):
        self.client_id = client_id
        self.profile_data = {
            "client_id": client_id,
            "risk_profile": None,
            "investment_horizon_months": None,
            "available_amount_usd": None,
            "liquidity_preference": None,
            "target_return_pct": None,
            "max_aggressive_pct": 40,
            "investment_experience": "low",
            "goals": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        self.portfolio_history = []
        self.recommendations_history = []

    def update_profile(self, **kwargs):
        """Update profile fields"""
        for key, value in kwargs.items():
            if key in self.profile_data:
                self.profile_data[key] = value
        self.profile_data["updated_at"] = datetime.now().isoformat()

    def add_recommendation(self, recommendation: Dict):
        """Add recommendation to history"""
        recommendation["timestamp"] = datetime.now().isoformat()
        self.recommendations_history.append(recommendation)

    def get_last_recommendation(self) -> Optional[Dict]:
        """Get most recent recommendation"""
        return self.recommendations_history[-1] if self.recommendations_history else None

    def add_portfolio(self, portfolio: Dict):
        """Add portfolio allocation to history"""
        portfolio["timestamp"] = datetime.now().isoformat()
        self.portfolio_history.append(portfolio)

    def get_current_portfolio(self) -> Optional[Dict]:
        """Get current portfolio"""
        return self.portfolio_history[-1] if self.portfolio_history else None

    def to_dict(self) -> Dict:
        """Serialize profile to dictionary"""
        return {
            "profile_data": self.profile_data,
            "portfolio_history": self.portfolio_history,
            "recommendations_history": self.recommendations_history
        }

    @staticmethod
    def from_dict(data: Dict) -> "ClientProfile":
        """Deserialize profile from dictionary"""
        profile = ClientProfile(data["profile_data"]["client_id"])
        profile.profile_data = data["profile_data"]
        profile.portfolio_history = data.get("portfolio_history", [])
        profile.recommendations_history = data.get("recommendations_history", [])
        return profile


class MemoryManager:
    """
    Unified memory manager for STM and LTM
    Orchestrates both conversation and client profile memory
    """

    def __init__(self, client_id: str):
        self.client_id = client_id
        self.stm = ConversationBuffer(max_messages=30)
        self.conversation_summary = ConversationSummary()
        self.ltm = ClientProfile(client_id)

    def add_user_message(self, content: str, metadata: Dict = None):
        """Add user message to STM"""
        self.stm.add_message("user", content, metadata)

    def add_assistant_message(self, content: str, metadata: Dict = None):
        """Add assistant message to STM"""
        self.stm.add_message("assistant", content, metadata)

    def get_conversation_context(self) -> str:
        """Get context for LLM from both STM and summary"""
        stm_context = self.stm.get_context()
        summary = self.conversation_summary.get_summary()

        context = stm_context
        if summary:
            context = f"## Resumen de Conversaciones Anteriores:\n{summary}\n\n{stm_context}"

        return context

    def get_client_memory(self) -> Dict:
        """Get client profile for agent reasoning"""
        return self.ltm.profile_data

    def update_client_profile(self, **kwargs):
        """Update long-term client profile"""
        self.ltm.update_profile(**kwargs)

    def save_recommendation_to_ltm(self, recommendation: Dict):
        """Save recommendation to long-term memory"""
        self.ltm.add_recommendation(recommendation)

    def summarize_conversation(self, conversation_history: List[Dict]):
        """
        Generate summary of conversation (could be done with LLM in production)
        """
        key_points = []
        for msg in conversation_history:
            if msg["role"] == "user":
                key_points.append(f"Usuario mencionó: {msg['content'][:100]}")
            elif "recomendación" in msg["content"].lower():
                key_points.append(f"Recomendación: {msg['content'][:150]}")

        summary = "\n".join(key_points[-5:])  # Keep last 5 key points
        self.conversation_summary.update_summary(summary)

    def to_dict(self) -> Dict:
        """Serialize entire memory state"""
        return {
            "client_id": self.client_id,
            "stm": {
                "messages": self.stm.messages
            },
            "conversation_summary": self.conversation_summary.to_dict(),
            "ltm": self.ltm.to_dict()
        }

    @staticmethod
    def from_dict(data: Dict) -> "MemoryManager":
        """Deserialize memory from dictionary"""
        mgr = MemoryManager(data["client_id"])

        # Restore STM
        mgr.stm.messages = data.get("stm", {}).get("messages", [])

        # Restore conversation summary
        summary_data = data.get("conversation_summary", {})
        mgr.conversation_summary.summary = summary_data.get("summary", "")
        mgr.conversation_summary.key_decisions = summary_data.get("key_decisions", [])
        mgr.conversation_summary.client_preferences = summary_data.get("client_preferences", {})

        # Restore LTM
        ltm_data = data.get("ltm", {})
        if ltm_data:
            mgr.ltm = ClientProfile.from_dict(ltm_data)

        return mgr


class DynamoDBMemoryStore:
    """
    Storage backend for memory using AWS DynamoDB
    Implements persistence of client profiles and conversation summaries
    """

    def __init__(self, table_name: str = "fintech-memories"):
        self.table_name = table_name
        # In production, initialize DynamoDB client
        # self.dynamodb = boto3.resource('dynamodb')
        # self.table = self.dynamodb.Table(table_name)

    def save_memory(self, client_id: str, memory_state: Dict):
        """Save memory state to DynamoDB"""
        # In production:
        # item = {
        #     "client_id": client_id,
        #     "timestamp": datetime.now().isoformat(),
        #     "memory_state": json.dumps(memory_state),
        #     "ttl": int(time.time()) + (30 * 24 * 60 * 60)  # 30 days
        # }
        # self.table.put_item(Item=item)
        pass

    def load_memory(self, client_id: str) -> Optional[Dict]:
        """Load memory state from DynamoDB"""
        # In production:
        # response = self.table.query(
        #     KeyConditionExpression=Key('client_id').eq(client_id),
        #     ScanIndexForward=False,
        #     Limit=1
        # )
        # if response['Items']:
        #     return json.loads(response['Items'][0]['memory_state'])
        return None

    def save_ltm(self, client_id: str, profile: ClientProfile):
        """Save long-term profile to permanent storage"""
        # Implement actual persistence
        pass

    def load_ltm(self, client_id: str) -> Optional[ClientProfile]:
        """Load long-term profile from permanent storage"""
        # Implement actual retrieval
        return None
