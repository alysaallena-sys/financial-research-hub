# 来源、接口参考与数据边界

投资有风险，分析结果和查询结果不构成投资建议。

本项目组合公开资讯和研报元数据接口。下表记录实现前核查的固定来源。所列第三方项目提供接口或设计参考；本项目不打包它们的源码或研报数据库。若今后复制代码，必须另行核对具体文件许可、署名和兼容性。

## 已核查的项目

| 项目与固定提交 | 代码许可或文档状态 | 参考范围 |
| --- | --- | --- |
| [AKShare](https://github.com/akfamily/akshare/tree/a199a70684165f08c16557a7b59b37bebdda7495) · `a199a70684165f08c16557a7b59b37bebdda7495` | MIT；数据说明另有限制 | 个股研报标题、机构、日期、评级、分年度 EPS/PE 和 PDF 链接；接口自身不读取 PDF |
| [report-cli](https://github.com/manymore13/report-cli/tree/0d98dde87a6b295359ae68152ca2693428baef83) · `0d98dde87a6b295359ae68152ca2693428baef83` | MIT | 个股、行业、宏观、策略和券商晨报的接口划分；旧 `manymore13/eastmoney` URL 会重定向至此仓库 |
| [a-share-research-monitor](https://github.com/nexaforgelab/a-share-research-monitor/tree/87940e4c87d2bde2af56813decb701bdb26d39a1) · `87940e4c87d2bde2af56813decb701bdb26d39a1` | Apache-2.0 | 稳定标识、快照与新增/更新差异的方法；不继承其默认新闻、模型或推送配置 |
| [manymore13/report](https://github.com/manymore13/report/tree/4818d294141c827ae056babfe1c63a51b0e4103d) · `4818d294141c827ae056babfe1c63a51b0e4103d` | Apache-2.0 | 日、周、月与行业目录的阅读组织；目录仓库不等于完整采集器 |
| [yfinance](https://github.com/ranaroussi/yfinance/tree/e2f6104164b70085556fe2f8e194cf3ca18550f5) · `e2f6104164b70085556fe2f8e194cf3ca18550f5` | Apache-2.0；README 提醒 Yahoo 数据个人用途条件 | Yahoo 聚合的机构评级事件和目标价共识；它与 Yahoo 无官方隶属关系 |
| [equity-research-reports-skill](https://github.com/Ray-Yuan21/equity-research-reports-skill/tree/0b0e11c133768681fb73bc33c3b779fdb0c93b3d) · `0b0e11c133768681fb73bc33c3b779fdb0c93b3d` | MIT | 公开候选的来源、新鲜度和目录规范；其开源搜索脚本只生成查询计划 |

AKShare、report-cli 和上述监控项目主要使用东方财富相关接口。不同库返回相同结果，不代表获得多个独立数据源。

## 第一版来源范围

| 来源 | 内容边界 | 使用时核对 |
| --- | --- | --- |
| BBC、Guardian 等固定公开资讯 Feed | 标题、链接、发表时间和短摘要 | Feed 是否允许当前用途；正文和媒体附件不在默认采集范围 |
| TED 公开 Feed | 演讲条目标题、链接、时间和短摘要 | Feed 当前可达性、署名、内容使用条款；不默认下载视频或字幕 |
| 东方财富研报接口 | 目录字段和公开原文链接 | 分页、日期、数量上限、字段变化、来源访问条件与原报告权利 |
| Yahoo，经可选 yfinance 适配器 | 机构评级事件 | 聚合来源的覆盖、延迟、缺失及个人用途条件；不保证完整投行覆盖 |

网页可读、URL 可取得、软件采用 MIT 或 Apache，均不能单独证明第三方数据允许批量保存、建库或再分发。用户应根据原来源条件决定本地留存范围。

## 明确保留的限制

- 查询结果是目录或评级事件时，不把它写成研报全文分析。
- 按数据集记录原发布机构与直接 provider。机构名称字段不表示程序直接连接该机构。
- 保留发表时间和首次观察时间。首次观察不等于刚刚发表。
- 报告缺失、分页截断、字段未知和来源失败都应显式显示。
- 同一元数据记录的更新不等于机构已经修改正文观点。观点变化需要原文与时间证据。
- 公开仓库不包含实时采集结果、文章全文、研报 PDF 或商业数据库内容。

## 不打包、不默认接入的项目

| 项目 | 原因 |
| --- | --- |
| [efinance](https://github.com/Micro-sheep/efinance/tree/c8fd370a3109b2d14a121e3a32a86e9c8354b01b) | 已核源码含关闭证书校验和 HTTP 路径；README 非商用声明与 MIT 文本并存。未解决这些问题，不能直接作为本项目默认依赖 |
| [FinceptTerminal](https://github.com/Fincept-Corporation/FinceptTerminal/tree/7716ee8613249fb44c4d14036c5bc16ed6f34e97) | 固定提交许可文件存在冲突；它还包含云模型、外部 MCP 和真实交易路径。这里只参考工作台功能分区，不复制 UI、资产或代码 |
| [ReportGem](https://github.com/littlemosquito123/reportgem-global-research/tree/835da7dc04df38856d5152324cf64690f4d556a7) | 仓库仅提供商业远程 MCP 接入说明。官网摘要限制批量抓取、建库和转发。付费服务与账号访问不在默认范围 |

ReportGem 的官网规则可能与固定 README 不同。核查时发现官网已更新搜索计费与订阅规则。后续如果评估该服务，应重新阅读其[官方说明](https://www.reportgem.com/en/mcp.html)和完整条款，不使用旧价格作承诺。

## HTTPS传输与TED路径

系统curl保持正常证书校验；参照[curl证书说明](https://curl.se/docs/sslcerts.html)及[官方参数手册](https://curl.se/docs/manpage.html)。项目仅提供显式选择，不会因Python证书错误自动切换，不修改系统CA或信任设置。

2026-11-06，官方起始地址`https://www.ted.com/feeds/talks.rss`的实际响应依次指向`https://pa.tedcdn.com/feeds/talks.rss`与`https://feeds.acast.com/public/shows/67587e77c705e441797aff96`。项目仅增加这两个精确主机，没有放宽为泛域。本次最终网络读取失败，不能把来源链确认写成TED采集成功。

## 软件许可与接口参考

本项目的原创实现适用 [LICENSE](../LICENSE)。可选包仍适用各自的软件许可。接口与数据格式参考不构成对原数据提供方的代理、合作或背书。

GitHub Actions 的基础配置参考 [GitHub Python 测试文档](https://docs.github.com/en/actions/tutorials/build-and-test-code/python) 和 [actions/setup-python 官方仓库](https://github.com/actions/setup-python)。2026-11-06 通过官方 GitHub tag ref 核对并固定：

- [`actions/checkout` v7](https://github.com/actions/checkout/tree/3d3c42e5aac5ba805825da76410c181273ba90b1)：`3d3c42e5aac5ba805825da76410c181273ba90b1`。
- [`actions/setup-python` v7](https://github.com/actions/setup-python/tree/6d4fd22b20465ccc0f7354476588e8df7c9ca0e0)：`6d4fd22b20465ccc0f7354476588e8df7c9ca0e0`。

工作流只运行离线测试，不定时采集金融来源。Action 与 Python 的准备过程可能连接 GitHub；测试本身不请求资讯或研报接口。

