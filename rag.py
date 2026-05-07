"""
RAG 核心逻辑 - 法律助手专用版
提供专业的法律问答功能，包括法条引用、案例推送等
"""
from typing import List, Dict, Optional, Any
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableWithMessageHistory, RunnableLambda
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings

from file_history_store import get_history
from vector_stores import LegalVectorStore, VectorStoresService
from legal_entities import DocumentType, LegalProvision, CaseAnalysis
import config_data as config
from dotenv import load_dotenv
import re

load_dotenv(verbose=True)


class LegalCitationFormatter:
    """法条引用格式化器"""

    @staticmethod
    def format_article_citation(doc: Document) -> str:
        """
        格式化法条引用

        Args:
            doc: 包含法条信息的文档

        Returns:
            str: 格式化后的法条引用
        """
        metadata = doc.metadata
        content = doc.page_content

        article_num = metadata.get('article_number', 'N/A')
        chapter = metadata.get('chapter', '未知章节')
        part = metadata.get('part', '')
        doc_type = metadata.get('document_type', '法律')

        citation = f"《{doc_type}》"

        if part:
            citation += f" {part}"
        if chapter:
            citation += f" {chapter}"

        citation += f" 第{article_num}条"

        content_preview = content[:100].replace('\n', ' ')
        if len(content) > 100:
            content_preview += "..."

        return f"{citation}\n{content_preview}"

    @staticmethod
    def extract_article_numbers(text: str) -> List[str]:
        """
        从文本中提取法条编号

        Args:
            text: 输入文本

        Returns:
            List[str]: 法条编号列表
        """
        patterns = [
            r'第(\d+)条',
            r'第([零一二三四五六七八九十百千]+)条',
            r'《[^》]+》\s*第(\d+)条',
        ]

        article_numbers = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            article_numbers.extend(matches)

        return list(set(article_numbers))

    @staticmethod
    def format_with_citations(docs: List[Document]) -> str:
        """
        格式化文档列表，带法条引用

        Args:
            docs: 文档列表

        Returns:
            str: 格式化后的文本
        """
        if not docs:
            return "无相关参考资料"

        formatted = []
        for i, doc in enumerate(docs, 1):
            citation = LegalCitationFormatter.format_article_citation(doc)
            formatted.append(f"【参考 {i}】\n{citation}\n")

        return "\n".join(formatted)


class LegalRelationTracker:
    """法律关系追踪器"""

    def __init__(self):
        """初始化追踪器"""
        self.legal_relations: Dict[str, List[str]] = {}
        self.mentioned_articles: List[str] = []
        self.legal_concepts: List[str] = []
        self.discussion_history: List[Dict] = []

    def track_article_reference(self, article_number: str, context: str):
        """
        追踪法条引用

        Args:
            article_number: 条文编号
            context: 引用上下文
        """
        if article_number not in self.mentioned_articles:
            self.mentioned_articles.append(article_number)

        if article_number not in self.legal_relations:
            self.legal_relations[article_number] = []

        if context:
            self.legal_relations[article_number].append(context)

    def track_legal_concept(self, concept: str):
        """
        追踪法律概念

        Args:
            concept: 法律概念
        """
        if concept not in self.legal_concepts:
            self.legal_concepts.append(concept)

    def add_to_history(self, user_query: str, assistant_response: str):
        """
        添加对话历史

        Args:
            user_query: 用户问题
            assistant_response: 助手回答
        """
        self.discussion_history.append({
            "query": user_query,
            "response": assistant_response,
            "mentioned_articles": self.mentioned_articles.copy(),
            "legal_concepts": self.legal_concepts.copy()
        })

    def get_related_articles(self, article_number: str) -> List[str]:
        """
        获取相关法条

        Args:
            article_number: 条文编号

        Returns:
            List[str]: 相关法条编号列表
        """
        return self.legal_relations.get(article_number, [])

    def get_discussion_summary(self) -> str:
        """
        获取讨论摘要

        Returns:
            str: 讨论摘要文本
        """
        summary_parts = []

        if self.mentioned_articles:
            summary_parts.append(f"已讨论的法条: {', '.join(self.mentioned_articles)}")

        if self.legal_concepts:
            summary_parts.append(f"涉及的法律概念: {', '.join(self.legal_concepts)}")

        if self.discussion_history:
            summary_parts.append(f"对话轮数: {len(self.discussion_history)}")

        return "\n".join(summary_parts) if summary_parts else "暂无讨论记录"

    def clear(self):
        """清除所有追踪数据"""
        self.legal_relations.clear()
        self.mentioned_articles.clear()
        self.legal_concepts.clear()
        self.discussion_history.clear()


