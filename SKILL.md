# OTA 酒店多平台比价

对同一酒店（或同一城市、同一入住/离店日期）做美团、飞猪、携程、同程四平台价格比较。

## 何时用

- 用户说"比价 xx""查一下 xx 的酒店价格""对比几家平台""帮我比下 xx 酒店价格"等。
- 触发词示例："比价 杭州 2026-11-20 2026-11-21"、"帮我比下明天和平饭店的酒店价格"

## 标准流程（用户 2026-10-15 指定，2026-10-16 加入同程）

| 平台 | 路径 |
|---|---|
| 美团 | `custom.meituan-travel` 连接器（保险库凭证） |
| 飞猪 | 官方 `flyai` CLI（`~/.flyai/config.json` 已配正式 Key） |
| 携程 | 默认携程问道匿名接口；非必要不走 Trip.com 浏览器 |
| 同程 | 程心 skill `hotel-query.js`（`~/workspace/ota-tools/tongcheng/`，需 `CHENGXIN_API_KEY`），默认渠道 |

渠道优先级（用户 2026-10-16 指定）：携程默认走问道、同程默认走程心 skill，
浏览器只在必要时用（用户明确要各房型实时可订价而默认渠道没给全）。

## 两阶段工作流（用户 2026-10-15 指定）

用户问"哪个酒店好"（选酒店）时，先做阶段一；再做阶段二。用户直接点名酒店时，
可跳过阶段一。

### 阶段一：快速摸底（选酒店）

**规划行程、找酒店、确认候选时，优先用美团的工具**（查询速度快）。
先用美团确认候选酒店的**大概价格、位置**，从中锁定 1–3 家候选。
- 如需查询**基础信息**（面积、床型、设施设备、开业/装修时间、评分），
  除美团外，**同时检索携程问道**连接器的数据，两边对照。
- 飞猪（结构化 JSON，价格明码）主要用于阶段二的价格带确认。

### 阶段二：四平台比价

对阶段一锁定的每家候选酒店，四个平台**都必须返回结果**。
- **用模糊关键词搜索，不用精确匹配**：从酒店全名提炼关键词
  （品牌 + 地标/路名，如"全季 中山北路""希尔顿 禾木"），
  不同平台酒店名可能有差异
  （如"全季酒店(杭州城站地铁站西湖大道店)" vs "全季酒店杭州火车城站西湖大道店"），
  靠人工判断对齐是同一家。
- 美团、飞猪、同程走各自 skill/CLI；携程默认走携程问道（非必要不走浏览器）。

### 最终呈现：图文并茂（用户 2026-10-16 规范）

用 `widget.create_html_widget` 生成对比卡片，每家酒店一张卡，包含：
酒店图 + 平台 + 价格 + 房型 + 关键政策（早餐、取消）+ **各平台详情页/下单跳转链接**。
文字部分结论先行，再给推荐理由。

呈现规则（2026-10-16 用户指定）：
- **只展示最低价**：每平台只列最低价房型（注明房型名/面积/早餐/取消），
  不罗列全部房型；用户点名要某房型时才展示该房型价格。
- **设施设备提炼**：从多平台收集设施信息，提炼关键点以标签形式展示
  （如"丝涟床垫""行政酒廊""免费停车"），不贴大段原文。
- **排版**：卡片顶部酒店图 + 名称/钻级/评分/开业时间；中部各平台最低价行
  （平台名 + 口径标注 + 价格 + 预订链接）；下部关键设施标签 + 结论。
  各节字段以平台当次实际返回为准，没有的不硬凑。
- 查不到的平台明确写"当次未查到"，不编造。

## 执行方法

### 快捷：比价脚本（美团+飞猪+携程问道）

```bash
cd ~/workspace/ota-tools && python3 compare_hotels.py \
  --city <城市> --check-in YYYY-MM-DD --check-out YYYY-MM-DD [--limit 10]
```

结果存 `~/workspace/ota-tools/results/`。脚本内飞猪、美团为实时价，
携程问道为区间参考价。

### 精确：四平台分别查（推荐用于具体酒店比价）

