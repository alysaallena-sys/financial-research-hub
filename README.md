# Financial Research Hub · 金融资讯组合

**投资有风险，分析结果和查询结果不构成投资建议。**

**仅限非商用。** 代码适用自定义的 [Financial Research Hub Noncommercial License 1.0](LICENSE)。本项目允许查看源码、非商用研究、修改和分享。商业用途需要相关权利人另行书面授权。它是 source-available 项目，不宣称采用 OSI 开源许可。

把公开新闻、TED 条目、券商研报目录和海外机构评级变化放进一个本地工作台。记录来源与时间，比较新增和更新，导出带风险提示的资料，供个人研究使用。

![Safari 中运行的工作台；画面内容均为合成演示数据](docs/images/demo-workspace.png)

## 能做什么

| 信息 | 第一版范围 |
| --- | --- |
| 公开新闻与 TED | 读取固定公开 RSS/Atom 源的标题、链接、日期和短摘要 |
| 国内券商研报 | 查询东方财富提供的个股、行业、宏观、策略与券商晨报元数据 |
| 海外机构评级 | 通过可选的 yfinance 适配器读取 Yahoo 聚合的评级事件 |
| 变化记录 | 保存本地 SQLite 快照，区分首次观察、新增、更新和未变 |
| 查询与简报 | 按类型、来源、证券代码或关键词筛选，生成可追溯的资料简报 |
| 知识库导出 | JSON、CSV、Markdown 与检索分块保留风险提示、来源和演示标记 |

研报目录包含哪些字段，取决于具体接口。目录记录不等于研报全文。评级事件也不等于投行的完整论证。不同程序共用东方财富或 Yahoo 时，仍是同一直接数据来源。

## 快速开始：先运行合成演示

需要 Python 3.11 或更高版本。基础功能使用 Python 标准库，不要求模型账号或数据 API key。

在项目目录运行：

```sh
git clone https://github.com/alysaallena-sys/financial-research-hub.git
cd financial-research-hub
python -m finance_research_hub --db .local/demo.sqlite3 demo
python -m finance_research_hub --db .local/demo.sqlite3 serve --demo --port 8765
```

