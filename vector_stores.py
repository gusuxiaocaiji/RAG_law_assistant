"""
向量数据库服务 - 法律助手专用版
提供法律文档的向量检索服务
"""
from typing import List, Dict, Optional, Any
import re
from langchain_chroma import Chroma
from langchain_core.documents import Document
import config_data as config
from dotenv import load_dotenv
from legal_entities import DocumentType

load_dotenv(verbose=True)


class LegalVectorStore:
    """
    法律专用向量存储服务

    提供多种检索模式：
    - 按法条编号精确检索
    - 按法律概念语义检索
    - 按文档类型检索
    - 混合检索（向量 + 关键词）
    """

    def __init__(self, embedding):
        """
        初始化向量存储服务

        Args:
            embedding: 嵌入模型
        """
        self.embedding = embedding
        self.vector_store = Chroma(
            collection_name=config.collection_name,
            embedding_function=self.embedding,
            persist_directory=config.persist_directory,
        )

    def get_retriever(self, search_kwargs: Optional[Dict] = None):
        """
        获取检索器

        Args:
            search_kwargs: 检索参数

        Returns:
            Retriever: 向量检索器
        """
        if search_kwargs is None:
            search_kwargs = {"k": config.legal_max_results}
        return self.vector_store.as_retriever(
            search_kwargs=search_kwargs
        )

    def search_by_article_number(
        self,
        article_number: str,
        max_results: int = 5
    ) -> List[Document]:
        """
        按法条编号精确检索

        支持多种编号格式：
        - 阿拉伯数字：1260
        - 中文数字：第一千二百六十条
        - 混合格式：第1260条

        Args:
            article_number: 条文编号（可以是字符串或数字）
            max_results: 最大返回结果数

        Returns:
            List[Document]: 匹配的文档列表
        """
        article_num_str = str(article_number).strip()
        clean_num = article_num_str.replace('第', '').replace('条', '').strip()

        arabic_num = self._chinese_to_arabic(article_num_str)

        filter_conditions = self._build_article_filter(article_num_str, arabic_num)

        if filter_conditions:
            try:
                results = self.vector_store.similarity_search(
                    query=f"第{article_num_str}条",
                    k=max_results * 3,
                    filter=filter_conditions
                )
                if results:
                    return results[:max_results]
            except Exception as e:
                pass

        results = self.vector_store.similarity_search(
            query=f"第{article_num_str}条",
            k=max_results * 5
        )

        filtered_results = []
        for doc in results:
            if len(filtered_results) >= max_results:
                break

            if self._matches_article(doc, article_num_str, arabic_num):
                filtered_results.append(doc)

        return filtered_results

    def search_by_concept(
        self,
        concept: str,
        max_results: int = 5,
        doc_type: Optional[DocumentType] = None
    ) -> List[Document]:
        """
        按法律概念语义检索

        使用语义相似度搜索法律概念相关条文

        Args:
            concept: 法律概念关键词
            max_results: 最大返回结果数
            doc_type: 可选的文档类型过滤

        Returns:
            List[Document]: 匹配的文档列表
        """
        if doc_type:
            filter_condition = {"document_type": doc_type.value}
            try:
                results = self.vector_store.similarity_search(
                    query=concept,
                    k=max_results,
                    filter=filter_condition
                )
                return results
            except Exception:
                pass

        results = self.vector_store.similarity_search(
            query=concept,
            k=max_results
        )

        return results

    def search_by_doc_type(
        self,
        doc_type: DocumentType,
        max_results: int = 10,
        chapter_filter: Optional[str] = None
    ) -> List[Document]:
        """
        按文档类型检索

        Args:
            doc_type: 文档类型
            max_results: 最大返回结果数
            chapter_filter: 可选的章节过滤

        Returns:
            List[Document]: 匹配的文档列表
        """
        filter_conditions = {"document_type": doc_type.value}

        if chapter_filter:
            filter_conditions["chapter"] = chapter_filter

        try:
            results = self.vector_store.similarity_search(
                query="",
                k=max_results,
                filter=filter_conditions
            )
            return results
        except Exception:
            return []

    def hybrid_search(
        self,
        query: str,
        keywords: Optional[List[str]] = None,
        max_results: int = 5,
        doc_type: Optional[DocumentType] = None,
        metadata_filters: Optional[Dict] = None
    ) -> List[Document]:
        """
        混合检索策略（向量 + 关键词）

        结合语义相似度和关键词匹配，提供更精准的检索结果

        Args:
            query: 语义查询文本
            keywords: 关键词列表（用于关键词匹配）
            max_results: 最大返回结果数
            doc_type: 文档类型过滤
            metadata_filters: 元数据过滤条件

        Returns:
            List[Document]: 匹配的文档列表，按相关性排序
        """
        vector_results = self.vector_store.similarity_search_with_score(
            query=query,
            k=max_results * 3
        )

        scored_results = []
        for doc, score in vector_results:
            if self._passes_filters(doc, doc_type, metadata_filters):
                relevance_score = self._calculate_relevance(
                    doc, query, keywords
                )
                combined_score = (1 - score) * 0.6 + relevance_score * 0.4
                scored_results.append((doc, combined_score))

        if keywords:
            keyword_matches = self._keyword_search(
                keywords,
                max_results=max_results * 2,
                doc_type=doc_type,
                metadata_filters=metadata_filters
            )

            for doc, kw_score in keyword_matches:
                existing = next(
                    (i for i, (d, _) in enumerate(scored_results) if d.page_content == doc.page_content),
                    -1
                )
                if existing >= 0:
                    old_doc, old_score = scored_results[existing]
                    scored_results[existing] = (old_doc, max(old_score, kw_score))
                else:
                    scored_results.append((doc, kw_score * 0.8))

        scored_results.sort(key=lambda x: x[1], reverse=True)

        return [doc for doc, score in scored_results[:max_results]]

    def search_by_chapter(
        self,
        part: Optional[str] = None,
        chapter: Optional[str] = None,
        section: Optional[str] = None,
        max_results: int = 10
    ) -> List[Document]:
        """
        按章节检索

        Args:
            part: 编名称
            chapter: 章名称
            section: 节名称
            max_results: 最大返回结果数

        Returns:
            List[Document]: 匹配的文档列表
        """
        metadata_filter = {}

        if chapter:
            metadata_filter["chapter"] = chapter
        if section:
            metadata_filter["section"] = section

        if metadata_filter:
            try:
                return self.vector_store.similarity_search(
                    query="",
                    k=max_results,
                    filter=metadata_filter
                )
            except Exception as e:
                pass

        query_parts = []
        if part:
            query_parts.append(part)
        if chapter:
            query_parts.append(chapter)
        if section:
            query_parts.append(section)

        query = " ".join(query_parts) if query_parts else "法律条文"

        results = self.vector_store.similarity_search(
            query=query,
            k=max_results * 3
        )

        filtered = []
        for doc in results:
            if self._matches_chapter(doc, part, chapter, section):
                filtered.append(doc)
                if len(filtered) >= max_results:
                    break

        return filtered

    def search_by_provisions_range(
        self,
        start_article: int,
        end_article: int,
        max_results: int = 20
    ) -> List[Document]:
        """
        按条文范围检索

        检索指定范围内的所有条文

        Args:
            start_article: 起始条文编号
            end_article: 结束条文编号
            max_results: 最大返回结果数

        Returns:
            List[Document]: 匹配的文档列表
        """
        results = self.vector_store.similarity_search(
            query=f"第{start_article}条到第{end_article}条",
            k=max_results * 2
        )

        filtered = []
        for doc in results:
            article_num = self._extract_article_number(doc)
            if article_num and start_article <= article_num <= end_article:
                filtered.append(doc)
                if len(filtered) >= max_results:
                    break

        filtered.sort(key=lambda d: self._extract_article_number(d) or 0)

        return filtered

    def _chinese_to_arabic(self, chinese_str: str) -> int:
        """
        将中文数字转换为阿拉伯数字

        Args:
            chinese_str: 中文数字字符串

        Returns:
            int: 阿拉伯数字
        """
        if not chinese_str:
            return 0

        chinese_str = chinese_str.replace('第', '').replace('条', '').replace('零', '')

        if not chinese_str or chinese_str == '十':
            return 10

        chinese_num_map = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9
        }

        result = 0
        temp = 0
        i = 0

        while i < len(chinese_str):
            char = chinese_str[i]

            if char in chinese_num_map:
                temp = temp * 10 + chinese_num_map[char]
                i += 1
            elif char == '十':
                if i == 0:
                    result += 10
                else:
                    result += temp * 10
                temp = 0
                i += 1
            elif char == '百':
                result += temp * 100
                temp = 0
                i += 1
            elif char == '千':
                result += temp * 1000
                temp = 0
                i += 1
            elif char == '万':
                result = (result + temp) * 10000
                temp = 0
                i += 1
            else:
                i += 1

        result += temp
        return result

    def _build_article_filter(self, article_str: str, arabic_num: int) -> Optional[Dict]:
        """
        构建条文检索过滤器

        Args:
            article_str: 条文字符串
            arabic_num: 阿拉伯数字

        Returns:
            Optional[Dict]: 过滤条件
        """
        clean_str = article_str.replace('第', '').replace('条', '').strip()

        if clean_str.isdigit():
            return {"article_number": clean_str}

        try:
            return {"article_number": str(arabic_num)}
        except Exception:
            return None

    def _matches_article(
        self,
        doc: Document,
        article_str: str,
        arabic_num: int
    ) -> bool:
        """
        检查文档是否匹配指定条文

        Args:
            doc: 文档
            article_str: 条文字符串
            arabic_num: 阿拉伯数字

        Returns:
            bool: 是否匹配
        """
        content = doc.page_content.lower()
        metadata = doc.metadata

        clean_str = article_str.replace('第', '').replace('条', '').strip()

        if 'article_number' in metadata:
            try:
                if str(metadata['article_number']) == str(arabic_num):
                    return True
                if str(metadata['article_number']) == clean_str:
                    return True
            except Exception:
                pass

        patterns = [
            f"第{arabic_num}条",
            f"第{clean_str}条",
            f"第{article_str}条"
        ]

        for pattern in patterns:
            if pattern in content or pattern in doc.page_content:
                return True

        return False

    def _passes_filters(
        self,
        doc: Document,
        doc_type: Optional[DocumentType],
        metadata_filters: Optional[Dict]
    ) -> bool:
        """
        检查文档是否通过过滤条件

        Args:
            doc: 文档
            doc_type: 文档类型
            metadata_filters: 元数据过滤

        Returns:
            bool: 是否通过
        """
        if doc_type:
            if doc.metadata.get('document_type') != doc_type.value:
                return False

        if metadata_filters:
            for key, value in metadata_filters.items():
                if key not in doc.metadata:
                    return False
                if isinstance(value, str):
                    if value not in str(doc.metadata[key]):
                        return False
                elif doc.metadata[key] != value:
                    return False

        return True

    def _calculate_relevance(
        self,
        doc: Document,
        query: str,
        keywords: Optional[List[str]]
    ) -> float:
        """
        计算文档与查询的相关性得分

        Args:
            doc: 文档
            query: 查询文本
            keywords: 关键词列表

        Returns:
            float: 相关性得分 (0-1)
        """
        content_lower = doc.page_content.lower()
        query_lower = query.lower()

        score = 0.0

        query_words = query_lower.split()
        for word in query_words:
            if word in content_lower:
                score += 0.2

        if keywords:
            keyword_count = sum(1 for kw in keywords if kw.lower() in content_lower)
            score += (keyword_count / len(keywords)) * 0.3

        if 'title' in doc.metadata:
            title_lower = doc.metadata['title'].lower()
            if query_lower in title_lower:
                score += 0.3

        return min(score, 1.0)

    def _keyword_search(
        self,
        keywords: List[str],
        max_results: int,
        doc_type: Optional[DocumentType],
        metadata_filters: Optional[Dict]
    ) -> List[tuple]:
        """
        关键词搜索

        Args:
            keywords: 关键词列表
            doc_type: 文档类型
            metadata_filters: 元数据过滤
            max_results: 最大结果数

        Returns:
            List[tuple]: (文档, 得分) 列表
        """
        results = self.vector_store.similarity_search(
            query=" ".join(keywords),
            k=max_results
        )

        scored = []
        for doc in results:
            if self._passes_filters(doc, doc_type, metadata_filters):
                score = self._keyword_match_score(doc, keywords)
                scored.append((doc, score))

        return scored

    def _keyword_match_score(self, doc: Document, keywords: List[str]) -> float:
        """
        计算关键词匹配得分

        Args:
            doc: 文档
            keywords: 关键词列表

        Returns:
            float: 匹配得分
        """
        content_lower = doc.page_content.lower()
        score = 0.0

        for kw in keywords:
            count = content_lower.count(kw.lower())
            if count > 0:
                score += min(count * 0.2, 0.5)

        return min(score, 1.0)

    def _matches_chapter(
        self,
        doc: Document,
        part: Optional[str],
        chapter: Optional[str],
        section: Optional[str]
    ) -> bool:
        """
        检查文档是否匹配指定章节

        Args:
            doc: 文档
            part: 编名称
            chapter: 章名称
            section: 节名称

        Returns:
            bool: 是否匹配
        """
        metadata = doc.metadata

        if part and metadata.get('part'):
            if part not in metadata['part']:
                return False

        if chapter and metadata.get('chapter'):
            if chapter not in metadata['chapter']:
                return False

        if section and metadata.get('section'):
            if section not in metadata['section']:
                return False

        return True

    def _extract_article_number(self, doc: Document) -> Optional[int]:
        """
        从文档中提取条文编号

        Args:
            doc: 文档

        Returns:
            Optional[int]: 条文编号
        """
        metadata = doc.metadata

        if 'article_number' in metadata:
            try:
                return int(metadata['article_number'])
            except Exception:
                pass

        match = re.search(r'第(\d+)条', doc.page_content)
        if match:
            try:
                return int(match.group(1))
            except Exception:
                pass

        return None


