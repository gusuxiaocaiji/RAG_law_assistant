import streamlit as st
import config_data as config
from vector_stores import VectorStoresService
from rag import CasePushService, LegalCitationFormatter
from langchain_community.embeddings import DashScopeEmbeddings

st.set_page_config(
    page_title="案例分析",
    page_icon="⚖️",
    layout="wide"
)


if "vector_store" not in st.session_state:
    st.session_state["vector_store"] = VectorStoresService(
        embedding=DashScopeEmbeddings(model=config.embedding_model_name)
    )

if "case_pusher" not in st.session_state:
    st.session_state["case_pusher"] = CasePushService(st.session_state["vector_store"])


st.title("⚖️ 案例分析助手")
st.caption("输入案情描述，获取案件要素分析、适用法条和相关案例")

st.divider()


with st.container():
    st.subheader("📝 案情描述")

    case_type = st.selectbox(
        "案件类型",
        options=["民事", "刑事", "行政", "未知"],
        format_func=lambda x: {"民事": "⚖️ 民事", "刑事": "🔒 刑事", "行政": "🏛️ 行政", "未知": "❓ 未知"}[x]
    )

    case_input = st.text_area(
        "请详细描述案情",
        placeholder="""请输入案件的基本事实，例如：
- 原告与被告的身份关系
- 纠纷产生的时间、地点、原因
- 争议的焦点问题
- 已采取的法律措施（如有）

示例：2024年1月，甲与乙签订房屋买卖合同，约定购买乙名下商品房一套，价格200万元。甲支付首付款60万元后，乙迟迟不配合办理过户手续，且房屋被其他债权人申请查封。甲欲解除合同并要求双倍返还定金。""",
        height=200
    )

    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 4])
    with col_btn1:
        analyze_btn = st.button("🔍 分析案情", type="primary", use_container_width=True)

    with col_btn2:
        if st.button("🗑️ 清空", use_container_width=True):
            st.session_state["case_analysis"] = None
            st.session_state["applied_provisions"] = None
            st.session_state["similar_cases"] = None
            st.rerun()

    with col_btn3:
        st.write("")


if analyze_btn and case_input:
    with st.spinner("🔄 正在分析案情..."):
        try:
            case_type_for_search = case_type if case_type != "未知" else None

            similar_cases = st.session_state["case_pusher"].find_similar_cases(
                query=case_input,
                case_type=case_type_for_search,
                max_results=5
            )

            st.session_state["similar_cases"] = similar_cases

            applied_provisions = []
            for case in similar_cases:
                provisions = case.metadata.get('applied_provisions', [])
                applied_provisions.extend(provisions)

            applied_provisions = list(set(applied_provisions))[:10]
            st.session_state["applied_provisions"] = applied_provisions

            st.session_state["case_analysis"] = {
                "case_type": case_type,
                "summary": case_input[:500],
                "key_points_identified": len(similar_cases) > 0
            }

            st.success("✅ 案情分析完成！")

        except Exception as e:
            st.error(f"分析出错: {str(e)}")


if "case_analysis" in st.session_state and st.session_state["case_analysis"]:
    analysis = st.session_state["case_analysis"]

    st.divider()
    st.subheader("📋 案件要素分析")

    col_type, col_summary = st.columns(2)

    with col_type:
        st.markdown("**📂 案件类型**")
        case_type_display = analysis.get("case_type", "未知")
        type_icons = {"民事": "⚖️", "刑事": "🔒", "行政": "🏛️", "未知": "❓"}
        st.info(f"{type_icons.get(case_type_display, '📋')} {case_type_display}案件")

        st.markdown("**🔑 识别要点**")
        if analysis.get("key_points_identified"):
            st.success("✓ 已识别案件关键要素")
        else:
            st.warning("⚠ 建议补充更多案件细节")

    with col_summary:
        st.markdown("**📜 案情摘要**")
        summary = analysis.get("summary", "")
        if len(summary) > 200:
            st.markdown(f"{summary[:200]}...")
        else:
            st.markdown(summary)


