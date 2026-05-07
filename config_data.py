
md5_path = './md5.text'

#RAG
collection_name = 'civil_law'
persist_directory = './chroma_db'

#spliter
chunk_size = 500  # 法条较短，减少块大小
chunk_overlap = 50
separators = ["\n\n", "\n", ".", "!", "?", "。", "？", "！", " ", ""]
max_split_char_number = 1000        #文本分割的阈值

# 新增法律专用配置
legal_max_results = 5  # 检索返回结果数
enable_citation = True  # 启用法条引用

#
similarity_threshold = 1            #检索返回匹配的文档数量

embedding_model_name = 'text-embedding-v4'
chat_model_name = 'qwen3.6-max-preview'

session_config = {
    "configurable": {
        "session_id": "user_001",
    }
}