class CasePushService:
    """案例推送服务"""

    def __init__(self, vector_store: LegalVectorStore):
        """
        初始化案例推送服务

        Args:
            vector_store: 向量存储服务
        """
        self.vector_store = vector_store

    def find_similar_cases(
        self,
        query: str,
        case_type: Optional[str] = None,
        max_results: int = 3
    ) -> List[Document]:
        """
        查找相似案例

        Args:
            query: 查询文本
            case_type: 案件类型过滤
            max_results: 最大结果数

        Returns:
            List[Document]: 相似案例列表
        """
        try:
            results = self.vector_store.search_by_concept(
                concept=query,
                max_results=max_results,
                doc_type=DocumentType.JUDGMENT if case_type else None
            )

            case_results = [
                doc for doc in results
                if doc.metadata.get('document_type') == '判决文书'
            ]

            return case_results[:max_results]
        except Exception:
            return []

    def extract_case_key_points(self, case_doc: Document) -> Dict[str, Any]:
        """
        提取案例要点

        Args:
            case_doc: 案例文档

        Returns:
            Dict: 案例要点字典
        """
        metadata = case_doc.metadata
        content = case_doc.page_content

        return {
            "case_number": metadata.get('case_number', '未知案号'),
            "case_type": metadata.get('case_type', '未知类型'),
            "court_level": metadata.get('court_level', '未知审级'),
            "judgment_date": metadata.get('judgment_date', '未知日期'),
            "summary": content[:200] if len(content) > 200 else content,
            "applied_provisions": metadata.get('applied_provisions', [])
        }

    def format_case_push(
        self,
        cases: List[Document],
        max_cases: int = 3
    ) -> str:
        """
        格式化案例推送

        Args:
            cases: 案例列表
            max_cases: 最大推送案例数

        Returns:
            str: 格式化后的案例推送文本
        """
        if not cases:
            return "暂无相关案例推荐"

        formatted_cases = []
        for i, case in enumerate(cases[:max_cases], 1):
            key_points = self.extract_case_key_points(case)
            case_text = f"""
【类案 {i}】
案号: {key_points['case_number']}
案件类型: {key_points['case_type']}
审理法院: {key_points['court_level']}法院
裁判日期: {key_points['judgment_date']}
案件概要: {key_points['summary']}
"""
            if key_points['applied_provisions']:
                provisions = ', '.join(key_points['applied_provisions'][:5])
                case_text += f"适用法条: {provisions}\n"

            formatted_cases.append(case_text)

        return "\n".join(formatted_cases)


class PromptTemplateManager:
    """提示词模板管理器"""

    CIVIL_LAW_TEMPLATE = ChatPromptTemplate.from_messages([
        ("system", """你是一个专业的法律助手，专门解答《民法典》相关法律问题。

回答规范：
1. 严谨专业：使用准确的法律术语
2. 有据可依：每个观点都需引用相关法条
3. 结构清晰：先给出结论，再详细解释
4. 实用导向：提供可操作的法律建议

法条引用格式：
- 引用法条时使用【《民法典》第X条】格式
- 明确说明法条的适用范围和条件
- 必要时提供相关司法解释

上下文信息：
{context}

对话历史：
{history}

当前问题：
{input}"""),
        ("user", "{input}")
    ])

    JUDGMENT_TEMPLATE = ChatPromptTemplate.from_messages([
        ("system", """你是一个专业的法律分析助手，专门分析裁判文书和案例。

分析要点：
1. 案件事实：准确理解案件基本事实
2. 争议焦点：明确当事人之间的争议焦点
3. 法律适用：分析法院援引的法律依据
4. 裁判要旨：提取案例的裁判规则

案例参考：
{context}

对话历史：
{history}

当前问题：
{input}"""),
        ("user", "{input}")
    ])

    GENERAL_TEMPLATE = ChatPromptTemplate.from_messages([
        ("system", """你是一个智能助手，根据提供的参考资料回答用户问题。

参考资料：
{context}

对话历史：
{history}

请简洁专业地回答以下问题：
{input}"""),
        ("user", "{input}")
    ])

    @classmethod
    def get_template(cls, doc_type: Optional[DocumentType] = None) -> ChatPromptTemplate:
        """
        根据文档类型获取对应的提示词模板

        Args:
            doc_type: 文档类型

        Returns:
            ChatPromptTemplate: 对应的提示词模板
        """
        if doc_type == DocumentType.CIVIL_LAW:
            return cls.CIVIL_LAW_TEMPLATE
        elif doc_type == DocumentType.JUDGMENT:
            return cls.JUDGMENT_TEMPLATE
        else:
            return cls.GENERAL_TEMPLATE

    @classmethod
    def auto_detect_template(cls, docs: List[Document]) -> ChatPromptTemplate:
        """
        根据文档内容自动检测并选择模板

        Args:
            docs: 文档列表

        Returns:
            ChatPromptTemplate: 选择的提示词模板
        """
        if not docs:
            return cls.GENERAL_TEMPLATE

        doc_types = [doc.metadata.get('document_type', '通用') for doc in docs]

        if any('民法典' in dt for dt in doc_types):
            return cls.CIVIL_LAW_TEMPLATE
        elif any('判决' in dt for dt in doc_types):
            return cls.JUDGMENT_TEMPLATE
        else:
            return cls.GENERAL_TEMPLATE


