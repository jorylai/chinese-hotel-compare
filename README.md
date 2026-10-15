# OTA 酒店多平台比价

能装在任意有浏览器功能的 personal agent，实现中国 OTA 全网比价。

对同一酒店（或同一城市、同一入住/离店日期）做**美团 / 飞猪 / 携程**三平台价格比较。
包含一个可复用的比价工作流（`SKILL.md`，适配 AI Agent 调用）+ 一个开箱即用的比价脚本。

## 功能

- **两阶段工作流**：先快速摸底锁定 1–3 家候选，再三平台精确比价
- **模糊关键词搜索**：从酒店全名提炼"品牌+地标"关键词（如"全季 中山北路"），人工对齐不同平台的酒店命名差异
- **价格口径透明**：每个平台的价格口径、缺失字段都在文档里写清楚，不硬比不可比的
- **图文卡片呈现**：酒店图 + 平台 + 价格 + 房型 + 关键政策 + 各平台下单跳转链接

## 安装

需要 Node.js ≥ 18 和 Python ≥ 3.9。

```bash
git clone https://github.com/<you>/ota-hotel-compare.git
cd ota-hotel-compare
npm install          # 安装 flyai 和 ht-ai 两个官方 CLI
```

## 凭证配置

### 美团（ht-ai）

1. 打开 [developer.meituan.com/zh/v2/dev/token](https://developer.meituan.com/zh/v2/dev/token)，按页面指引申请并复制你的 API Token。
2. 配置到环境变量（推荐）：
   ```bash
   export MEITUAN_HT_TOKEN=<你的token>
   ```
   也可以写入 `~/.config/meituan-travel/config.json` 的 `key` 字段。建议加到 `~/.bashrc` / `~/.zshrc` 持久化。
3. 验证：
   ```bash
   npx @meituan-travel/ht-ai@latest query --query "北京到上海的机票"
   ```

### 飞猪（flyai）

1. 去 [flyai.open.fliggy.com](https://flyai.open.fliggy.com/) 申请正式 API Key。
2. 配置：
   ```bash
   npx flyai config set FLYAI_API_KEY <你的key>
   ```
3. 不配 Key 也能用（体验模式），但价格会打码（如 ¥2xx）。

### 携程问道（区间参考）

- 匿名接口直接可用，无需配置（低频调用；未完全公开文档化，可能调整）。
- 如需正式 Key：去 [www.ctrip.com/wendao/openclaw](https://www.ctrip.com/wendao/openclaw) 申请，
  配置 `export TRIPAI_API_KEY=<key>` 或写入 `~/.config/tripai-skill/api_key`。
  官方仓库：[trips-ai/tripai-skill](https://github.com/trips-ai/tripai-skill)。

### Trip.com

无需配置，浏览器人工查实时价。

> ⚠️ 不要把任何 Key / Token 写进代码、文档或提交到 git，一律走环境变量或各 CLI 自带的 config。

## 使用

### 一键比价脚本

```bash
# 美团 token（可选，不配则美团侧跳过）
export MEITUAN_HT_TOKEN=<token>

python3 scripts/compare_hotels.py --city 杭州 --check-in 2026-11-20 --check-out 2026-11-21
```

输出三平台酒店列表（名称｜价格｜星级｜地址），结果 JSON 存到 `results/`。

### 作为 AI Agent 的 Skill

把本仓库的 `SKILL.md` + `skill.yaml` 放到你的 Agent 的 skills 目录即可。
Skill 内定义了完整工作流：

1. **阶段一 · 快速摸底**：用美团查大概价格/位置锁定候选；查基础信息（面积/床型/设施/开业时间/评分）时美团 + 携程问道同时检索、两边对照
2. **阶段二 · 三平台比价**：美团（`ht-ai` CLI）、飞猪（`flyai` CLI）、携程（浏览器查 trip.com 实时价），三个平台都要返回结果
3. **呈现**：图文卡片，每家酒店含图片、各平台价格、下单跳转链接；结论先行

触发词：`比价`、`酒店比价`、`查酒店价格`

## 价格口径（重要）

三家平台的价格口径**不一样**，汇报时必须说明，不可直接硬比：

| 平台 | 口径 |
|---|---|
| 美团 | 约价（"￥xxx起/晚"），有时脱敏；自然语言接口无结构化产品字段，可能混有团购口径，**仅作参考量级** |
| 飞猪 | 酒店级聚合价（正式 Key 下明码）；非房型级可订价 |
| Trip.com | 浏览器实时可订价，以页面为准（含税/不含税需注明；港币需按当日汇率换算） |
| 携程问道 | 区间/参考价；非保证可订价 |

各接口能返回哪些字段（面积、床型、设施、评分……），见 `docs/INTERFACE_FIELDS.md` 对照表。

## 合规

- 仅供个人研究使用；商用或对外发布前请走各平台官方商务合作。
- 注意竞品价格监控的合规边界。

## License

MIT