class VectorStoresService(LegalVectorStore):
    """
    向量存储服务（兼容旧接口）

    提供与旧版 VectorStoresService 兼容的接口
    """

    def __init__(self, embedding):
        super().__init__(embedding)


if __name__ == '__main__':
    from langchain_community.embeddings import DashScopeEmbeddings

    embeddings = DashScopeEmbeddings(model="text-embedding-v4")
    store = LegalVectorStore(embeddings)

    print("=" * 60)
    print("法律向量检索服务测试")
    print("=" * 60)

    print("\n1. 按法条编号检索:")
    results = store.search_by_article_number("1260", max_results=3)
    print(f"   找到 {len(results)} 条结果")
    for i, doc in enumerate(results, 1):
        print(f"   {i}. {doc.page_content[:60]}...")

    print("\n2. 按法律概念检索:")
    results = store.search_by_concept("合同", max_results=3)
    print(f"   找到 {len(results)} 条结果")
    for i, doc in enumerate(results, 1):
        print(f"   {i}. {doc.page_content[:60]}...")

    print("\n3. 混合检索:")
    results = store.hybrid_search(
        query="房屋买卖合同纠纷",
        keywords=["房屋", "买卖", "合同"],
        max_results=3
    )
    print(f"   找到 {len(results)} 条结果")
    for i, doc in enumerate(results, 1):
        print(f"   {i}. {doc.page_content[:60]}...")

    print("\n" + "=" * 60)