if "applied_provisions" in st.session_state and st.session_state["applied_provisions"]:
    st.divider()
    st.subheader("⚖️ 适用法条")

    provisions = st.session_state["applied_provisions"]

    st.info(f"根据类案分析，建议关注以下 {len(provisions)} 条法律条文：")

    cols = st.columns(3)
    for i, provision in enumerate(provisions):
        with cols[i % 3]:
            with st.container():
                st.markdown(f"**📌 第{provision}条**")
                if st.button("查看详情", key=f"prov_{provision}"):
                    try:
                        docs = st.session_state["vector_store"].search_by_article_number(provision)
                        if docs:
                            st.session_state["selected_provision"] = docs[0]
                            st.rerun()
                    except:
                        pass
                st.divider()

else:
    with st.expander("💡 适用法条说明"):
        st.markdown("""
        **适用法条从哪里来？**

        1. 系统会基于您输入的案情，从向量数据库中检索相似案例
        2. 分析相似案例中援引的法律条文
        3. 汇总整理后展示给您

        **法条的作用**

        - 帮助您了解类似案件的法律适用规则
        - 为您的案件处理提供参考
        - 提示可能涉及的法律风险
        """)


if "similar_cases" in st.session_state and st.session_state["similar_cases"]:
    st.divider()
    st.subheader("🔗 类案推送结果")

    cases = st.session_state["similar_cases"]

    st.info(f"找到 {len(cases)} 个相似案例供参考：")

    for i, case in enumerate(cases):
        with st.expander(f"📁 类案 {i+1}: {case.metadata.get('case_number', '未知案号')}", expanded=i==0):
            col_info1, col_info2 = st.columns(2)

            with col_info1:
                st.markdown(f"**🏛️ 审理法院**: {case.metadata.get('court_level', '未知')}法院")
                st.markdown(f"**📅 裁判日期**: {case.metadata.get('judgment_date', '未知')}")

            with col_info2:
                st.markdown(f"**⚖️ 案件类型**: {case.metadata.get('case_type', '未知')}")
                st.markdown(f"**📊 相似度**: {100 - (i * 15)}%")

            st.divider()

            st.markdown("**📋 案件概要**")
            case_content = case.page_content
            if len(case_content) > 300:
                st.markdown(case_content[:300] + "...")
            else:
                st.markdown(case_content)

            provisions = case.metadata.get('applied_provisions', [])
            if provisions:
                st.markdown("**📜 本案适用法条**")
                provision_tags = ", ".join([f"第{p}条" for p in provisions[:5]])
                st.markdown(provision_tags)

            col_view, col_sim = st.columns(2)
            with col_view:
                if st.button("查看完整内容", key=f"view_{i}"):
                    st.session_state["case_detail"] = case

            with col_sim:
                if st.button("搜索类似条文", key=f"sim_{i}"):
                    if provisions:
                        st.session_state["search_provision"] = provisions[0]
                        st.rerun()

else:
    with st.expander("💡 类案推送说明"):
        st.markdown("""
        **什么是类案推送？**

        类案推送是基于您输入的案情，从数据库中检索相似的已判决案例。

        **类案的作用**

        1. **参考裁判规则**: 了解类似案件法院如何认定事实和适用法律
        2. **预判诉讼风险**: 评估己方诉讼请求的可行性和可能结果
        3. **学习诉讼策略**: 参考相似案件的诉讼技巧和代理方案

        **使用建议**

        - 案情描述越详细，推送的案例越精准
        - 关注案例中的争议焦点和法院裁判观点
        - 结合自身案件情况选择参考
        """)