然后打开 [本地工作台](http://127.0.0.1:8765)。演示内容均为合成样例。它们不代表真实新闻、真实机构观点或当前行情。

服务默认只绑定本机回环地址。它不会自动向互联网发布页面。上述命令将演示记录放入 `.local/demo.sqlite3`，与默认的 `.local/research.sqlite3` 分开。关闭服务时，在启动它的终端按 `Ctrl+C`。

## 查询、简报和导出

```sh
python -m finance_research_hub --db .local/demo.sqlite3 query --kind research
python -m finance_research_hub --db .local/demo.sqlite3 brief
python -m finance_research_hub --db .local/demo.sqlite3 export --format markdown
python -m finance_research_hub --db .local/demo.sqlite3 export --format csv
python -m finance_research_hub --db .local/demo.sqlite3 export --format json
python -m finance_research_hub --db .local/demo.sqlite3 export --format jsonl
```

具体参数以 `python -m finance_research_hub --help` 及子命令帮助为准。`--db` 省略时使用 `.local/research.sqlite3`。JSON 同时提供记录与带提示的检索分块；JSONL 按分块输出。空结果的 JSONL 和 CSV 仍输出一条 `record_type: notice` 提示记录；它不是资料条目，导入时应先区分类型。查询和导出只读取本地库。它们不会暗中发起采集、模型调用或 PDF 下载。

## 可选的实时元数据采集

演示模式之外，采集需要显式的 `--live`。先核对 [来源说明](docs/SOURCES.md)，再选择允许使用的来源。以下命令说明功能入口，不表示第三方接口已经完成运行验收：

```sh
python -m finance_research_hub collect --source bbc --live
python -m finance_research_hub collect --source guardian --live
python -m finance_research_hub collect --source ted --live
python -m finance_research_hub collect --source eastmoney --symbol 600519 --live
```

研报类型可选 `stock`、`industry`、`strategy`、`macro`、`morning`。指定股票时使用 `--symbol`；指定行业时使用 `--industry`。用 `--begin`、`--end` 明确日期，并用 `--max-pages`、`--page-size` 限定结果。程序默认查询最近 7 天；最多 10 页，每页最多 100 条。结果会保留覆盖或截断状态。

```sh
python -m finance_research_hub collect --source eastmoney --report-type macro --begin 2026-01-01 --end 2026-01-07 --max-pages 1 --page-size 20 --live
```

此处的固定日期只是参数示例，不代表已取得该期间的完整数据。

海外评级适配器需要用户自行安装可选依赖：

```sh
python -m pip install '.[ratings]'
python -m finance_research_hub collect --source yahoo --symbol AAPL --live
```

安装依赖会连接软件包源。实时采集会连接相应数据源。任何采集都有超时、分页或数量上限。请结合返回的覆盖信息判断结果，不能把有限页面当成完整历史。

如果 Python 的 CA 配置不完整，而系统 `curl` 可以正常验证来源证书，可显式选择系统传输：

```sh
python -m finance_research_hub collect --source bbc --transport curl --live
```

该选项只适用于 RSS 和东方财富适配器。它继续校验 HTTPS 证书，并逐跳核对来源白名单。它不会关闭证书验证，也不会修改系统信任设置。yfinance 使用自己的网络实现，不接受此覆盖选项。

2026-11-06的小样本核查已取得BBC、Guardian和东方财富一页研报元数据。TED的官方跳转链已核，本次最终网络请求失败，当前保留待验状态。海外评级的可选依赖尚未运行验收。详见[验收范围](docs/ACCEPTANCE.md)。

本项目不内置付费研报库、不采集付费媒体、不下载研报 PDF、不执行交易，也不自动运行模型、通知或定时任务。第三方访问失败时，应保留失败状态；不要绕过来源限制。

## 导入编辑器、智能体或知识库

**任何使用本项目构建知识库的集成方，都必须让编辑器在查询结果和分析结果中可见展示：**

> 投资有风险，分析结果和查询结果不构成投资建议。

保留每条记录、每个检索分块和导出文件中的同一提示。仅存入隐藏元数据、仅放在许可页面或仅显示一次弹窗，都不满足项目集成条件。

- 机器可读协议：[integrations/editor-contract.json](integrations/editor-contract.json)
- 集成与验收步骤：[integrations/editor-instructions.md](integrations/editor-instructions.md)
- 项目智能体规则：[AGENTS.md](AGENTS.md)

本仓库能在自带页面、CLI 和导出路径中实现提示保留。它无法从技术上强制未知的第三方编辑器执行规则。外部集成方必须检查最终显示效果，不得宣称未验收的集成已经合规。

## 数据与隐私

本地数据库、日志、凭据、真实采集结果和取得的原始研报不应进入公开仓库。`.gitignore` 已排除常见本地状态。发布前仍需检查实际文件清单。公开仓库只包含程序、文档、测试及明确标记的合成样例。

每条内容应区分原发布机构与直接数据提供方，并保留发表时间、采集时间和当前覆盖状态。公开可读不等于允许批量保存或再分发。软件许可也不替代数据、文章或研报的使用条件。

## 验证与贡献

```sh
python -B -m unittest discover -s tests -v
```

离线测试使用合成输入。测试不请求真实金融接口，不调用模型，不下载报告。GitHub Actions 使用只读仓库权限运行同一测试入口。工作流通过与第三方接口当前可用，是两种不同证据。

阅读 [验收范围](docs/ACCEPTANCE.md)、[贡献规则](CONTRIBUTING.md) 和 [安全说明](SECURITY.md)。新增来源时，要补充接口覆盖、权利边界、失败行为及风险提示保留验证。

## 授权与风险

[LICENSE](LICENSE) 和 [NOTICE](NOTICE) 约束本项目原创代码及文档。第三方包和数据继续适用原条款。项目不保证数据完整、准确或及时，不保证投资收益，也不提供投资、法律或税务建议。

