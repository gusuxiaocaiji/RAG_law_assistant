"""
文档解析器基类
定义统一的解析接口
"""
from abc import ABC, abstractmethod
from typing import List, Dict


class BaseParser(ABC):
    """文档解析器抽象基类"""
    
    @abstractmethod
    def parse(self) -> str:
        """
        解析文档并返回文本内容
        
        Returns:
            str: 解析后的文本内容
        """
        pass
    
    @abstractmethod
    def get_metadata(self) -> Dict[str, any]:
        """
        获取文档元数据
        
        Returns:
            Dict: 元数据字典
        """
        pass
    
    @abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """
        获取支持的扩展名列表
        
        Returns:
            List[str]: 支持的文件扩展名列表
        """
        pass
    
    def validate_file(self, file_path: str) -> bool:
        """
        验证文件是否有效
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 文件是否有效
        """
        import os
        if not os.path.exists(file_path):
            return False
        
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.get_supported_extensions()