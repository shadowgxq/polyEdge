# Tasks

> 本 change 为后端单端纯计算，只保留 `## 后端` 分节；无对外接口、无前端、无 DB 迁移。

## 后端

- [x] 1.1 在 `backend/` `services` 层新建偏差计算模块目录（如 `services/bias_scoring/`），定义模块内**输入契约**数据结构：选项级 `price / volume / liquidity / volume24hr / traders(可 None) / depth(可选)`、事件级选项集合 + `commentCount`（仅透传，不参与偏差）。字段命名锚定 bias-algorithm §2 / data-source §2，并注释「依赖 poly-data-integration 提供选项级归一化字段」的契约假设（design D2）。
- [x] 1.2 定义参数配置对象与默认值：`α=0.7 / β=0.3`、`w_vol=w_liq=w_24h=w_turn=1/4`、`w_depth=0`、`T=15`（bias-algorithm §7、design D8）；`norm` 不入配置。
- [x] 1.3 实现归一函数 `norm(x_i)=x_i/Σ_j x_j`（份额型，钉死非可配置），含分量全 0 / Σ=0 除零兜底记 0、不产 NaN（bias-algorithm §3.2、design D3）。
- [x] 1.4 实现概率份额 `p_i = price_i/Σ price_j`（bias-algorithm §3.1）；`Σ price_j = 0` 触发「不适用偏差分析」路径。
- [x] 1.5 实现交易热度 `trade_i`：`turnover_i = clamp(volume24hr/volume,0,1)`（volume=0 记 0），四项 norm 加权合成，可选 `w_depth·norm(depth)` 默认关闭（bias-algorithm §3.2、design D4）。
- [x] 1.6 实现参与/持仓热度 `social_i = norm(traders_i)`，含退化判定谓词（缺失/null=无、0=有效 0）（bias-algorithm §3.3、design D2）。
- [x] 1.7 实现数据退化（混合退化口径）：事件内任一选项缺 per-option 参与数据 → 全事件 `h_i = trade_i`（等价 β=0），输出 `degraded_trade_only` 标注（bias-algorithm §3.5、design D6）。
- [x] 1.8 实现热度合成 `h_i = α·trade_i + β·social_i` 与热度份额 `hs_i = h_i/Σ h_j`，含 `Σ h_j = 0` → `hs_i = 1/n` 均分兜底（bias-algorithm §3.4/§3.6）。
- [x] 1.9 实现 `round` 半值向上进位（round half away from zero，用 Decimal ROUND_HALF_UP，`14.5→15`、`−14.5→−15`），实现 `d_i = hs_i − p_i` 与 `bias_i = clamp(round(d_i·100), −100, 100)`（bias-algorithm §3.7、design D5）。
- [x] 1.10 实现适用性边界与无效选项处理：单选项 / 缺价格标注「不适用偏差分析」不产 bias_i；价格全 0 / 数据缺失选项排除并标注，排除后 `p_i` 与 `hs_i` 在剩余有效集重归一使 Σ=1（bias-algorithm §6、design D6）。
- [x] 1.11 实现偏差三分类：阈值 `T` 默认 15，三档互斥（`≥+T` 泡沫 / `≤−T` 冷门 / `(−T,+T)` 合理），每标签产出中/英两套文案（bias-algorithm §4、PRD §5.4）。
- [x] 1.12 实现多事件排行分档口径：所有选项各在所属事件内算 bias_i，按 `±T` 对齐互斥无交集分三档（泡沫降序 / 冷门升序 / 合理列表），每项保留事件归属；TopN 截取不在本模块（bias-algorithm §5、design D7）。
- [x] 1.13 固化黄金 fixture 数据文件（固定输入 → 期望 bias_i/标签），覆盖 bias-algorithm §8 七类：正常多选项、阈值边界（+15/−15/14）、round 半值边界（14.5→15 / −14.5→−15）、clamp 边界、除零兜底（分量 Σ=0 / Σh=0 / volume=0）、参与数据退化、排除后重归一。数值人工精算并交叉核对（PRD AC-3、bias-algorithm §8、design D9）。
- [x] 1.14 编写 pytest 单测：逐条断言黄金 fixture 输入 → 期望输出；补真实/近真实数据的冒烟用例（不产 NaN、不抛异常、输出结构完整），不以真实数据断言具体数值。
- [x] 1.15 验证：`backend/` 下 `make lint`（ruff）+ `make test`（pytest）通过；无模型改动故无需迁移。