class LegalRAGService:
    """
    法律助手 RAG 服务

    提供专业的法律问答功能，包括：
    - 智能检索（法条编号、语义、混合检索）
    - 法条引用格式化
    - 法律关系追踪
    - 类案推送
    - 多轮对话支持
    """

    def __init__(self):
        """初始化法律 RAG 服务"""
        self.vector_store = LegalVectorStore(
            embedding=DashScopeEmbeddings(model=config.embedding_model_name)
        )

        self.citation_formatter = LegalCitationFormatter()
        self.relation_tracker = LegalRelationTracker()
        self.case_pusher = CasePushService(self.vector_store)

        self.chat_model = ChatTongyi(model=config.chat_model_name)

        self.default_template = PromptTemplateManager.get_template(DocumentType.CIVIL_LAW)

        self.chain = self._build_chain()

        self.conversation_chain = RunnableWithMessageHistory(
            self.chain,
            get_history,
            input_messages_key="input",
            history_messages_key="history",
        )

    def _format_context(self, docs: List[Document]) -> str:
        """
        格式化检索结果为上下文

        Args:
            docs: 检索到的文档列表

        Returns:
            str: 格式化的上下文文本
        """
        if not docs:
            return "无相关参考资料"

        formatted_docs = []
        for i, doc in enumerate(docs, 1):
            metadata = doc.metadata
            content = doc.page_content

            article_info = ""
            if 'article_number' in metadata:
                article_info = f"【《{metadata.get('document_type', '法律')}》第{metadata['article_number']}条】"

            chapter_info = ""
            if 'chapter' in metadata and metadata['chapter']:
                chapter_info = f"（{metadata['chapter']}）"

            doc_text = f"{article_info}{chapter_info}\n{content}"
            formatted_docs.append(f"[文档{i}]\n{doc_text}")

        return "\n\n".join(formatted_docs)

    def _build_chain(self):
        """构建 RAG 执行链"""
        def format_for_retriever(value: dict) -> str:
            return value["input"]

        def format_docs(docs: List[Document]) -> str:
            return self._format_context(docs)

        def prepare_prompt_input(value: dict) -> dict:
            return {
                "input": value["input"]["input"],
                "context": value["context"],
                "history": value["input"]["history"]
            }

        chain = (
            {
                "input": RunnablePassthrough(),
                "context": (
                    RunnableLambda(format_for_retriever)
                    | self.vector_store.get_retriever()
                    | RunnableLambda(format_docs)
                )
            }
            | RunnableLambda(prepare_prompt_input)
            | self.default_template
            | self.chat_model
            | StrOutputParser()
        )

        return chain

    def ask(
        self,
        question: str,
        retrieval_mode: str = "hybrid",
        enable_case_push: bool = False,
        session_config: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        提问并获取回答

        Args:
            question: 用户问题
            retrieval_mode: 检索模式（exact/semantic/hybrid/chapter）
            enable_case_push: 是否启用案例推送
            session_config: 会话配置

        Returns:
            Dict: 包含回答和元数据的字典
        """
        if session_config is None:
            session_config = config.session_config

        try:
            if retrieval_mode == "exact":
                article_num = self.citation_formatter.extract_article_numbers(question)
                if article_num:
                    docs = self.vector_store.search_by_article_number(
                        article_num[0],
                        max_results=config.legal_max_results
                    )
                else:
                    docs = []
            elif retrieval_mode == "semantic":
                docs = self.vector_store.search_by_concept(
                    question,
                    max_results=config.legal_max_results
                )
            elif retrieval_mode == "chapter":
                docs = self.vector_store.search_by_chapter(
                    max_results=config.legal_max_results
                )
            else:
                docs = self.vector_store.hybrid_search(
                    query=question,
                    max_results=config.legal_max_results
                )

            for doc in docs:
                if 'article_number' in doc.metadata:
                    self.relation_tracker.track_article_reference(
                        doc.metadata['article_number'],
                        question
                    )

            template = PromptTemplateManager.auto_detect_template(docs)
            self.default_template = template

            self.chain = self._build_chain()

            response = self.conversation_chain.invoke(
                {"input": question},
                session_config
            )

            self.relation_tracker.add_to_history(question, response)

            result = {
                "answer": response,
                "cited_articles": self.relation_tracker.mentioned_articles.copy(),
                "discussion_summary": self.relation_tracker.get_discussion_summary()
            }

            if enable_case_push and docs:
                similar_cases = self.case_pusher.find_similar_cases(question)
                if similar_cases:
                    case_push_text = self.case_pusher.format_case_push(similar_cases)
                    result["similar_cases"] = case_push_text

            return result

        except Exception as e:
            return {
                "answer": f"处理您的问题时出现错误: {str(e)}",
                "cited_articles": [],
                "discussion_summary": self.relation_tracker.get_discussion_summary()
            }

    def get_citation_formatter(self) -> LegalCitationFormatter:
        """
        获取法条引用格式化器

        Returns:
            LegalCitationFormatter: 格式化器实例
        """
        return self.citation_formatter

    def get_relation_tracker(self) -> LegalRelationTracker:
        """
        获取法律关系追踪器

        Returns:
            LegalRelationTracker: 追踪器实例
        """
        return self.relation_tracker

    def reset_conversation(self):
        """重置对话上下文"""
        self.relation_tracker.clear()
        self.default_template = PromptTemplateManager.get_template(DocumentType.CIVIL_LAW)
        self.chain = self._build_chain()

        self.conversation_chain = RunnableWithMessageHistory(
            self.chain,
            get_history,
            input_messages_key="input",
            history_messages_key="history",
        )


class RagService(LegalRAGService):
    """
    兼容旧接口的 RAG 服务

    提供与旧版 RagService 兼容的接口
    """

    def __init__(self):
        super().__init__()


def print_prompt(prompt):
    """打印提示词（调试用）"""
    print("=" * 60)
    print("Prompt:")
    print(prompt.to_string() if hasattr(prompt, 'to_string') else str(prompt))
    print("=" * 60)
    return prompt


if __name__ == '__main__':
    print("=" * 60)
    print("法律助手 RAG 服务测试")
    print("=" * 60)

    service = LegalRAGService()

    session_config = {
        "configurable": {
            "session_id": "test_session",
        }
    }

    print("\n测试1: 精确检索法条")
    result = service.ask(
        "民法典第123条是什么内容？",
        retrieval_mode="exact",
        session_config=session_config
    )
    print(f"\n回答:\n{result['answer']}")
    print(f"\n引用法条: {result['cited_articles']}")

    print("\n" + "-" * 60)
    print("\n测试2: 语义检索")
    result = service.ask(
        "合同无效的情形有哪些？",
        retrieval_mode="semantic",
        session_config=session_config
    )
    print(f"\n回答:\n{result['answer'][:300]}...")

    print("\n" + "-" * 60)
    print("\n测试3: 带案例推送")
    result = service.ask(
        "房屋买卖合同纠纷怎么处理？",
        retrieval_mode="hybrid",
        enable_case_push=True,
        session_config=session_config
    )
    print(f"\n回答:\n{result['answer'][:300]}...")
    if 'similar_cases' in result:
        print(f"\n推荐案例:\n{result['similar_cases'][:200]}...")

    print("\n" + "-" * 60)
    print("\n测试4: 多轮对话")
    result1 = service.ask(
        "我想了解一下合同法的基本原则",
        session_config=session_config
    )
    print(f"\n第一轮回答:\n{result1['answer'][:200]}...")

    result2 = service.ask(
        "那具体到买卖合同呢？",
        session_config=session_config
    )
    print(f"\n第二轮回答:\n{result2['answer'][:200]}...")
    print(f"\n讨论摘要:\n{result2['discussion_summary']}")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
