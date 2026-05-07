from typing import List, Optional
from dataclasses import dataclass, field
from enum import Enum

class ChapterLevel(Enum):
    PART = "编"
    CHAPTER = "章"
    SECTION = "节"
    SUBSECTION = "节下"
    ARTICLE = "条"

class ReferenceType(Enum):
    CITATION = "引用"
    REFERENCE = "参照"
    APPLICABLE = "援引"
    REPEALED = "废止"

class DocumentType(Enum):
    CIVIL_LAW = "民法典"
    JUDGMENT = "判决文书"
    GENERAL = "通用文档"

@dataclass
class LegalChapter:
    level: ChapterLevel
    code: str
    name: str
    full_name: str
    parent_code: Optional[str] = None
    child_codes: List[str] = field(default_factory=list)
    sort_order: int = 0

@dataclass
class ArticleReference:
    source_article_id: str
    target_article_id: str
    reference_type: ReferenceType
    context: Optional[str] = None
    description: Optional[str] = None

@dataclass
class LegalProvision:
    article_id: str
    chapter: str
    article_number: str
    content: str
    section: Optional[str] = None
    title: Optional[str] = None
    effective_date: Optional[str] = None
    amendment_history: List[str] = field(default_factory=list)
    related_provisions: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    is_amended: bool = False
    is_repealed: bool = False
    metadata: dict = field(default_factory=dict)

@dataclass
class CaseAnalysis:
    case_id: str
    case_number: str
    title: str
    case_type: str
    court_level: str
    judgment_date: str
    facts: str
    reasoning: str
    judgment_result: str
    issues: List[str] = field(default_factory=list)
    applied_provisions: List[str] = field(default_factory=list)
    key_points: List[str] = field(default_factory=list)
    similar_cases: List[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

@dataclass
class LegalDocument:
    document_id: str
    document_type: DocumentType
    title: str
    issuing_authority: Optional[str] = None
    issuing_date: Optional[str] = None
    effective_date: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    provisions: List[LegalProvision] = field(default_factory=list)
    chapters: List[LegalChapter] = field(default_factory=list)
