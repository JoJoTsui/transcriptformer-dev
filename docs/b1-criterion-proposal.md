# B1 判据修订(预注册草案) / B1 Criterion Revision (Pre-registration Draft)

**状态(Status):** 草案,待签字(draft — sign-off required)。**必须在观察到任何微调模型留出集结果之前定稿;训练开始后本判据冻结,事后任何修改使预注册失效。** 原 "≥6/8 物种" 判据保留为历史记录(登记项 7.3/7.7),本文不追溯修改它,也不把它静默替换为两物种闸门。

**证据基础(Evidence):** [`logs/dataset_audit/holdout_coverage.json`](../logs/dataset_audit/holdout_coverage.json)(pre-QC 投影,seed 42);登记项 3.3、3.4、3.7、7.3、7.7;[续审 S3](agents/continuation-review-2026-09-22.md);[基线设计 §3](perturbation-and-baseline-design.md)。

---

## 中文

### 1. 为什么原 B1 不可执行

- 原判据:"留出 likelihood 平均改善 ≥ 5%,覆盖 8 个训练物种中的 ≥ 6 个,且任一物种退化不超过 2%"。
- 按 `(species, embryo_id)` 全局隔离与 train-only 规则,最终留出集**只存在于人和小鼠**;线虫、斑马鱼、果蝇、鸡、海胆、兔为单胚胎合并文件(按设计只入训练集),五个空间文件均为 train-only。任一物种内部按细胞划分留出已被否决(登记项 3.4:胚胎内泄漏)。
- **合作方待裁定第 1–3 项不会改变这一事实:** 第 1、2 项(小鼠 prenatal 图谱、Nature2019 multi-omics)均为小鼠数据,只会增加小鼠胚胎;第 3 项(采样加权)与留出资格无关。六物种无留出的缺口与这些决定正交。
- 所以 6/8 的分母在查看任何模型结果之前就已确定不可达(续审 S3)。不得在看到结果后改分母,也不得把训练观测计入留出。

### 2. 可测量的留出分层(pre-QC,最终以 QC 后为准)

| 物种 | 阶段 | 观测数 | 独立胚胎数 | 层级 |
|---|---|---:|---:|---|
| 小鼠 | gastrula | 7,838 | 11 | 主要(≥3 胚胎) |
| 小鼠 | neurula | 12,688 | 4 | 主要(≥3 胚胎) |
| 小鼠 | 无分期(unmapped) | 3,458 | 7 | 仅总体汇总,不进阶段解析 |
| 人 | organogenesis | 32,066 | 1 | 描述性(登记项 3.7:n=1) |

不同阶段行的胚胎计数可能重叠,**不得相加为独立供体**。小鼠无分期行为 1.15 的已知缺失,不参与阶段解析指标,但计入总体 likelihood。

### 3. 修订后的 B1(B1-A,推荐方案)

度量口径:留出集每细胞序列 log-likelihood(bits/cell,越高越好),记 `S`;改善率 `(S_ft − S_base) / |S_base|`。该口径把 "改善 ≥ 5%" 定义为相对基座绝对分值的 5%,对负分值亦有定义;若签字时改用其他口径(如按位元/token 的 NLL 相对下降),须在训练前写入本页。

1. **主要终点(小鼠,多胚胎留出):** 在最终留出集上,按胚胎聚合(每胚胎均值 → 胚胎层均值,登记项 3.7 的层级)。通过条件:每个合格阶段分层(≥ 3 个留出胚胎:gastrula n=11、neurula n=4,pre-QC)均改善 ≥ 5%,且任一分层退化不超过 2%。
2. **次要终点(人 organogenesis,单胚胎,n=1):** 描述性。通过条件:退化不超过 2%。只报告细胞层效应量与区间,明确标注"胚胎内、无胚胎层不确定性",不做推断性表述。
3. **无留出物种(6 个):** 不产生 B1 结论。仅报告训练拟合描述,报告中显式声明"无种内泛化证据"。
4. **配套闸门不变:** B2(阶段 kNN 纯度 ≥ +5 点)在同一留出队列上执行(小鼠为主要、人为描述性);B3 判据不变;B4 仍受探测资源阻塞,解阻后独立执行。
5. **冻结纪律:** 本判据与"合格分层名单"在任何微调模型留出评估之前冻结。QC 可能削减分层:prepare 完成后先重跑 `report_holdout_coverage.py`,以 QC 后数字冻结分层名单(某分层跌到 < 3 个胚胎即降为描述性,规则事前固定)。语料或 QC 任何后续变更都要求重新冻结并记录,不得在看到结果后调整阈值、分层或分母。
6. **结论表述范围:** 允许"微调在小鼠多胚胎留出上提升 likelihood,且在单个人胚胎上未退化";禁止对六个无留出物种作种内泛化声明。若基座已满足头条结论,微调降级为稳健性检验(基线设计 §3 原文不变)。

### 4. 备选方案

- **B1-B:补充独立胚胎后再定稿(备选)。** 为 ≥ 4 个无留出物种寻找带逐胚胎身份的多胚胎公开数据(每物种 ≥ 3 个合格胚胎),经跨文件 barcode 去重(登记项 1.1 的 D1 检查)与 QC 后重冻结分母,再回到近似原形的 6/8 判据。后果:训练延期;新数据同时进入语料/assay/QC 决策;需合作方提供或确认数据来源。
- **B1-C:仅描述,采纳闸门只用 B2/B3/B4(不推荐)。** 后果:采纳决定没有任何未见数据 likelihood 证据,证据强度显著下降。
- **否决:从单胚胎/合并数据集中按细胞或切片划出留出。** 违反登记项 3.4/3.6(胚胎内泄漏;切片不是独立胚胎),不列为选项。

