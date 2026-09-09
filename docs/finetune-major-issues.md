# 多物种胚胎发生微调的主要问题清单(中文版)

汇总本次微调的所有重大问题——来源包括对抗性评审(`docs/agents/adversarial-review-2026-09-09.md`)、数据集审计(`logs/dataset_audit/`)、整改计划(ADR 0003)以及验证设计文档(`docs/perturbation-and-baseline-design.md`)。**计算资源类问题(显存、单轮训练时长、GPU 数量、WSL 内存)不在本文范围内**——它们单独记录在评审报告的 C 类发现和训练准备清单中。

状态标记:**已解决**(已修复并验证,附提交号)· **已设计**(方案已确定,实现待做)· **待决**(尚无定论)· **已接受**(已知局限,附缓解措施)。

---

## 1. 语料库组成与数据完整性

| # | 问题 | 状态 |
|---|---|---|
| 1.1 | **TOME 与原肠胚图谱重复(D1)。** 8 个 TOME 文件(E6.75–E8.5a,共 105,373 个细胞)与 139k 细胞的原肠胚图谱逐字节重复;TOME E6.5 也有 78.4% 重复且计数向量完全一致。相同细胞可能同时落入训练集和留出集。 | **已解决** — 丢弃 9 个文件,保留图谱;`validate_manifest.py` 新增跨文件去重检查(同一物种文件间共享 barcode 超过 1,000 即硬性失败;当前 106 对比较全部通过)。`c088eeb` |
| 1.2 | **TOME E8.5b 来源未证实。** 与图谱无 barcode 重叠、命名空间不同,但无法对照原始发表确认其出处。 | **待决** — 暂保留在清单中,已在 `logs/dataset_audit/composition.md` 标记为可丢弃候选。训练前需做决定。 |
| 1.3 | **人 CS6 fig3 ⊂ fig2(D2)。** 8,445 个 spot,obs 名 100% 重合;三个 fig 文件本属同一胚胎却带三个 embryo_id。 | **已解决** — 丢弃 fig3;fig1/fig2 共用 `embryo_id: human_cs6`,保留不同 section_id。`c088eeb` |
| 1.4 | **果蝇重建 raw 文件缺少可用元数据。** 547,805 个细胞的 `cell_type` 全为 "unknown",且 assay 常量错误(应为 sci-RNA-seq3 而非 10x)。 | **已解决** — 从 Science 2022 注释文件按 obs 名 100% 匹配并入 `cell_type`(51 类,仅 0.55% unknown)与 `predicted_doublet`;assay 更正为 sci-RNA-seq3(GSE190147)。`c088eeb` |
| 1.5 | **果蝇 `predicted_doublet` 无信息量** — 注释源中该列为单一取值 "Singlet"。 | **已接受** — 如实并入;该注释无法用于双联体过滤。 |
| 1.6 | **小鼠时间序列的"空孔"。** 4,188 个 `embryo_id == "empty"` 的细胞(空板孔)会被按胚胎划分逻辑当作一个"胚胎"。 | **已解决** — 在源头剔除(59,136 → 54,948 细胞,188 个真实胚胎),记录于 `uns["empty_well_exclusion"]`。`c088eeb` |
| 1.7 | **非整数/已处理矩阵。** 部分源文件提供的是归一化或缩放后的值(CS9 空间数据、兔图谱、Tyser CS7、果蝇连续体)而非原始计数。 | **已解决** — raw 层已重建并全量校验;CS9 确属缩放数据已剔除;重新生成的审计确认清单内所有数据集均为整数值。 |
| 1.8 | **脊椎动物囊胚期覆盖单薄(S7)。** 小鼠合计仅 952 个细胞(每文件 67–464);人囊胚期数据完全缺失。 | **已接受** — 已发表图谱的固有数据局限;囊胚期结论只能限于小鼠且须标注低样本量。 |
| 1.9 | **物种鉴定错误。** 海胆数据集实为 *Lytechinus variegatus* 而非最初假定的 *S. purpuratus*;清单此前也没有显式物种字段。 | **已解决** — 全部 27 个条目均带显式 `species` 字段(校验器强制格式)。`c088eeb` |
| 1.10 | **审计产物过时。** report.json/summary.txt 描述的还是整改前 37 条目的语料。 | **已解决** — 已按 27 条目清单重新生成(2,855,332 细胞 / 22 个单细胞文件 + 412,374 个 spot / 5 个空间文件)。`85d43fc` |
| 1.11 | **小鼠 E8–P0 出生前时间序列(Nature 2024)在库但完全未使用。** 与用户的物种数据集思维导图(物种.xmind / 胚胎期单细胞转录组物种与数据集.png)核对时发现:`Nature_2024_prenatal_time_lapse`(45 个时间点、约 1,144 万细胞核,E8 至出生)在磁盘上,但从未进入审计、清单或任何计划文档——它是整个收藏中最大的数据集,比现有语料总和还大约 3.5 倍。 | **待决** — 建议明确记录为排除:其大部分阶段超出胚胎发生范围(延伸至出生),且纳入会让小鼠占比从 53% 升至约 90%,加剧鼠偏倚。可选:仅挖掘其 E8–E13.5 窗口补充神经胚/器官发生期数据。需用户裁定。 |