**1. 美团**（自然语言问答，房型细节最全）
```bash
python3 ~/workspace/custom-connectors/custom.meituan-travel/bin/meituan-query.py \
  --query "<城市><酒店名><入住日期>入住<离店日期>离店<房型>价格" \
  --city <城市> --origin-query "<酒店名>价格"
```
返回 Markdown：房型名、床型、面积、入住人数、价格、取消政策、早餐、房型图、预订短链。
注意：价格有时脱敏（￥XX）；日期约束不一定被严格执行。

**2. 飞猪**（结构化 JSON，价格稳定明码）
```bash
cd ~/workspace/ota-tools && ./node_modules/.bin/flyai search-hotel \
  --dest-name <城市> --key-words "<酒店名>" \
  --check-in-date YYYY-MM-DD --check-out-date YYYY-MM-DD
```
返回 JSON `data.itemList[]`：name、price、star、address、brandName、
decorationTime、interestsPoi、latitude/longitude、mainPic、detailUrl、shId。
注意：价格为酒店级聚合价，非房型级；无面积、无房型详情。
Key 在 `~/.flyai/config.json`（用户轮换后需重新配置）。

**3. 携程**（默认走携程问道；非必要不走浏览器）

默认用携程问道匿名接口：
```bash
curl -s -X POST 'https://wendao-skill-prod.ctrip.com/skill/query' \
  -H 'Content-Type: application/json' \
  -d '{"query": "我需要查询<酒店全名>的所有房型的价格，入住日期YYYY年MM月DD日，离店日期YYYY年MM月DD日，请用md格式返回"}'
```
匿名可用。返回 Markdown：各房型名、参考价、面积、床型、含早、取消政策、预订链接。

注意（2026-10-16 实测结论）：
- 问道能给**最低起价参考**（如"最低约¥918/晚"），一次没拿到可重试 1–2 次；
  返回的是参考价，实际各房型价格会浮动。
- **全房型逐个的实时可订价**经常拿不到。
- 优势是房型清单最全（含面积/床型/楼层/早餐份数），适合做基础信息对照。

以下情况才走 Trip.com（非必要不走浏览器）：
- 用户明确要各房型实时可订价、而问道没给全时；
- 此时优先 TripGenie API（有 Key 时），其次浏览器。

TripGenie API（有 Key 时）：
```bash
export TRIPGENIE_API_KEY=<key>  # 去 www.trip.com/tripgenie/openclaw 申请
python3 ~/workspace/ota-tools/tripgenie-query.py \
  --query "<酒店全名><入住日期>入住<离店日期>离店，1间房2人，价格"
```
返回 Markdown（自然语言）：房型、价格、预订链接等。需自行解析。
注意：TripGenie 官方定位国际旅行；国内酒店更对口的是 TripAI（携程问道，`TRIPAI_API_KEY`）。

浏览器查 trip.com 实时价（最后手段）：
用 `browser.spawn_task`，任务描述包含：酒店全名、入住/离店日期（YYYY-MM-DD）、
间数、人数，要求返回基础房型名、每晚价格（含税优先，注明货币）、
是否含早、取消政策、价格页面 URL。只查价，不登录、不下单。

**4. 同程**（默认走程心 skill；非必要不走浏览器）

```bash
export CHENGXIN_API_KEY=<key>  # 去同程旅行 App 搜"程心激活码"申领
node ~/workspace/ota-tools/tongcheng/scripts/hotel-query.js \
  --destination "<城市>" --extra "<酒店关键词 入住日期入住 离店日期离店>" \
  --channel webchat --surface webchat
```
返回表格：酒店名、价格、类型、评分、设施、地址、预订链接（ly.com 短链）。
注意：未配 Key 时仅有极少量试用额度（约1次）；价格为同程实时价。
同程侧默认只用程心 skill，不走浏览器。

## 价格口径对照（汇报时必须说明）

- 美团：约价（"￥xxx起/晚"），有时脱敏；非保证可订价。
  ⚠️ 口径硬伤（用户 2026-10-15 指出）：ht-ai 为自然语言接口，无结构化产品类型字段，
  默认返回疑似团购口径而非日历房实时价。query 中明确要求"日历房、排除团购"后接口声称已排除，
  但无结构化字段可独立验证。美团侧价格仅作参考量级，不可与飞猪/Trip.com 日历房价严格对比。
