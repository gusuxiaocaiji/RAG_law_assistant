"""
案例解析器
解析裁判文书，提取案由、争议焦点、裁判要旨、适用法条等信息
"""
import re
from typing import List, Dict, Optional
from .base_parser import BaseParser
from legal_entities import CaseAnalysis, DocumentType


class CaseParser(BaseParser):
    """裁判文书解析器"""

    def __init__(self, text: str, source: str = "unknown"):
        """
        初始化解析器

        Args:
            text: 文书文本内容
            source: 文书来源标识
        """
        self.text = text
        self.source = source
        self.case_data: Optional[CaseAnalysis] = None

    def parse(self) -> str:
        """
        解析文书并返回文本内容

        Returns:
            str: 解析后的文本内容
        """
        self._extract_case_structure()
        return self.text

    def get_metadata(self) -> Dict[str, any]:
        """
        获取文书元数据

        Returns:
            Dict: 元数据字典
        """
        if not self.case_data:
            self._extract_case_structure()

        return {
            "source": self.source,
            "case_number": self.case_data.case_number if self.case_data else "",
            "case_type": self.case_data.case_type if self.case_data else "",
            "court_level": self.case_data.court_level if self.case_data else "",
        }

    def get_supported_extensions(self) -> List[str]:
        """
        获取支持的扩展名列表

        Returns:
            List[str]: 支持的文件扩展名列表
        """
        return ['.txt', '.pdf', '.doc', '.docx']

    def get_structured_case(self) -> CaseAnalysis:
        """
        获取结构化的案例分析

        Returns:
            CaseAnalysis: 包含完整案例信息的对象
        """
        if not self.case_data:
            self._extract_case_structure()

        return self.case_data

    def _extract_case_structure(self):
        """提取裁判文书的结构化信息"""
        case_number = self._extract_case_number()
        case_type = self._extract_case_type()
        court_level = self._extract_court_level()
        judgment_date = self._extract_judgment_date()
        title = self._extract_case_title()
        facts = self._extract_facts()
        reasoning = self._extract_reasoning()
        judgment_result = self._extract_judgment_result()
        issues = self._extract_issues()
        applied_provisions = self._extract_applied_provisions()
        key_points = self._extract_key_points()

        self.case_data = CaseAnalysis(
            case_id=self._generate_case_id(case_number),
            case_number=case_number,
            title=title,
            case_type=case_type,
            court_level=court_level,
            judgment_date=judgment_date,
            facts=facts,
            reasoning=reasoning,
            judgment_result=judgment_result,
            issues=issues,
            applied_provisions=applied_provisions,
            key_points=key_points,
            metadata={
                "source": self.source,
                "full_text": self.text
            }
        )

    def _extract_case_number(self) -> str:
        """提取案号"""
        patterns = [
            r'案号[：:]\s*([^\n]+)',
            r'\(([0-9]{4})\s*[^)]+第[^)]+\)',
            r'第([0-9]{4})[^第]+号',
            r'[\（\(]([0-9]{4})[\）\)][^号]+号',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text)
            if match:
                return match.group(1).strip()

        return "未知案号"

    def _extract_case_type(self) -> str:
        """提取案件类型"""
        type_keywords = {
            "民事": ["民事", "民初", "民终", "民再"],
            "刑事": ["刑事", "刑初", "刑终", "刑再"],
            "行政": ["行政", "行初", "行终"],
            "执行": ["执行", "执"],
            "赔偿": ["赔偿", "赔"],
        }

        text_upper = self.text[:500]

        for case_type, keywords in type_keywords.items():
            for keyword in keywords:
                if keyword in text_upper:
                    return case_type

        return "未知类型"

    def _extract_court_level(self) -> str:
        """提取审级"""
        level_keywords = {
            "基层": ["基层人民法院", "人民法庭"],
            "中级": ["中级人民法院"],
            "高级": ["高级人民法院"],
            "最高": ["最高人民法院"],
        }

        text_start = self.text[:1000]

        for level, keywords in level_keywords.items():
            for keyword in keywords:
                if keyword in text_start:
                    return level

        return "未知审级"

    def _extract_judgment_date(self) -> str:
        """提取裁判日期"""
        patterns = [
            r'(\d{4})年(\d{1,2})月(\d{1,2})日',
            r'(\d{4})-(\d{2})-(\d{2})',
            r'(\d{4})/(\d{2})/(\d{2})',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text)
            if match:
                if '-' in pattern or '/' in pattern:
                    return f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}"
                else:
                    return f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}"

        return "未知日期"

    def _extract_case_title(self) -> str:
        """提取案件标题"""
        lines = self.text.split('\n')

        for line in lines[:10]:
            line = line.strip()
            if len(line) > 5 and len(line) < 100:
                if any(keyword in line for keyword in ['案', '判决', '裁定', '调解']):
                    return line

        return self._extract_case_type() + "案件"

    def _extract_facts(self) -> str:
        """提取案件事实"""
        sections = self._find_section(r'^(.*?(?:事实|经过|案情).*?)[。\n]', self.text)

        if sections:
            return self._clean_text(' '.join(sections))

        sections = self._find_section(r'^(.*?(?:基本|如下).*?)[。\n]', self.text)

        if sections:
            return self._clean_text(' '.join(sections))

        return self._extract_first_paragraph()

    def _extract_reasoning(self) -> str:
        """提取裁判理由"""
        sections = self._find_section(r'^(.*?(?:本院|认为|理由).*?)[。\n]', self.text)

        if sections:
            return self._clean_text(' '.join(sections))

        return self._extract_middle_paragraph()

    def _extract_judgment_result(self) -> str:
        """提取裁判结果"""
        sections = self._find_section(r'^(.*?(?:判决|裁定|调解|裁决).*?)[。\n]', self.text)

        if sections:
            return self._clean_text(' '.join(sections))

        result_patterns = [
            r'[一二三四]、\s*判决[：:]\s*([^\n]+)',
            r'依照[^。]+[。]',
            r'判决如下[：:]\s*([^\n]+)',
        ]

        for pattern in result_patterns:
            match = re.search(pattern, self.text)
            if match:
                return self._clean_text(match.group(1))

        return self._extract_last_paragraph()

    def _extract_issues(self) -> List[str]:
        """提取争议焦点"""
        issues = []

        issue_section = self._find_section(r'(?:争议|争执|焦点|分歧)(.*?)(?:本院|认为|理由|$)', self.text)

        if issue_section:
            text = ' '.join(issue_section)
            sentences = re.split(r'[。；]', text)
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 10 and len(sentence) < 200:
                    issues.append(self._clean_text(sentence))

        issue_patterns = [
            r'[一二三四五六七八九十]+、\s*([^。，]+?[？?])',
            r'焦点[：:]\s*([^\n]+)',
        ]

        for pattern in issue_patterns:
            matches = re.findall(pattern, self.text)
            for match in matches:
                match = match.strip()
                if len(match) > 5 and len(match) < 200 and match not in issues:
                    issues.append(self._clean_text(match))

        return list(set(issues))[:10]

    def _extract_applied_provisions(self) -> List[str]:
        """提取适用法条"""
        provisions = []

        provision_patterns = [
            r'《([^》]+)》第([零一二三四五六七八九十百千\d]+)条',
            r'第([零一二三四五六七八九十百千\d]+)条',
            r'民法典第([零一二三四五六七八九十百千\d]+)条',
        ]

        for pattern in provision_patterns:
            matches = re.findall(pattern, self.text)
            for match in matches:
                if isinstance(match, tuple):
                    law_name = match[0] if match[0] else "民法典"
                    article_num = match[1]
                    provision = f"《{law_name}》第{self._normalize_article_num(article_num)}条"
                else:
                    provision = f"第{self._normalize_article_num(match)}条"

                if provision not in provisions:
                    provisions.append(provision)

        provision_section = self._find_section(
            r'(?:适用|依据|根据)[^。]*?第[零一二三四五六七八九十百千\d]+条',
            self.text
        )

        if provision_section:
            for section in provision_section:
                matches = re.findall(r'第([零一二三四五六七八九十百千\d]+)条', section)
                for match in matches:
                    provision = f"第{self._normalize_article_num(match)}条"
                    if provision not in provisions:
                        provisions.append(provision)

        return provisions

    def _extract_key_points(self) -> List[str]:
        """提取裁判要旨/关键点"""
        key_points = []

        key_point_patterns = [
            r'要旨[：:]\s*([^\n]+)',
            r'要义[：:]\s*([^\n]+)',
            r'裁判要点[：:]\s*([^\n]+)',
            r'规则[：:]\s*([^\n]+)',
        ]

        for pattern in key_point_patterns:
            matches = re.findall(pattern, self.text)
            for match in matches:
                match = match.strip()
                if len(match) > 10 and len(match) < 500:
                    key_points.append(self._clean_text(match))

        conclusion_section = self._find_section(r'(?:综上|总之|由此可见)(.*?)$', self.text)

        if conclusion_section:
            text = ' '.join(conclusion_section)
            sentences = re.split(r'[。；]', text)
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 20 and len(sentence) < 300:
                    key_points.append(self._clean_text(sentence))

        return list(set(key_points))[:5]

    def _find_section(self, pattern: str, text: str) -> List[str]:
        """查找符合模式的文本段落"""
        matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL)
        return [m.strip() for m in matches if m.strip()]

    def _clean_text(self, text: str) -> str:
        """清理文本"""
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n+', ' ', text)
        text = text.strip()
        return text

    def _extract_first_paragraph(self) -> str:
        """提取第一段"""
        lines = [l.strip() for l in self.text.split('\n') if l.strip()]
        return self._clean_text(' '.join(lines[:3])) if lines else ""

    def _extract_middle_paragraph(self) -> str:
        """提取中间段落"""
        lines = [l.strip() for l in self.text.split('\n') if l.strip()]
        if len(lines) > 5:
            return self._clean_text(' '.join(lines[len(lines)//2-2:len(lines)//2+2]))
        return self._extract_first_paragraph()

    def _extract_last_paragraph(self) -> str:
        """提取最后段落"""
        lines = [l.strip() for l in self.text.split('\n') if l.strip()]
        return self._clean_text(' '.join(lines[-3:])) if lines else ""

    def _normalize_article_num(self, num_str: str) -> str:
        """规范化条文编号"""
        chinese_map = {
            '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
            '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10
        }

        if num_str.isdigit():
            return num_str

        result = 0
        temp = 0

        for char in num_str:
            if char in chinese_map:
                temp = temp * 10 + chinese_map[char]
            elif char == '十':
                result += temp * 10
                temp = 0
            elif char == '百':
                result += temp * 100
                temp = 0
            elif char == '千':
                result += temp * 1000
                temp = 0

        result += temp
        return str(result)

    def _generate_case_id(self, case_number: str) -> str:
        """生成案例ID"""
        clean_number = re.sub(r'[^a-zA-Z0-9]', '', case_number)
        return f"CASE_{clean_number}" if clean_number else f"CASE_{abs(hash(self.source))[-8:]}"

    def search_related_provisions(self, provisions: List[str]) -> Dict[str, str]:
        """
        查找相关法条的详细内容

        Args:
            provisions: 法条编号列表

        Returns:
            Dict[str, str]: 法条编号到内容的映射
        """
        return {prov: f"{prov}的详细内容" for prov in provisions}


def parse_case_text(text: str, source: str = "unknown") -> CaseParser:
    """
    解析裁判文书文本的便捷函数

    Args:
        text: 文书文本
        source: 文书来源

    Returns:
        CaseParser: 解析器实例
    """
    parser = CaseParser(text, source)
    parser.parse()
    return parser


if __name__ == '__main__':
    sample_case = """
民事判决书
案号：（2021）京01民初1234号

原告张三诉被告李四房屋买卖合同纠纷一案，本院于2021年5月20日立案后，依法适用普通程序，公开开庭进行了审理。本案现已审理终结。

原告诉称，2019年10月1日，原被告签订房屋买卖合同，约定被告将其所有的位于北京市海淀区的房屋出售给原告，房屋总价500万元。合同签订后，原告支付了首付款150万元，但被告迟迟不办理过户手续。

被告辩称，不同意原告的诉讼请求。被告表示，因房屋价格上涨，被告不再愿意继续履行合同，愿意退还首付款并承担违约责任。

本院认为，本案的争议焦点为：1. 涉案房屋买卖合同的效力？2. 被告是否应当继续履行合同？

根据《中华人民共和国民法典》第五百零九条、第五百一十条、第五百七十七条的规定，当事人应当按照约定全面履行自己的义务。当事人一方不履行合同义务或者履行合同义务不符合约定的，应当承担违约责任。

综上所述，依据《中华人民共和国民法典》第五百零九条、第五百一十条、第五百七十七条，《中华人民共和国民事诉讼法》第一百二十八条的规定，判决如下：

一、被告李四于本判决生效后三十日内继续履行与原告张三签订的房屋买卖合同，协助原告办理涉案房屋的过户手续；

二、被告李四于本判决生效后十日内支付原告张三违约金20万元。

如果未按本判决指定的期间履行给付金钱义务，应当加倍支付迟延履行期间的债务利息。
    """

    parser = parse_case_text(sample_case, "sample_court")
    case = parser.get_structured_case()

    print(f"案件编号: {case.case_number}")
    print(f"案件类型: {case.case_type}")
    print(f"审理法院: {case.court_level}")
    print(f"裁判日期: {case.judgment_date}")
    print(f"争议焦点: {case.issues}")
    print(f"适用法条: {case.applied_provisions}")
    print(f"\n裁判结果:\n{case.judgment_result}")
