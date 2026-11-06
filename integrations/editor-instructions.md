# 编辑器与知识库集成规则

**投资有风险，分析结果和查询结果不构成投资建议。**

本规则适用于使用本项目程序、导出格式或集成设施的编辑器、智能体、RAG 服务和个人知识库。集成用途必须符合 [LICENSE](../LICENSE) 的非商用要求。

## 必须实现的结果

每次向用户展示查询结果或分析结果时，在结果正文或紧邻结果的持久提示栏中显示以下原文：

> 投资有风险，分析结果和查询结果不构成投资建议。

显示区应可读。隐藏元数据、折叠的条款页面和仅出现一次的弹窗不能替代该提示。

## 接入步骤

1. 阅读 [机器协议](editor-contract.json)、项目许可和来源使用条件。
2. 将下方规则加入所用编辑器的项目规则或知识库系统指令。
3. 在导入前检查每条记录的 `risk_notice`、来源、日期和 `is_demo`。缺失时拒绝导入，或先重新生成完整导出。
4. 分块时将风险提示同时写入分块正文和分块元数据。仅继承父文档元数据不够。
5. 检索与模型调用时保留提示、出处、时间及演示标记。不要把未知字段补成事实。
6. 在最终回答渲染层固定显示提示。不要依赖模型偶尔遵守提示词。
7. 按下方验收步骤核对最终页面，再声明集成完成。

JSONL 与 CSV 的空结果会输出 `record_type: notice` 行，用来保留提示。它不是真实资料，导入器不得把它计作一篇报告或新闻。非空 JSONL 使用 `record_type: chunk`；非空 CSV 使用 `record_type: record`。

以下规则可加入 Cursor、VS Code、Obsidian 或其它编辑器的相应项目规则中。不同产品的规则入口和渲染能力不同；请使用其实际支持的机制。

```text
Financial Research Hub integration rules:
- Noncommercial use only. Preserve LICENSE, NOTICE and attribution.
- Show this exact notice with every query and analysis result:
  投资有风险，分析结果和查询结果不构成投资建议。
- Preserve the notice in every record, retrieval chunk and exported file.
- Hidden metadata alone does not satisfy visible-display requirements.
- Keep broker opinions, disclosed facts and generated analysis separate.
- Cite original source, direct provider and publication date when available.
- Preserve is_demo and clearly mark synthetic examples.
- Do not bypass source access controls or assume third-party redistribution rights.
```

## 集成验收

用合成记录完成以下检查，不要为验收上传私人研报：

| 操作 | 可观察通过条件 |
| --- | --- |
| 导入后搜索一条记录 | 结果旁可见完整中文风险提示；来源和演示标记保留 |
| 让编辑器生成一段分析 | 分析结果可见同一提示，并区分来源内容与生成推断 |
| 将文档拆为多个检索分块 | 每个分块正文和元数据均保留提示 |
| 导出为 JSON、CSV 或 Markdown | 每条记录均保留提示，日期与来源未丢失 |
| 移除提示后尝试导入 | 集成层拒绝导入，或先重新生成符合协议的数据 |

本仓库可以验证自带输出路径。它无法从技术上控制未知的外部编辑器。集成方负责实现显示层，并保留自己实际测到的验收结果。仅复制本文件或保存 `editor-contract.json`，不能证明编辑器已经满足要求。