### 5. 签字记录

| 项 | 选择(勾选) |
|---|---|
| 判据 | ☐ B1-A(推荐)☐ B1-B ☐ B1-C |
| 度量口径 | ☐ bits/cell 相对改善(本文 §3)☐ 其他(写明:____) |
| 阈值 | ☐ 沿用 5% / 2%(冻结设计原值)☐ 其他(写明:____) |

姓名/角色:____________　日期:____________

---

## English

### 1. Why the registered B1 cannot be executed

- Registered text: "Mean holdout likelihood improves ≥ 5% in ≥ 6 of 8 training species, with no species degrading > 2% (B1)."
- Under global `(species, embryo_id)` isolation and the train-only rules, the final holdout exists **only in human and mouse**. Worm, zebrafish, fly, chicken and urchin (and rabbit) are pooled single-embryo files pinned to training; all five spatial files are train-only. Carving per-cell holdout within one embryo is rejected (item 3.4: same-embryo leakage).
- **Collaborator decisions #1–#3 do not change this:** #1 and #2 (mouse prenatal atlas, mouse Nature2019 multi-omics) only add mouse embryos; #3 (sampling weights) does not affect holdout eligibility. The six-species gap is orthogonal to those decisions.
- The six-of-eight denominator is therefore unreachable before any model result exists (continuation review S3). The denominator must not be changed after results are seen, and training observations must never be counted as holdout.

### 2. Measurable holdout strata (pre-QC; freeze on post-QC numbers)

| Species | Phase | Observations | Unique embryos | Tier |
|---|---|---:|---:|---|
| mouse | gastrula | 7,838 | 11 | primary (≥ 3 embryos) |
| mouse | neurula | 12,688 | 4 | primary (≥ 3 embryos) |
| mouse | unmapped (unstaged) | 3,458 | 7 | overall summary only, never phase-resolved |
| human | organogenesis | 32,066 | 1 | descriptive (item 3.7: n = 1) |

Embryo counts in different phase rows may overlap and must not be summed as independent donors. The unstaged mouse rows are the known 1.15 missingness: excluded from phase-resolved metrics, counted in overall likelihood.

### 3. Revised B1 (B1-A, recommended)

Metric convention: per-cell sequence log-likelihood on the holdout (bits/cell, higher is better), `S`; improvement = `(S_ft − S_base) / |S_base|`. This makes "≥ 5% improvement" well-defined even for negative scores. Any other convention (e.g. relative NLL reduction per token) must be written into this page before training starts.

1. **Primary endpoint (mouse, multi-embryo holdout):** embryo-level aggregation (per-embryo means, then the embryo-level mean — the item 3.7 hierarchy) on final-holdout rows. Pass condition: every eligible phase stratum with ≥ 3 holdout embryos (gastrula n = 11, neurula n = 4, pre-QC) improves ≥ 5%, with no stratum degrading > 2%.
2. **Secondary endpoint (human organogenesis, single embryo, n = 1):** descriptive. Pass condition: no degradation > 2%. Report cell-level effect size and interval, explicitly labelled "within-embryo, no embryo-level uncertainty"; no inferential wording.
3. **Species without holdout (6):** contribute no B1 verdict. Training-fit descriptions only, with an explicit "no in-species generalization evidence" statement in every report.
4. **Companion gates unchanged:** B2 (phase kNN purity ≥ +5 points absolute) runs on the same holdout cohorts (mouse primary, human descriptive); B3 unchanged; B4 remains blocked on probe assets and runs independently once unblocked.
5. **Freezing discipline:** this criterion and the eligible-stratum list are frozen before any finetuned-model holdout evaluation. QC may shrink strata: re-run `report_holdout_coverage.py` on the prepared corpus and freeze on the post-QC numbers; any stratum dropping below 3 embryos demotes to descriptive by this pre-stated rule. Any later corpus or QC change requires a recorded re-freeze. Thresholds, strata and denominators must not be adjusted after results are seen.
6. **Claim scope:** permitted: "the finetune improves holdout likelihood in mouse across gastrula/neurula and does not degrade in a single human embryo"; prohibited: in-species generalization claims for the six holdout-less species. If the base model already satisfies the headline claims, the finetune is demoted to a robustness check (baseline design §3, unchanged).

### 4. Alternatives

- **B1-B: delay and source independent embryos first.** Acquire multi-embryo public datasets with per-embryo identities for ≥ 4 of the 6 species (≥ 3 eligible embryos per species), pass the cross-file barcode dedup (item 1.1, D1 check) and QC, re-freeze the denominator, then register a near-original 6/8-style criterion over the enlarged eligible set. Consequences: schedule slip; new data reopens corpus/assay/QC decisions; needs collaborator data or confirmation.
- **B1-C: descriptive B1 only; gate adoption on B2/B3/B4 (not recommended).** Consequences: adoption decided without held-out likelihood evidence; substantially weaker.
- **Rejected: carving holdout cells or sections out of single-embryo/pooled datasets.** Violates items 3.4/3.6 (same-embryo leakage; sections are not independent embryos). Not an option.

### 5. Sign-off record

| Item | Choice (tick) |
|---|---|
| Criterion | ☐ B1-A (recommended) ☐ B1-B ☐ B1-C |
| Metric convention | ☐ bits/cell relative improvement (§3) ☐ other (specify: ____) |
| Thresholds | ☐ carry over 5% / 2% (frozen design values) ☐ other (specify: ____) |

Name / role: ____________　Date: ____________