- 飞猪：酒店级聚合价（明码）；非房型级可订价。
- 同程：实时价（程心 skill，默认渠道）；试用额度有限，正式使用需配 Key。
- 携程：默认携程问道（最低起价参考 + 全房型清单/基础信息最全）；
  全房型逐个实时可订价拿不到、且用户明确需要时，才走 TripGenie API 或 Trip.com 浏览器。
  浏览器非必要不走。

同房型对比时先对齐房型名；房型不同（如"家庭套房" vs "亲子家庭房"）不可直接比，
汇报时明确指出。

## 面积与基础信息对照

| 维度 | 飞猪 | 美团 | 携程问道 | 同程 |
|---|---|---|---|---|
| 房间面积 | ❌ | ✅ | ✅ | ⚠️ |
| 床型 | ❌ | ✅ | ✅ | ⚠️ |
| 房型列表 | ❌ | ✅ | ✅ | ⚠️ |
| 早餐/取消政策 | ❌ | ✅ | ✅ | ⚠️ |
| 设施详情 | ❌ | ⚠️ | ✅ | ✅ |
| 评分/星级 | ⚠️/✅ | ❌ | ✅ | ✅ |
| 经纬度/品牌 | ✅ | ❌ | ❌ | ⚠️ |
| 结构化程度 | 高 | 低 | 低 | 中 |

完整字段清单见 `~/workspace/ota-tools/INTERFACE_FIELDS.md`。

## 汇报规范

- 结论先行：先给推荐结论，再列四平台价格。
- 每个平台分节，列酒店名/房型/价格/关键政策（早餐、取消），**并附该平台商品详情页跳转链接**：
  - 美团：Markdown 中的 dpurl.cn 短链（跟在房型名后）；
  - 飞猪：JSON `detailUrl` 字段；
  - Trip.com：浏览器任务返回的价格页面 URL；
  - 同程：表格中的 ly.com 预订短链。
- 价格以工具实时返回为准，绝不编造；标注数据来源与查询时间。
- Trip.com 价格如为港币，必须按查询当日汇率换算成人民币再汇报
 （2026-10-15 中间价约 1 HKD = 0.853 CNY）。
- 房型口径不一致时明确指出，不可比的不硬比。
- 只查价、不下单；不碰支付；不改日历。

## 注意事项

- npm 包装在 `~/workspace/ota-tools/node_modules`（本地 prefix），VM 重建后仍在；
  不要装到 /usr/lib（VM 重建会丢）。
- 飞猪 Key 明文存于 `~/.flyai/config.json`（600 权限）；用户轮换后需重新配置。
  该 Key 曾进过聊天，按规范视为泄露，已建议用户轮换。
- 美团 Token、飞猪 Key 均曾进过聊天，均按泄露处理；后续凭证只走安全录入页。
- `custom.flyai` 连接器因签名机制（HMAC-SHA256 签名输入含 key 本身）与保险库不兼容，
  已建档停用；`custom.ctrip-wendao`（workbuddy 渠道，需 body token）同理不可用。
  详见各连接器目录下的 CONNECTOR.md。
- 社区抓取类工具违反平台 ToS，仅供个人研究；商用/对外发布前走官方商务合作。
- 用户是美团酒店 B2B PM，注意竞品价格监控的合规边界。

## 相关文档

- 接口字段全集：`~/workspace/ota-tools/INTERFACE_FIELDS.md`
- 同程程心 skill（官方）：`~/workspace/ota-tools/tongcheng/SKILL.md`，Key 申领见其说明
- 美团连接器：`~/workspace/custom-connectors/custom.meituan-travel/CONNECTOR.md`
- 飞猪连接器（已停用）：`~/workspace/custom-connectors/custom.flyai/CONNECTOR.md`
- 携程问道连接器（workbuddy 渠道，已停用）：`~/workspace/custom-connectors/custom.ctrip-wendao/CONNECTOR.md`