## 2. 胚胎发生(分期 → 阶段)映射

| # | 问题 | 状态 |
|---|---|---|
| 2.1 | **果蝇滑动窗口"不一致"(S4)。** 相互重叠的 4 小时采样窗口(hrs_06_10 与 hrs_08_12)把同一段 8–10 小时间隔分到了两个阶段——看似映射错误。 | **已解决(作为约定)** — 每个窗口按**中点**归入唯一阶段(胚带延伸 ≈ 4–9 h → 神经胚期);规则已写入 `preprocess/stage_phase_mapping.md`。但逐阶段*分析*必须按窗口中点把每个细胞去重到单一阶段——**实现待做**(分析层)。 |
| 2.2 | **线虫 100–130 分钟分箱误配。** 线虫原肠胚形成始于 26–28 细胞期(约受精后 100 分钟),原标为囊胚期的该分箱已覆盖早期原肠胚形成。 | **已解决** — 移至原肠胚期(用户裁定,记录于 `stage_phase_mapping.md` 与清单)。`fa5cf1b` |
| 2.3 | **斑马鱼 24 hpf 误配。** 24 hpf 是咽胚期起点,而非器官发生期。 | **已解决** — 移至神经胚期(用户裁定,已记录)。`fa5cf1b` |
| 2.4 | **边界判定缺乏文献依据。** 五项边界判定此前仅凭经验。 | **已解决** — 完整引文表见 `docs/perturbation-and-baseline-design.md` §5(O'Rahilly & Müller、Downs & Davies、Kimmel、Hamburger & Hamilton、Sulston、Campos-Ortega & Hartenstein、Ton 2023、Massri 2021)。 |
| 2.5 | **斑马鱼"神经胚期"是系统型对齐约定。** Kimmel 分期本无"神经胚"一词;14–24 hpf = 体节期/咽胚期。果蝇胚带与线虫 comma 期归入神经胚期同理——无脊椎动物没有真正的神经胚。 | **已接受** — 明确记录为约定而非事实;所有跨物种结论必须承认这一粗粒度阶段词表。 |
| 2.6 | **边界稳健性未验证。** 任何一个分箱边界的错误都会改变阶段构成。 | **已设计** — 预注册敏感性分析:每个边界向两侧各平移一个分箱,重跑核心指标;验收标准 = 每个分层 top-100 扰动命中基因在两种平移下保持 ≥ 80% 重合。训练后执行。 |

## 3. 数据集划分与留出设计

| # | 问题 | 状态 |
|---|---|---|
| 3.1 | **划分按文件常量而非按胚胎(D4)。** 真实的逐胚胎 obs 列(小鼠时间序列 189 个胚胎、人 CS12–16 共 7 个胚胎)从未被使用;ADR 中"单胚胎数据集仅入训练集"的规则没有实现机制。 | **已解决** — 两遍式按(数据集 × 胚胎)划分 + 按物种分层;每条划分连同原因记录于 `split_assignments.json`。`55225c3` |
| 3.2 | **seed-42 划分经实证损坏(P1)。** 斑马鱼整体落入验证集(从未参与训练,却驱动早停);最终留出集仅覆盖 8 个物种中的 2 个。 | **已解决** — 按物种 + 数据类型分层;保证每个物种至少有 1 个胚胎进入训练集。`55225c3` |
| 3.3 | **留出集代表性缺口(3.1 修复的必然结果)。** 混合单胚胎数据集(线虫、兔、鸡、果蝇、斑马鱼)永远只进训练集——留出指标只能来自多胚胎文件(小鼠时间序列、人 CS12–16、空间切片)。 | **已接受** — 依 ADR 0002/0003;留出指标对这五个物种的种内泛化不提供任何信息。跨物种结论须依靠直系同源/阶段分析和零样本探测物种。 |
| 3.4 | **单胚胎数据集的细胞级泄漏。** 在同一胚胎内按细胞划分会把胚胎状态泄漏进留出集。 | **已解决** — 设计上已否决(ADR 0002);单胚胎/单切片数据集仅入训练集。 |
| 3.5 | **同一胚胎的空间切片。** CS6 fig1/fig2 是同一胚胎的切片;分开划分会产生泄漏。 | **已解决** — 共用 embryo_id、保留不同 section_id;按切片划分保证它们同侧。`c088eeb` |
| 3.6 | **没有阶段留出,也没有物种留出。** 当前设计按*胚胎*留出;无法度量对未见阶段或训练集内未见物种的泛化。 | **已接受** — 未见物种泛化改由保留的零样本探测物种覆盖(猕猴、猪、豚鼠、热带爪蟾、海鞘、文昌鱼);对时间序列数据而言阶段留出本无意义(阶段是连续体)。 |
| 3.7 | **伪重复(S5)。** 339 万细胞 ≈ 每个 物种 × 阶段 仅 n = 1–3 个胚胎(人原肠胚期 = 1 个 CS6 + 1 个 CS7 胚胎;兔/鸡/果蝇/线虫各为 1 个混合文件)。 | **已设计** — 所有推断在胚胎层面聚合;每张结果表报告每个 物种 × 阶段 的胚胎数 n;n = 1 的分层仅作描述性报告,不做不确定性声明、不用因果措辞。属分析层规则,在报告时强制执行。 |
| 3.8 | **采样加权不一致(来自 C8)。** 计划声称"自然采样加权",但 `BalancedDataset` 实际把空间数据过采样约 2.4 倍、重复小数据集,其 (stage, cell_type) 上限会把果蝇 54.7 万细胞压缩进 ≤ 11 个组。 | **待决** — 训练配置定稿时需裁定:接受当前 `BalancedDataset` 行为,还是实现真正的自然加权模式。 |

## 4. 基因标识、映射覆盖率与直系同源

| # | 问题 | 状态 |
|---|---|---|
| 4.1 | **版本号剥离破坏了非 Ensembl 标识(D3)。** 按 "." 截断毁掉了 8,693 个线虫序列名(`2L52.1`)和 2,073 个斑马鱼旁系同源符号(`acy3.1`);声称的 90% 线虫覆盖率实际只有约 47%。 | **已解决** — 剥离仅限 Ensembl/FBgn/WBGene 模式;覆盖率已按真实代码路径重算。`55225c3` |
| 4.2 | **映射后重复基因 ID 从未合并(P7)。** 1,107 个人类 / 2,817 个小鼠 / 2,025 个海胆词表基因对应 ≥ 2 个源列 → 构建训练数据集时崩溃,或推理时静默跳过整个文件。 | **已解决** — 重复项按计数求和合并,并在准备报告中以 `duplicate_genes_collapsed` 字段记录。`55225c3` |
| 4.3 | **各物种映射覆盖率 47–82% 不等(S6)。** 覆盖率差异会制造虚假的跨物种分化:某基因若不在物种 A 的映射中,看起来就像"被沉默"。 | **已设计** — 仅使用 Ensembl Compara 一对一直系同源(confidence = 1);海胆覆盖不足时经 S. purpuratus 桥接;抽样 200 对与 OrthoDB/DIOPT 交叉核对;并设**覆盖率下限**:被比较基因 ≥ 60% 有一对一直系同源、且该物种对全基因组一对一集合 ≥ 5,000 个基因,否则结论降级为单物种发现。**直系同源表构建尚未开始。** |
| 4.4 | **基因词表命名空间。** 存在分词时查错物种嵌入的风险。 | **已解决(已验证)** — TF-Metazoa 的 12 个词表在物种间经验证互不重叠。 |

## 5. 训练流程正确性(非计算资源)

| # | 问题 | 状态 |
|---|---|---|
| 5.1 | **早停保存的是最终权重而非最佳权重(P4)。** | **已解决** — 验证集改善时快照最佳检查点。`7cb9a6c` |
| 5.2 | **续训默认开启且实现损坏(P5)。** 未保存优化器/scaler/步数/RNG 状态;崩溃后重跑会用全新 AdamW 状态覆盖好检查点。 | **已解决** — 周期性原子全状态检查点(保留最近 2 个);真正的续训恢复全部状态并跳过已完成的微批次。`7cb9a6c` |
| 5.3 | **无 epoch 级打乱(P6)。** 每个 epoch 以相同顺序重放相同细胞。 | **已解决** — `BalancedDataset.set_epoch()`。`7cb9a6c` |
| 5.4 | **检查点不完整(P2 训练侧)。** 输出目录没有 config.json/词表 → 训练完成的产物不是可评估的模型。 | **已解决** — `save_finetuned_checkpoint()` 原子性地组装完整检查点目录(config + 硬链接词表 + 空间词表 + 权重)。`7cb9a6c` |

## 6. 评估框架的有效性

| # | 问题 | 状态 |
|---|---|---|
| 6.1 | **带空间条件的检查点无法评估(P2 评估侧)。** 评估代码从不设置 `spatial_bin` 辅助词表 → strict load_state_dict 直接崩溃。 | **已解决** — 评估端镜像了空间辅助词表的设置。`7cb9a6c` |
| 6.2 | **空间与单细胞按 assay 字符串路由(P3)。** Stereo-seq 标为 "unknown" → 空间留出文件会静默污染单细胞指标。 | **已解决** — 改按准备报告中的清单 `dataset_type` 路由(assay 启发式仅作兜底并告警)。`7cb9a6c` |
| 6.3 | **拟时序指标既易爆显存又无生物学意义(P8)。** 稠密 n×n float64 kNN 图(10 万细胞约需 80 GB),且跨物种计算一条轨迹。 | **已解决** — 改为按组(物种 → 胚胎 ID 兜底)的稀疏 kNN 拟时序,阶段顺序显式给出。`7cb9a6c` |
| 6.4 | **"微调模型"可能静默默认为基座检查点(P9)** → 基座对基座的零差异比较。 | **已解决** — 评估 CLI 拒绝把基座当微调模型,输出默认写入运行的 output_dir。`7cb9a6c` |

## 7. 下游结论的统计与科学有效性

| # | 问题 | 状态 |
|---|---|---|
| 7.1 | **似然下降影响分缺少零模型(S1)。** 删除高表达基因会移除更多似然质量 → 排名由表达量/检出率主导,而非调控重要性。 | **已设计(已冻结)** — 按 物种 × 阶段 分层,构建表达量与 dropout 率匹配的 10×10 分位数网格置换零模型;经验 p 值 + z 分数;每层 BH FDR q = 0.05。实现待做(训练后分析)。 |
| 7.2 | **"已知必需基因排名靠前"的验证是循环论证(S1)。** 小鼠来源的知识、小鼠占 53% 的语料、被记住的共表达。 | **已设计(已冻结)** — 8 套外部证伪集(MGI/IMPC、CRISPRz、FlyBase、WormBase RNAi、Jin 2020 Perturb-seq、类原肠胚筛选、Replogle 阴性对照、海胆 GRN);判定规则:≥ 2 套**非小鼠**集合中 AUROC > 0.6 且 FDR < 0.05,且排名不被持家基因主导。仅靠小鼠永远不算证伪通过。 |
| 7.3 | **缺少基座模型对照组(S2)。** 所有头条分析都可以先在零样本基座模型上跑;微调的边际价值原本永远不会被度量。 | **已设计(已冻结)** — 基座基线 B1–B4 + 预注册改进标准(≥ 6/8 物种留出似然提升 ≥ 5%;阶段 kNN 纯度绝对提升 ≥ 5 点;探测物种退化 ≤ 2 点;AUROC 下降 ≤ 0.02)。若基座已满足头条结论,微调降级为稳健性检验。 |
| 7.4 | **灾难性遗忘无人监控(S3)。** 胚胎留出集上的提升度量的是域适应,而非探测评估所依赖的零样本能力保持。 | **已设计(阈值已冻结)** — 冻结的非胚胎参照集(CELLxGENE Census 人/小鼠成体组织 + 海绵/酵母/疟原虫金丝雀集,可选果蝇细胞图谱);每个检查点计算似然差值 + 线性 CKA;非回归门限(3% / CKA 0.90)+ 响应阶梯,最终以 LoRA 兜底。**参照集尚未下载/构建。** |
| 7.5 | **因果措辞风险。** 似然影响分是关联性指标。 | **已接受(附规则)** — 禁用:"基因 X 驱动/调控阶段 P"(除非有湿实验或外部筛选支持);允许:"在阶段 P 具有 top 级似然影响分(分箱零模型 z = …,FDR q = …)"。 |
| 7.6 | **第二层反事实验证范围。** 反事实生成是否要用真实扰动数据验证? | **已解决(纳入范围)** — 对照 Jin et al. 2020(35 个 ASD/ND 风险基因的宫内 Perturb-seq):模型预测的下游受影响基因与实测差异表达基因的重合度。用户 2026-09-09 批准。 |

## 8. 探测物种与 ESM2 嵌入

| # | 问题 | 状态 |
|---|---|---|
| 8.1 | **探测物种不在词表内。** 猕猴、猪、豚鼠、热带爪蟾、海鞘、文昌鱼均非 TF-Metazoa 词表物种 → 其基因没有可学习的 token 嵌入。 | **已设计** — 按 `preprocess/fasta_manifest_pep.json` 用 ESM2 蛋白嵌入构建 token;猪和热带爪蟾的嵌入可下载现成版本;**猕猴、海鞘、文昌鱼须用 `preprocess/protein_embedding.py` 本地生成**(尚未执行——本机内存受限,必须分块推理)。 |
| 8.2 | **探测物种的基因级跨物种陈述需要同一张一对一直系同源表**(见 4.3);嵌入级比较则不需要。 | **已设计** — 共用 §6 直系同源框架。 |

---

## 训练前待决事项

1. **TOME E8.5b**(1.2):保留或丢弃——来源至今仍无法证实。
2. **采样加权**(3.8):接受 `BalancedDataset` 现状,还是实现真正的自然加权。
3. **直系同源表构建**(4.3):BioMart/Compara 拉取并固定版本——任何跨物种结论之前必须排期。
4. **遗忘监控参照集**(7.4):批准并构建 Census 下载 + 金丝雀文件。
5. **果蝇逐细胞阶段指派**(2.1):从 Calderon 图谱导出逐细胞估计年龄,或接受窗口中点指派。
6. **ESM2 生成**(8.1):为猕猴/海鞘/文昌鱼运行 `preprocess/protein_embedding.py`(内存受限,需分块)。
7. **小鼠 E8–P0 时间序列**(1.11):明确记录排除,或仅纳入其 E8–E13.5 窗口。

*计算资源类问题(基因 ID 头显存、单轮训练时长、bf16、WSL 内存、A40 部署)有意不在本文范围内;见对抗性评审的 C 类发现与 ADR 0003 的计算部分。*

---
---

# Major Issues for the Multi-Species Embryogenesis Finetune

Aggregated register of every significant issue raised about this finetune — from the
adversarial review (`docs/agents/adversarial-review-2026-09-09.md`), the dataset audit
(`logs/dataset_audit/`), the remediation program (ADR 0003), and the validation design
(`docs/perturbation-and-baseline-design.md`). **Compute-resource issues (VRAM, epoch time,
GPU count, WSL RAM) are deliberately out of scope** — they are tracked separately in the
review's C-findings and the training-setup checklist.

Status key: **resolved** (fixed and verified, commit cited) · **designed** (fix specified and
agreed, implementation pending) · **open** (no agreed fix yet) · **accepted** (a limitation we
knowingly carry, with a mitigation).

---

## 1. Corpus composition and data integrity

| # | Issue | Status |
|---|---|---|
| 1.1 | **TOME ⊂ gastrulation atlas duplication (D1).** 8 TOME files (E6.75–E8.5a, 105,373 cells) were byte-identical duplicates of the 139k gastrulation atlas; TOME E6.5 was 78.4% duplicated with identical count vectors. Identical cells could have landed in train AND holdout. | **Resolved** — 9 files dropped, atlas kept; cross-file dedup check added to `validate_manifest.py` (hard-fail > 1,000 shared barcodes; currently clean across 106 same-species pairs). `c088eeb` |
| 1.2 | **TOME E8.5b provenance unverified.** Zero barcode overlap with the atlas and a different barcode namespace, but its origin could not be confirmed against the publication. | **Open** — kept in the manifest, flagged as a drop candidate in `logs/dataset_audit/composition.md`. Decision needed before training. |
| 1.3 | **Human CS6 fig3 ⊂ fig2 (D2).** 8,445 spots, 100% obs-name intersection; the three fig files are one embryo carrying three embryo_ids. | **Resolved** — fig3 dropped; fig1/fig2 share `embryo_id: human_cs6` with distinct section_ids. `c088eeb` |
| 1.4 | **Drosophila rebuilt raw had no usable metadata.** 547,805 cells with `cell_type = "unknown"` and a wrong assay constant (10x instead of sci-RNA-seq3). | **Resolved** — `cell_type` (51 categories, 0.55% unknown) + `predicted_doublet` joined from the annotated Science 2022 file at 100% obs-name match; assay corrected to sci-RNA-seq3 (GSE190147). `c088eeb` |
| 1.5 | **Fly `predicted_doublet` carries no information** — categorical with the single value "Singlet" in the annotated source. | **Accepted** — joined faithfully; no doublet filtering possible from this annotation. |
| 1.6 | **Mouse timecourse "empty" wells.** 4,188 cells labeled `embryo_id == "empty"` (empty plate wells) would have been treated as an embryo by per-embryo splitting. | **Resolved** — excluded at the source (59,136 → 54,948 cells, 188 real embryos), recorded in `uns["empty_well_exclusion"]`. `c088eeb` |
| 1.7 | **Non-integer / processed matrices.** Several source files shipped normalized or scaled values (CS9 spatial, rabbit atlas, Tyser CS7, fly continuum) instead of raw counts. | **Resolved** — raw layers rebuilt and re-validated on the full data vector; CS9 honestly found scaled and dropped; regenerated audit confirms every manifest dataset is integer-valued. |
| 1.8 | **Vertebrate blastula coverage is thin (S7).** 952 mouse cells total (67–464 per file); human blastula absent entirely from the corpus. | **Accepted** — irreducible data limitation of published atlases; blastula-phase claims must be mouse-only and flagged as low-n. |
| 1.9 | **Species identity errors.** The sea-urchin dataset is *Lytechinus variegatus*, not *S. purpuratus* as initially assumed; no explicit species field existed in the manifest. | **Resolved** — all 27 entries carry an explicit `species` field (validator-enforced format). `c088eeb` |
| 1.10 | **Stale audit artifacts.** report.json/summary.txt described the pre-remediation 37-entry corpus. | **Resolved** — regenerated against the 27-entry manifest (2,855,332 cells / 22 sc files + 412,374 spots / 5 spatial files). `85d43fc` |
| 1.11 | **Mouse E8–P0 prenatal time-lapse (Nature 2024) is on disk but entirely unused.** Found while reconciling the user's curated dataset map (`物种.xmind` / `胚胎期单细胞转录组物种与数据集.png`): `Nature_2024_prenatal_time_lapse` (45 timepoints, ~11.44M nuclei, E8 to birth) exists on disk but was never audited, never in the manifest, never mentioned in any plan doc — it is the largest dataset in the collection, ~3.5× the rest of the corpus combined. | **Open** — recommend documenting a deliberate exclusion: most stages are outside the embryogenesis scope (runs to birth), and inclusion would push mouse from 53% to ~90% of the corpus, worsening mouse bias. Optional: mine only its E8–E13.5 window for extra neurula/organogenesis data. Needs a user decision. |

## 2. Embryogenesis (stage → phase) mapping

| # | Issue | Status |
|---|---|---|
| 2.1 | **Fly sliding-window "inconsistency" (S4).** Overlapping 4 h sampling windows (hrs_06_10 vs hrs_08_12) assigned the same 8–10 h interval to two phases — looked like a mapping bug. | **Resolved as convention** — windows are assigned one phase **by midpoint** (germ-band ≈ 4–9 h → neurula); the rule is now explicit in `preprocess/stage_phase_mapping.md`. Phase-resolved *analyses* must deduplicate cells to a single phase via window midpoint — **implementation pending** (analysis layer). |
| 2.2 | **Worm 100–130 min bin misassigned.** Gastrulation begins at the 26–28-cell stage (~100 min), so the bin labeled blastula overlaps early gastrulation. | **Resolved** — moved to gastrula (user decision, recorded in `stage_phase_mapping.md` and the manifest). `fa5cf1b` |
| 2.3 | **Zebrafish 24 hpf misassigned.** 24 hpf is pharyngula onset, not organogenesis. | **Resolved** — moved to neurula (user decision, recorded). `fa5cf1b` |
| 2.4 | **Boundary calls were uncited.** Five boundary decisions rested on judgment, not literature. | **Resolved** — full citation table in `docs/perturbation-and-baseline-design.md` §5 (O'Rahilly & Müller, Downs & Davies, Kimmel, Hamburger & Hamilton, Sulston, Campos-Ortega & Hartenstein, Ton 2023, Massri 2021). |
| 2.5 | **Zebrafish "neurula" is a phylotypic-alignment convention.** Kimmel staging has no neurula period; 14–24 hpf = segmentation/pharyngula. Same for fly germ-band and worm comma → neurula in invertebrates, which have no true neurula. | **Accepted** — documented as convention, not fact; all cross-species claims must acknowledge the coarse phase vocabulary. |
| 2.6 | **Boundary robustness unverified.** Any single-bin boundary error shifts phase composition. | **Designed** — pre-registered sensitivity analysis: shift every boundary one bin each direction; acceptance = top-100 perturbation hits per stratum retain ≥ 80% membership. Runs post-training. |

## 3. Dataset splitting and holdout design

| # | Issue | Status |
|---|---|---|
| 3.1 | **Splits were per-file-constant, not per-embryo (D4).** Real per-embryo obs columns (189 mouse timecourse embryos, 7 human CS12–16 embryos) were never used; the ADR's "single-embryo datasets are train-only" rule had no implementing mechanism. | **Resolved** — two-pass per-(dataset, embryo) splitting with per-species stratification; every assignment recorded with its reason in `split_assignments.json`. `55225c3` |
| 3.2 | **Seed-42 split verified broken (P1).** Zebrafish landed entirely in validation (never trained, yet drove early stopping); the final holdout covered only 2 of 8 species. | **Resolved** — stratified by species + dataset_type; every species guaranteed ≥ 1 training embryo. `55225c3` |
| 3.3 | **Holdout representation gap (consequence of 3.1's fix).** Pooled single-embryo datasets (worm, rabbit, chicken, fly, zebrafish) are always train-only — holdout metrics come only from multi-embryo files (mouse timecourse, human CS12–16, spatial sections). | **Accepted** — per ADR 0002/0003; held-out metrics say nothing about within-species generalization for those five species. Cross-species claims must lean on the orthology/phase analyses and zero-shot probes. |
| 3.4 | **Cell-level leakage for single-embryo datasets.** Splitting cells within one embryo would leak embryonic state into holdout. | **Resolved** — rejected by design (ADR 0002); single-embryo/section datasets are train-only. |
| 3.5 | **Same-embryo spatial sections.** CS6 fig1/fig2 are sections of one embryo; splitting them apart would leak. | **Resolved** — shared embryo_id with distinct section_ids; per-section split keeps them together. `c088eeb` |
| 3.6 | **No phase holdout or species holdout.** Current design holds out *embryos*; it cannot measure generalization to an unseen phase or unseen species within the training set. | **Accepted** — unseen-species generalization is covered instead by the reserved zero-shot probe species (macaque, pig, guinea pig, Xenopus, ciona, amphioxus); phase holdout is meaningless for time-course data (phases are a continuum). |
| 3.7 | **Pseudoreplication (S5).** 3.39M cells ≈ n = 1–3 embryos per species × phase (human gastrula = 1 CS6 + 1 CS7 embryo; rabbit/chicken/fly/worm = 1 pooled file each). | **Designed** — all inference aggregated at embryo level; embryo n reported per species × phase in every results table; n = 1 strata are descriptive-only with no uncertainty claims and no causal language. Analysis-layer rule, enforced at reporting time. |
| 3.8 | **Sampling-weighting mismatch (from C8).** The plan claimed "natural sampling weighting" but `BalancedDataset` oversamples spatial ~2.4×, repeats small datasets, and its (stage, cell_type) caps decimate the fly's 547k cells into ≤ 11 groups. | **Open** — decide at training setup whether the implemented weighting is the intended one or needs a true natural-weighting mode. |

## 4. Gene identity, mapping coverage, and orthology

| # | Issue | Status |
|---|---|---|
| 4.1 | **Version-stripping mangled non-Ensembl IDs (D3).** Stripping at "." destroyed 8,693 worm sequence names (`2L52.1`) and 2,073 zebrafish paralog symbols (`acy3.1`); advertised 90% worm coverage was really ~47%. | **Resolved** — stripping restricted to Ensembl/FBgn/WBGene patterns; coverage recomputed through the real code path. `55225c3` |
| 4.2 | **Duplicate gene IDs after mapping never collapsed (P7).** 1,107 human / 2,817 mouse / 2,025 urchin vocab genes had ≥ 2 source columns → crash at dataset build or silent file skip. | **Resolved** — duplicates collapsed by summing counts, reported as `duplicate_genes_collapsed` in the preparation report. `55225c3` |
| 4.3 | **Mapping coverage varies 47–82% across species (S6).** Differential coverage manufactures false cross-species divergence: a gene absent from species A's mapping looks "silenced". | **Designed** — Ensembl Compara 1:1 orthologs only (confidence = 1), urchin bridge via S. purpuratus if Metazoa coverage is thin, 200-pair cross-check against OrthoDB/DIOPT, and a **coverage floor**: ≥ 60% of compared genes with 1:1 orthologs and ≥ 5,000 genome-wide 1:1 genes per pair, else the claim is downgraded to single-species. **Orthology table build not started.** |
| 4.4 | **Gene vocab namespaces.** Risk of wrong-species embedding lookups at tokenization. | **Resolved (verified)** — the 12 TF-Metazoa vocabs are empirically disjoint across species. |

## 5. Training-pipeline correctness (non-compute)

| # | Issue | Status |
|---|---|---|
| 5.1 | **Early stopping saved final weights, not best (P4).** | **Resolved** — best-checkpoint snapshot on validation improvement. `7cb9a6c` |
| 5.2 | **Resume was default-on and broken (P5).** No optimizer/scaler/step/RNG state saved; a crashed rerun could clobber a good checkpoint with fresh-AdamW weights. | **Resolved** — periodic atomic full-state checkpoints (keep last 2); true resume restores all state and skips completed micro-batches. `7cb9a6c` |
| 5.3 | **No epoch shuffling (P6).** Every epoch replayed identical cells in identical order. | **Resolved** — `BalancedDataset.set_epoch()`. `7cb9a6c` |
| 5.4 | **Checkpoints were incomplete (P2, training half).** No config.json/vocabs in the output dir → a finished run was not an evaluatable model. | **Resolved** — `save_finetuned_checkpoint()` assembles a complete checkpoint dir (config + hardlinked vocabs + spatial vocab + weights) atomically. `7cb9a6c` |

## 6. Evaluation-harness validity

| # | Issue | Status |
|---|---|---|
| 6.1 | **Spatial checkpoints were unevaluatable (P2, eval half).** Evaluate never set up the `spatial_bin` aux vocab → strict load_state_dict crash. | **Resolved** — evaluate mirrors the spatial aux setup. `7cb9a6c` |
| 6.2 | **Spatial vs single-cell routed by assay string (P3).** Stereo-seq labeled "unknown" → spatial holdout files silently contaminated single-cell metrics. | **Resolved** — routing by manifest `dataset_type` from the preparation report (assay-heuristic fallback with warning). `7cb9a6c` |
| 6.3 | **Pseudotime metric was OOM-prone and meaningless (P8).** Dense n×n float64 kNN graph (~80 GB at 100k cells), one trajectory computed across species. | **Resolved** — sparse kNN pseudotime per group (species → embryo_id fallback), explicit stage ordering. `7cb9a6c` |
| 6.4 | **"Finetuned" could silently default to the base checkpoint (P9)** → base-vs-base comparison with zero deltas. | **Resolved** — evaluate CLI rejects base-as-finetuned, defaults output to the run's output_dir. `7cb9a6c` |

## 7. Statistical and scientific validity of downstream claims

| # | Issue | Status |
|---|---|---|
| 7.1 | **No null model for likelihood-drop impact scores (S1).** Deleting a highly expressed gene removes more likelihood mass → rankings dominated by expression/detection rate, not regulatory importance. | **Designed (frozen)** — expression- and dropout-matched 10×10 quantile-bin permutation null per species × phase stratum, empirical p-values + z-scores, BH FDR q = 0.05 per stratum. Implementation pending (post-training analysis). |
| 7.2 | **"Known essentials rank high" validation is circular (S1).** Mouse-derived knowledge, mouse-heavy corpus (53%), memorized co-expression. | **Designed (frozen)** — 8 external falsification sets (MGI/IMPC, CRISPRz, FlyBase, WormBase RNAi, Jin 2020 Perturb-seq, gastruloid screens, Replogle negative control, urchin GRN); verdict rule: AUROC > 0.6, FDR < 0.05 in ≥ 2 **non-mouse** sets, and rankings not housekeeping-dominated. Mouse alone never counts. |
| 7.3 | **No base-model control arm (S2).** Every headline analysis can run on the zero-shot base model; the marginal value of finetuning was never going to be measured. | **Designed (frozen)** — base-model baselines B1–B4 with pre-registered improvement criteria (≥ 5% holdout likelihood in ≥ 6/8 species, ≥ 5-point phase-purity gain, ≤ 2-point probe degradation, ≤ 0.02 AUROC drop). If base already satisfies the claims, finetune is demoted to a robustness check. |
| 7.4 | **Catastrophic forgetting unmonitored (S3).** Embryo-holdout improvement measures domain adaptation, not retention of the zero-shot ability the probe evaluation depends on. | **Designed (frozen thresholds)** — frozen non-embryo reference set (CELLxGENE Census human/mouse adult + sponge/yeast/plasmodium canaries, optional Fly Cell Atlas), per-checkpoint likelihood delta + linear CKA, non-regression gate (3% / CKA 0.90) with a response ladder ending in the LoRA fallback. **Reference set not yet downloaded/built.** |
| 7.5 | **Causal language risk.** Likelihood impact is associational. | **Accepted with rule** — prohibited: "gene X drives/regulates phase P" without wet-lab/external-screen support; permitted: "top-ranked likelihood impact score (bin-null z = …, FDR q = …)". |
| 7.6 | **Tier-2 counterfactual validation scope.** Does counterfactual generation get validated against real perturbation data? | **Resolved (in scope)** — Jin et al. 2020 (35 ASD/ND risk genes, in-utero Perturb-seq): overlap of predicted downstream-affected genes with observed DE genes. User-approved 2026-09-09. |

## 8. Probe species and ESM2 embeddings

| # | Issue | Status |
|---|---|---|
| 8.1 | **Probe species are out-of-vocabulary.** Macaque, pig, guinea pig, Xenopus tropicalis, ciona, amphioxus are not TF-Metazoa vocab species → their genes have no learned token embeddings. | **Designed** — tokens built from ESM2 protein embeddings per `preprocess/fasta_manifest_pep.json`; pig and X. tropicalis embeddings are downloadable pre-generated; **macaque, ciona, amphioxus must be generated locally** via `preprocess/protein_embedding.py` (not yet done — generation on this host is memory-constrained and must use chunked inference). |
| 8.2 | **Gene-level cross-species statements for probes need the same 1:1 ortholog table** (4.3); embedding-level comparisons do not. | **Designed** — shares the §6 orthology framework. |

---

## Open items requiring a decision before training

1. **TOME E8.5b** (1.2): keep or drop — provenance unverifiable so far.
2. **Sampling weighting** (3.8): accept `BalancedDataset` behavior as-is or implement true natural weighting.
3. **Orthology table build** (4.3): BioMart/Compara pull, pinned release — schedule before any cross-species claim.
4. **Forgetting reference set** (7.4): approve and build the Census download + canary files.
5. **Fly per-cell phase assignment** (2.1): export per-cell estimated age from the Calderon atlas, or accept window-midpoint assignment.
6. **ESM2 generation** (8.1): run `preprocess/protein_embedding.py` for macaque/ciona/amphioxus (memory-capped).
7. **Mouse E8–P0 time-lapse** (1.11): document an explicit exclusion, or include only its E8–E13.5 window.

*Compute-resource issues (gene-ID head VRAM, epoch time, bf16, WSL memory, A40 setup) are intentionally excluded here; see the C-findings in the adversarial review and ADR 0003 §compute.*
