import json
import os
from typing import Sequence, List, Dict, Optional, Any
from datetime import datetime
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict


def get_history(session_id):
    return FileChatMessageHistory(session_id, "./chat_history")


class LegalConversationState:
    """法律对话状态结构"""

    def __init__(
        self,
        session_id: str,
        current_legal_relations: Optional[List[str]] = None,
        confirmed_provisions: Optional[List[str]] = None,
        discussion_topics: Optional[List[str]] = None,
        related_cases: Optional[List[str]] = None,
        session_start: Optional[str] = None,
        last_update: Optional[str] = None
    ):
        self.session_id = session_id
        self.current_legal_relations = current_legal_relations or []
        self.confirmed_provisions = confirmed_provisions or []
        self.discussion_topics = discussion_topics or []
        self.related_cases = related_cases or []
        self.session_start = session_start or datetime.now().isoformat()
        self.last_update = last_update or datetime.now().isoformat()

    def add_legal_relation(self, relation: str) -> None:
        """添加法律关系类型"""
        if relation not in self.current_legal_relations:
            self.current_legal_relations.append(relation)
            self.last_update = datetime.now().isoformat()

    def add_confirmed_provision(self, provision: str) -> None:
        """添加已确认适用的法条"""
        if provision not in self.confirmed_provisions:
            self.confirmed_provisions.append(provision)
            self.last_update = datetime.now().isoformat()

    def add_discussion_topic(self, topic: str) -> None:
        """添加讨论话题"""
        if topic not in self.discussion_topics:
            self.discussion_topics.append(topic)
            self.last_update = datetime.now().isoformat()

    def add_related_case(self, case_id: str) -> None:
        """添加相关案例"""
        if case_id not in self.related_cases:
            self.related_cases.append(case_id)
            self.last_update = datetime.now().isoformat()

    def remove_legal_relation(self, relation: str) -> None:
        """移除法律关系类型"""
        if relation in self.current_legal_relations:
            self.current_legal_relations.remove(relation)
            self.last_update = datetime.now().isoformat()

    def get_summary(self) -> str:
        """获取状态摘要"""
        summary_parts = []
        if self.current_legal_relations:
            summary_parts.append(f"法律关系: {', '.join(self.current_legal_relations)}")
        if self.confirmed_provisions:
            summary_parts.append(f"适用法条: {', '.join([f'第{p}条' for p in self.confirmed_provisions])}")
        if self.discussion_topics:
            summary_parts.append(f"讨论话题: {', '.join(self.discussion_topics[:3])}")
        return "\n".join(summary_parts) if summary_parts else "暂无记录"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "current_legal_relations": self.current_legal_relations,
            "confirmed_provisions": self.confirmed_provisions,
            "discussion_topics": self.discussion_topics,
            "related_cases": self.related_cases,
            "session_start": self.session_start,
            "last_update": self.last_update
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LegalConversationState":
        """从字典创建"""
        return cls(
            session_id=data.get("session_id", ""),
            current_legal_relations=data.get("current_legal_relations", []),
            confirmed_provisions=data.get("confirmed_provisions", []),
            discussion_topics=data.get("discussion_topics", []),
            related_cases=data.get("related_cases", []),
            session_start=data.get("session_start"),
            last_update=data.get("last_update")
        )


class LegalConversationStateManager:
    """法律对话状态管理器"""

    def __init__(self, storage_path: str = "./legal_state"):
        self.storage_path = storage_path
        os.makedirs(self.storage_path, exist_ok=True)

    def _get_state_file_path(self, session_id: str) -> str:
        """获取状态文件路径"""
        safe_session_id = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in session_id)
        return os.path.join(self.storage_path, f"state_{safe_session_id}.json")

    def save_state(self, state: LegalConversationState) -> None:
        """保存状态到文件"""
        file_path = self._get_state_file_path(state.session_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)

    def load_state(self, session_id: str) -> Optional[LegalConversationState]:
        """从文件加载状态"""
        file_path = self._get_state_file_path(session_id)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return LegalConversationState.from_dict(data)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def delete_state(self, session_id: str) -> None:
        """删除状态文件"""
        file_path = self._get_state_file_path(session_id)
        if os.path.exists(file_path):
            os.remove(file_path)

    def get_or_create_state(self, session_id: str) -> LegalConversationState:
        """获取或创建状态"""
        state = self.load_state(session_id)
        if state is None:
            state = LegalConversationState(session_id=session_id)
            self.save_state(state)
        return state


class FileChatMessageHistory(BaseChatMessageHistory):
    """文件存储的聊天历史"""

    def __init__(self, session_id: str, storage_path: str):
        self.session_id = session_id
        self.storage_path = storage_path
        self.file_path = os.path.join(self.storage_path, self.session_id)

        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

        self.state_manager = LegalConversationStateManager()
        self._legal_state: Optional[LegalConversationState] = None

    @property
    def legal_state(self) -> LegalConversationState:
        """获取法律对话状态"""
        if self._legal_state is None:
            self._legal_state = self.state_manager.get_or_create_state(self.session_id)
        return self._legal_state

    def save_legal_state(self) -> None:
        """保存法律对话状态"""
        if self._legal_state is not None:
            self.state_manager.save_state(self._legal_state)

    def add_legal_relation(self, relation: str) -> None:
        """添加法律关系类型"""
        self.legal_state.add_legal_relation(relation)
        self.save_legal_state()

    def add_confirmed_provision(self, provision: str) -> None:
        """添加已确认适用的法条"""
        self.legal_state.add_confirmed_provision(provision)
        self.save_legal_state()

    def add_discussion_topic(self, topic: str) -> None:
        """添加讨论话题"""
        self.legal_state.add_discussion_topic(topic)
        self.save_legal_state()

    def add_related_case(self, case_id: str) -> None:
        """添加相关案例"""
        self.legal_state.add_related_case(case_id)
        self.save_legal_state()

    def get_legal_state_summary(self) -> str:
        """获取法律状态摘要"""
        return self.legal_state.get_summary()

    def clear_legal_state(self) -> None:
        """清除法律对话状态"""
        self.state_manager.delete_state(self.session_id)
        self._legal_state = None

    def add_messages(self, messages: Sequence[BaseMessage]) -> None:
        """添加消息"""
        all_messages = list(self.messages)
        all_messages.extend(messages)

        new_messages = [message_to_dict(message) for message in all_messages]
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(new_messages, f, ensure_ascii=False)

    @property
    def messages(self) -> list[BaseMessage]:
        """获取消息列表"""
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                messages_data = json.load(f)
                return messages_from_dict(messages_data)
        except FileNotFoundError:
            return []

    def clear(self) -> None:
        """清除消息历史"""
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump([], f)


_state_manager_instance: Optional[LegalConversationStateManager] = None


def get_legal_state_manager() -> LegalConversationStateManager:
    """获取状态管理器单例"""
    global _state_manager_instance
    if _state_manager_instance is None:
        _state_manager_instance = LegalConversationStateManager()
    return _state_manager_instance


def load_legal_state(session_id: str) -> Optional[LegalConversationState]:
    """加载法律对话状态"""
    return get_legal_state_manager().load_state(session_id)


def save_legal_state(state: LegalConversationState) -> None:
    """保存法律对话状态"""
    get_legal_state_manager().save_state(state)


def create_legal_state(session_id: str) -> LegalConversationState:
    """创建新的法律对话状态"""
    state = LegalConversationState(session_id=session_id)
    get_legal_state_manager().save_state(state)
    return state