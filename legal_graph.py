import networkx as nx
import os
from typing import List, Optional, Dict, Set
from legal_entities import (
    ArticleReference,
    ReferenceType,
    LegalChapter,
    LegalProvision
)

class LegalKnowledgeGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.chapter_graph = nx.DiGraph()
        self._init_graphs()

    def _init_graphs(self):
        if not self.graph:
            self.graph = nx.DiGraph()
        if not self.chapter_graph:
            self.chapter_graph = nx.DiGraph()

    def add_provision(self, provision: LegalProvision):
        self.graph.add_node(
            provision.article_id,
            article_number=provision.article_number,
            article_number_str=provision.article_number,
            chapter=provision.chapter,
            section=provision.section or "",
            content_preview=provision.content[:100]
        )

    def add_chapter(self, chapter: LegalChapter):
        self.chapter_graph.add_node(
            chapter.code,
            level=chapter.level.value,
            name=chapter.name
        )
        if chapter.parent_code:
            self.chapter_graph.add_edge(chapter.parent_code, chapter.code)

    def add_reference(self, reference: ArticleReference):
        self.graph.add_edge(
            reference.source_article_id,
            reference.target_article_id,
            reference_type=reference.reference_type.value,
            context=reference.context
        )

    def get_referencing_articles(self, article_id: str) -> List[str]:
        if article_id not in self.graph:
            return []
        return list(self.graph.predecessors(article_id))

    def get_referenced_articles(self, article_id: str) -> List[str]:
        if article_id not in self.graph:
            return []
        return list(self.graph.successors(article_id))

    def get_references_by_type(self, article_id: str, ref_type: ReferenceType) -> List[str]:
        if article_id not in self.graph:
            return []
        successors = self.graph.successors(article_id)
        return [
            target for target in successors
            if self.graph.has_edge(article_id, target)
            and self.graph[article_id][target].get('reference_type') == ref_type.value
        ]

    def get_chapter_hierarchy(self, chapter_code: str) -> Dict:
        if chapter_code not in self.chapter_graph:
            return {}
        ancestors = []
        current = chapter_code
        while self.chapter_graph.has_node(current):
            node_data = self.chapter_graph.nodes[current]
            ancestors.append({
                'code': current,
                'name': node_data.get('name'),
                'level': node_data.get('level')
            })
            predecessors = list(self.chapter_graph.predecessors(current))
            if not predecessors:
                break
            current = predecessors[0]
        return {'hierarchy': list(reversed(ancestors))}

    def find_citation_chain(self, source_article: str, target_article: str) -> Optional[List[str]]:
        try:
            path = nx.shortest_path(self.graph, source_article, target_article)
            return path
        except nx.NetworkXNoPath:
            return None

    def get_all_citations(self, article_id: str, depth: int = 1) -> Set[str]:
        if article_id not in self.graph:
            return set()
        citations = set()
        current_level = {article_id}
        for _ in range(depth):
            next_level = set()
            for art in current_level:
                next_level.update(self.graph.successors(art))
            citations.update(next_level)
            current_level = next_level
        return citations

    def get_statistics(self) -> Dict:
        return {
            'total_articles': self.graph.number_of_nodes(),
            'total_references': self.graph.number_of_edges(),
            'total_chapters': self.chapter_graph.number_of_nodes(),
            'citation_types': self._count_citation_types()
        }

    def _count_citation_types(self) -> Dict[str, int]:
        counts = {}
        for u, v, data in self.graph.edges(data=True):
            ref_type = data.get('reference_type', 'unknown')
            counts[ref_type] = counts.get(ref_type, 0) + 1
        return counts

    def save_graph(self, filepath: str):
        nx.write_gml(self.graph, f"{filepath}_provisions.gml")
        nx.write_gml(self.chapter_graph, f"{filepath}_chapters.gml")

    def load_graph(self, filepath: str):
        prov_path = f"{filepath}_provisions.gml"
        chap_path = f"{filepath}_chapters.gml"
        if os.path.exists(prov_path):
            self.graph = nx.read_gml(prov_path)
        if os.path.exists(chap_path):
            self.chapter_graph = nx.read_gml(chap_path)