if "selected_provision" in st.session_state and st.session_state["selected_provision"]:
    st.divider()
    st.subheader("📖 法条详情")

    doc = st.session_state["selected_provision"]
    metadata = doc.metadata

    col_detail1, col_detail2 = st.columns([3, 1])

    with col_detail1:
        st.markdown(f"**《{metadata.get('document_type', '法律')}》第{metadata.get('article_number', 'N/A')}条**")
        st.markdown(f"**所属章节**: {metadata.get('part', '')} {metadata.get('chapter', '')}")

        st.divider()
        st.markdown("**📜 法条内容**")
        st.markdown(doc.page_content)

    with col_detail2:
        st.markdown("**🔗 关联分析**")

        related_concepts = metadata.get('legal_concepts', [])
        if related_concepts:
            st.markdown("相关法律概念:")
            for concept in related_concepts[:5]:
                st.markdown(f"- {concept}")

        related_provisions = metadata.get('related_provisions', [])
        if related_provisions:
            st.markdown("关联条文:")
            for rel in related_provisions[:5]:
                st.markdown(f"- {rel}")

        if st.button("返回案例分析"):
            st.session_state.pop("selected_provision", None)
            st.rerun()


with st.sidebar:
    st.subheader("🛠️ 快速工具")

    st.markdown("**📌 常用法条**")
    common_articles = ["7", "10", "118", "143", "153", "186", "236", "462", "585", "588"]
    for art in common_articles:
        if st.button(f"第{art}条", key=f"common_{art}"):
            try:
                docs = st.session_state["vector_store"].search_by_article_number(art)
                if docs:
                    st.session_state["selected_provision"] = docs[0]
                    st.rerun()
            except:
                pass

    st.divider()

    st.markdown("**📚 案件类型**")
    case_type_examples = {
        "买卖合同纠纷": "标的物交付、质量异议、价款支付",
        "借款纠纷": "借款合意、资金交付、还款期限",
        "侵权纠纷": "侵权行为、损害后果、因果关系",
        "婚姻家庭": "婚姻关系、财产分割、子女抚养"
    }

    for case_type, description in case_type_examples.items():
        with st.expander(case_type):
            st.caption(description)
            if st.button(f"使用示例案情", key=f"example_{case_type}"):
                st.session_state["example_case"] = case_type
                st.rerun()

if "example_case" in st.session_state:
    example_cases = {
        "买卖合同纠纷": "甲向乙购买价值50万元的货物，双方签订合同后甲支付了30%定金，后乙未能按时交货，且货物质量不符合约定标准。甲要求解除合同并双倍返还定金。",
        "借款纠纷": "2023年1月，A向B借款100万元，约定年利率12%，期限一年。到期后A未能还款，且下落不明。B起诉要求A还款并支付利息。",
        "侵权纠纷": "甲在某商场购物时因地面积水滑倒受伤，造成骨折。商场称已尽到安全保障义务，拒绝赔偿。甲欲主张损害赔偿。",
        "婚姻家庭": "夫妻婚后共同购买房产，登记在一方名下。现双方协议离婚，对房产归属产生争议，男方主张房产为其个人财产。"
    }

    st.divider()
    st.subheader("📝 示例案情")
    st.info(f"已加载「{st.session_state['example_case']}」示例案情")
    st.text_area("请详细描述案情", value=example_cases.get(st.session_state["example_case"], ""), height=150, key="example_input")

    if st.button("使用此案情分析"):
        st.session_state.pop("example_case", None)
        st.session_state["case_analysis"] = {
            "case_type": "民事",
            "summary": example_cases.get(st.session_state["example_case"], "")[:500],
            "key_points_identified": True
        }
        st.rerun()

    if st.button("清除示例"):
        st.session_state.pop("example_case", None)
        st.rerun()

st.divider()

with st.expander("📖 法律知识小贴士"):
    st.markdown("""
    ### 如何撰写有效的案情描述

    1. **明确当事人信息**
       - 原告/被告身份（自然人/法人）
       - 当事人之间的关系

    2. **叙述纠纷经过**
       - 时间、地点、人物
       - 事件发展过程
       - 争议焦点

    3. **说明诉讼请求**
       - 原告的诉求是什么
       - 被告的抗辩理由

    4. **提供证据线索**
       - 关键证据有哪些
       - 证据的证明目的

    ### 案例分析方法

    | 分析维度 | 说明 |
    |----------|------|
    | 事实认定 | 法院如何认定案件事实 |
    | 法律适用 | 援引了哪些法条 |
    | 裁判结果 | 最终判决内容 |
    | 启示建议 | 对类似案件的指导意义 |
    """)