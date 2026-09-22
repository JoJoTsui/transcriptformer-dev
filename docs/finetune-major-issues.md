# 多物种胚胎发生微调的主要问题清单(中文版)

本文汇总本次微调的全部重大问题,来源包括:对抗性评审(`docs/agents/adversarial-review-2026-09-09.md`)、数据集审计(`logs/dataset_audit/`)、整改计划(ADR 0003)与验证设计文档(`docs/perturbation-and-baseline-design.md`)。本文自身亦经三方对抗性复核并据此修订(`docs/agents/register-review-2026-09-14.md`)。**计算资源类问题(显存、单轮训练时长、GPU 数量、WSL 内存)不在本文范围内**——它们单独记录于评审报告的 C 类发现与 ADR 0003 的计算部分。需要生物学合作方裁定的事项,另行汇总于文末《致合作者:待您裁定的事项》。

**工程进度:** 五项可独立推进的工程任务均已完成并分别推送;见 [执行跟踪](agents/finetune-readiness-tracker.md) 与 [工具用法](finetune-readiness-tools.md)。策略/QC/B1 决策、探测资源和完整 prepare 仍待完成。

**2026-09-22 续审(历史记录):** 复现证据见 [续审报告](agents/continuation-review-2026-09-22.md)。3.9 的常量 section_id 方案无效,状态重新打开;新增 3.11(覆盖 section_id 会改变空间分箱)与 7.7(B1 的六物种留出标准不可达)。这些是设计缺陷,尚未实施修复。

状态标记:**已解决**(已修复并验证,附提交号)· **已设计**(方案已确定,实现待做)· **待决**(尚无定论)· **已接受**(已知局限,附缓解措施)。

---

## 1. 语料库组成与数据完整性

| # | 问题 | 状态 |
|---|---|---|
| 1.1 | **TOME 与 gastrula(原肠胚期)图谱重复(D1)。** 8 个 TOME 文件(E6.75–E8.5a,共 105,373 个细胞)与 139k 细胞的 gastrula 图谱逐字节重复;TOME E6.5 也有 78.4% 重复,且计数向量完全一致。这意味着相同的细胞可能同时落入训练集和留出集(holdout)。 | **已解决** — 已丢弃 9 个文件并保留图谱;`validate_manifest.py` 新增跨文件去重检查:同一物种的文件间共享 barcode 超过 1,000 即硬性失败,当前 106 对比较全部通过。该检查的范围限制:每个文件仅抽样前 50,000 个 obs_names。`c088eeb` |
| 1.2 | **TOME E8.5b 来源之谜——已查明。** 该文件(154,313 个细胞)实为 Nature 2024 prenatal time-lapse(出生前时间序列)图谱(见 1.11)中 run_4(E8.0–E8.5)子集的再发布版本:同时去除 `run_N_` 前缀和末尾 `-<i>` 后缀后,barcode 匹配率达 99.54%(153,597/154,313),且抽样 120 个共享细胞的计数向量完全一致;它与 TOME 其余文件无关。 | **已解决(来源)** — 该文件目前保留在清单中:只要 1.11 的 prenatal 图谱保持排除状态,语料内就不存在重复。**但若纳入该图谱的任何部分,必须先丢弃 E8.5b**(D1 式重复)。716 个未匹配细胞(来自零散孔板)记录于验证脚本 `.scratch/verify_e85b_vs_prenatal.py` 与 ADR 0003。`59bf940` |
| 1.3 | **人 CS6 fig3 ⊂ fig2(D2)。** 8,445 个 spot 的 obs 名 100% 重合;三个 fig 文件本属同一胚胎,却携带三个不同的 embryo_id。 | **已解决** — 已丢弃 fig3;fig1/fig2 共用 `embryo_id: human_cs6`,并保留不同的 section_id。`c088eeb` |
| 1.4 | **果蝇重建的 raw 文件缺少可用元数据。** 547,805 个细胞的 `cell_type` 全为 "unknown",且 assay 常量标错(应为 sci-RNA-seq3 而非 10x)。 | **已解决** — 已从 Science 2022 注释文件按 obs 名 100% 匹配,并入 `cell_type`(51 类,仅 0.55% unknown)与 `predicted_doublet`;assay 已更正为 sci-RNA-seq3(GSE190147)。`c088eeb` |
| 1.5 | **果蝇 `predicted_doublet` 列无信息量。** 注释源中该列只有单一取值 "Singlet"。 | **已接受** — 已如实并入;该注释无法用于双联体(doublet)过滤。 |
| 1.6 | **小鼠时间序列中的"空孔"。** 4,188 个 `embryo_id == "empty"` 的细胞来自空板孔,但在按胚胎划分的逻辑下会被当作一个"胚胎"处理。 | **已解决** — 已在源头剔除(59,136 → 54,948 个细胞,188 个真实胚胎),并记录于 `uns["empty_well_exclusion"]`。`c088eeb` |
| 1.7 | **非整数/已处理矩阵。** 部分源文件提供的是归一化或缩放后的数值(CS9 scRNA、兔图谱、Tyser CS7、果蝇连续体),而非原始计数。 | **已解决** — raw 层已重建并完成全量校验。确属缩放并已剔除的文件是人 CS9 scRNA(2,150 个细胞,raw_counts=False);CS9 Stereo-seq 空间文件(96,837 个 spot)自始至终为整数值,仍保留在语料中。重新生成的审计确认清单内所有数据集均为整数值。 |
| 1.8 | **脊椎动物 blastula(囊胚期)覆盖单薄(S7)。** 小鼠合计仅 952 个细胞(每文件 67–464);人的 blastula 数据完全缺失。 | **已接受** — 这是已发表图谱的固有数据局限;blastula 相关结论只能限于小鼠,且须标注低样本量。 |
| 1.9 | **物种鉴定错误。** 海胆数据集实为 *Lytechinus variegatus*,而非最初假定的 *S. purpuratus*;清单此前也没有显式的物种字段。 | **已解决** — 全部 27 个条目均带显式 `species` 字段(校验器强制格式)。`c088eeb` |
| 1.10 | **审计产物过时。** report.json/summary.txt 描述的还是整改前 37 条目的语料。 | **已解决** — 已按 27 条目清单重新生成(2,855,332 个细胞 / 22 个单细胞文件 + 412,374 个 spot / 5 个空间文件)。`85d43fc` |
| 1.11 | **小鼠 E8–P0 prenatal time-lapse 图谱(Nature 2024)在库但完全未使用。** 与用户的物种数据集思维导图(物种.xmind / 胚胎期单细胞转录组物种与数据集.png)核对时发现:`Nature_2024_prenatal_time_lapse` 在磁盘上,却从未进入审计、清单或任何计划文档——它是整个收藏中最大的数据集。**2026-09-09 已补审计**(h5py 直接读取,脚本在 `.scratch/`):磁盘上为 4 个 CELLxGENE 随机分片(UUID 文件名,各约 34 GB、约 286 万 × 45,525 个 ENSMUSG 基因;`uns/title` = "Whole dataset: Normalized subset N";obs 名两两零重叠;var 逐字相同;每个分片都覆盖全部 43 个 `author_day` 分箱和全部 16 个测序 run)。**合计 11,441,407 个细胞核,与论文声明完全一致。** 观测对象为细胞核(sci-RNA-seq3,`suspension_type=nucleus`);74 个供体胚胎(`donor_id`);`author_day` 共 43 个分箱 E0800-E0850…P0000(论文宣称 45 个时间点),Theiler 12–27;`author_cell_type` 190 类 / `cell_type` 134 个 CL 术语;`X` 为 log 归一化值,整数原始计数在 `raw.X`/`layers["raw.X"]`;obsm 仅 `X_umap`。原审计失败的原因是:anndata 0.11 的 `read_h5ad(backed="r")` 会把 `layers["raw.X"]`(48.8 亿 nnz,仅 int64 indices 就需 36.4 GiB)整体物化,超出 26 GiB 内存上限。与训练语料的重叠情况:与其他 12 个小鼠文件 barcode 零重叠;**但 TOME E8.5b(154,313 个细胞)去掉 `run_N_` 前缀后,99.54% 的 barcode 落在本图谱 run_4(E8.0–E8.5)子集中,抽样 120 个共享细胞的计数向量完全一致**——E8.5b 实为该 Nature 2024 图谱的再发布切片,这同时解释了 1.2 的来源疑问。 | **待决** — 建议明确记录为排除:其大部分阶段超出胚胎发生范围(延伸至出生),且纳入会让小鼠占比从 53% 升至约 90%,加剧鼠偏倚。也可选择仅挖掘其 E8–E13.5 窗口,补充 neurula(神经胚期)/organogenesis(器官发生期)数据。**若任何部分被纳入,必须先丢弃 TOME E8.5b(D1 式重复)。** 需用户裁定。 |
| 1.12 | **空间坐标准备工具已实现,原始文件尚未激活。** fig1、CS8、CS9 的坐标来自标识字符串;fig2 用 X_spatial,CS7 用 newx/newy。工具同时保留真实切片身份,避免原先清单常量合并多个切片。 | **已修复(工具)** — `fee6970`: `scripts/prepare_spatial_coordinates.py` 默认只读审计;显式复制模式输出新 H5AD 与派生清单,不改原始文件。412,374 个 spot 的全量坐标/元数据副本往返验证通过;16 项测试通过。完整表达矩阵副本与正式 prepare 尚未执行(5.5)。 |
| 1.13 | **全库无双联体、线粒体或环境 RNA(ambient RNA)质控。** `_apply_qc` 仅支持 min/max 基因数与 counts(清单只设了 min_genes: 200);没有数据集带可用的双联体分数(1.5 的注释仅覆盖果蝇);`percent.mito` 虽存在于 fig1/CS9 的 obs 中但未被使用,也没有任何环境 RNA 处理。每个训练数据集都未经筛查即入库——双联体风险最高的 54.7 万细胞 sci-RNA-seq3 果蝇图谱被明确判为无法过滤。 | **待决** — 需裁定是否在训练前运行计算性双联体/质控筛查。 |
| 1.14 | **assay 词表 token 错标。** 模型的 assay 词表(assay_vocab.json,40 个键)含 `sci-RNA-seq` 但**不含** `sci-RNA-seq3`,而分词器会把缺失键映射为 "unknown"。因此果蝇的 547,805 个细胞(约占语料 17%)、全部 Stereo-seq spot 和孔板法小鼠时间序列静默共用同一个 "unknown" assay token——三个平台在模型输入中被混为一谈。(另:composition.md 声称 inDrop 不在 assay 词表内——这是错的,它是第 13 号键。) | **待决** — 训练前需裁定 assay 字符串归一化方案。 |
| 1.15 | **小鼠单胚胎时间序列 27% 的细胞无分期。** 54,948 个细胞中有 14,775 个 developmental_time 为 NaN。准备保留真实缺失值,采样审计单独报告 unknown。伪时序评估已在建图前排除缺分期行并报告数量,避免改变有分期细胞的得分。 | **训练纳入策略待决;评估已修复** |
| 1.16 | **spot ≠ 细胞。** 41.2 万个 Stereo-seq spot 属于多细胞测量,却以与单细胞相同的逐细胞 likelihood(似然)训练;只有评估路由(6.2)区分二者。需对训练和阶段层面结论加注分辨率/去卷积警告。 | **已接受** — 缓解措施待定;记录为警告。 |
| 1.17 | **人 gastrula 阶段的空间旗舰数据约 87% 为胚外组织。** fig1(41.2 万 spot 中的 228,028 个)中,PL.EXMC+CTB.Fusion+STB+CTB+MTB 合计 199,586 个(87.5%),均为 trophoblast(滋养层)/胎盘来源;fig2 有 51% 为连接蒂。除非在分析时按细胞类型过滤,人 gastrula 结果将由胚外组织主导。 | **已接受** — 分析层过滤规则;记录为组成警告。 |
| 1.18 | **第二个在库但未使用的数据集。** 小鼠 Nature2019 E4.5–E7.5 multi-omics(2,971 个细胞,GSE133725,原始计数,ENSMUSG)不在任何审计、清单或计划中;它可部分覆盖单薄的 blastula/gastrula 窗口(1.8)。 | **待决** — 需记录排除或纳入。 |
| 1.19 | **Tyser CS7 重建细胞数差异。** 重建文件为 1,170 个细胞,旧处理文件为 1,195 个;两个命名空间的 obs 名零重叠,25 个细胞的差异无法追溯;可能源于不同的源 QC 版本。 | **已接受** — 已记录。 |

## 2. 胚胎发生(分期 → 阶段)映射

| # | 问题 | 状态 |
|---|---|---|
| 2.1 | **果蝇滑动窗口"不一致"(S4)。** 相互重叠的 4 小时采样窗口(hrs_06_10 与 hrs_08_12)把同一段 8–10 小时间隔分到了两个阶段——看似映射错误。 | **已解决(作为约定)** — 每个窗口按**中点**归入唯一阶段(germ-band(胚带)延伸 ≈ 4–9 h → neurula(神经胚期));规则已写入 `preprocess/stage_phase_mapping.md`。但逐阶段*分析*必须按窗口中点把每个细胞去重到单一阶段——**实现待做**(分析层)。 |
| 2.2 | **线虫 100–130 分钟分箱误配。** 线虫 gastrulation(原肠胚形成)始于 26–28 细胞期(约受精后 100 分钟),原标为 blastula(囊胚期)的该分箱已覆盖早期 gastrulation。 | **已解决** — 已移至 gastrula(用户裁定,记录于 `stage_phase_mapping.md` 与清单)。`fa5cf1b` |
| 2.3 | **斑马鱼 24 hpf 误配。** 24 hpf 是 pharyngula(咽胚期)起点,而非 organogenesis(器官发生期)。 | **已解决** — 已移至 neurula(用户裁定,已记录)。`fa5cf1b` |
| 2.4 | **边界判定缺乏文献依据。** 五项边界判定此前仅凭经验。 | **已解决** — 完整引文表见 `docs/perturbation-and-baseline-design.md` §5(O'Rahilly & Müller、Downs & Davies、Kimmel、Hamburger & Hamilton、Sulston、Campos-Ortega & Hartenstein、Ton 2023、Massri 2021)。`1b0196d` |
| 2.5 | **斑马鱼 "neurula" 是系统型对齐约定。** Kimmel 分期本无 "neurula" 一词;14–24 hpf = segmentation(体节期)/pharyngula。果蝇 germ-band 与线虫 comma 期归入 neurula 同理——无脊椎动物没有真正的神经胚结构。 | **已接受** — 明确记录为约定而非事实;所有跨物种结论必须承认这一粗粒度阶段词表。 |
| 2.6 | **边界稳健性未验证。** 任何一个分箱边界的错误都会改变阶段构成。 | **已设计** — 预注册敏感性分析:每个边界向两侧各平移一个分箱,重跑核心指标。需注意:平移边界会重构分层本身,命中名单的成员资格会机械地随之改变——因此敏感性指标应以细胞层面分数的稳定性(与平移无关)为主要锚点,并以每个分层 top-100 扰动命中基因在两种平移下保持 ≥ 80% 重合作为次要校验。训练后执行。 |
| 2.7 | **物种 × 阶段矩阵的空洞(超出 1.8 的 blastula 单薄问题)。** 海胆无 neurula 分层(16 hpf gastrula → 18–24 hpf prism(棱柱幼体)→ organogenesis);鸡只有 gastrula/neurula;兔和人均无 blastula。任何"全部 8 个物种在阶段 P"的陈述都会随阶段静默改变物种构成。 | **已接受** — 每份跨物种报告必须附阶段构成表。 |
| 2.8 | **数值 native stage 未匹配 JSON 字符串键。** 小鼠时间序列浮点分期与海胆整数 hpf 原先绕过 stage_mapping,成为未映射标签。 | **已解决** — `649b702` 共用标签映射 helper,匹配数值的字符串键并保留 native_stage 和真实缺失值;准备/覆盖/采样共用。全库仅余已知14,775条缺分期小鼠观测,不擅自分期。 |

## 3. 数据集划分与留出设计

| # | 问题 | 状态 |
|---|---|---|
| 3.1 | **划分按文件常量而非按胚胎(D4)。** 真实的逐胚胎 obs 列(小鼠时间序列 189 个 embryo_id 值 = 188 个真实胚胎 + 1 个 "empty" 伪胚胎(1.6);人 CS12–16 共 7 个胚胎)从未被使用;ADR 中"单胚胎数据集仅入训练集"的规则也没有实现机制。 | **已解决** — 改为两遍式按(数据集 × 胚胎)划分,并按物种分层;每条划分连同原因记录于 `split_assignments.json`。`55225c3` |
| 3.2 | **seed-42 划分经实证损坏(P1)。** 斑马鱼整体落入验证集——从未参与训练,却驱动早停;最终留出集(holdout)仅覆盖 8 个物种中的 2 个。 | **已解决** — 按物种逐一分层;当前所有模态均按胚胎判定资格(2026-09-22 更新,见 3.9);保证每个物种至少有 1 个胚胎进入训练集。`55225c3` |
| 3.3 | **留出集代表性缺口。** 实际 27 文件、pre-QC 元数据投影仅 human/mouse 有 final_holdout;线虫、兔、鸡、果蝇、斑马鱼和海胆六物种无留出。空间数据全部只进训练集。 | **已接受(范围限制)** — `logs/dataset_audit/holdout_coverage.json` 明确列出物种×阶段×划分的观测数和独立胚胎数。不得对无留出物种宣称种内泛化;B1 标准另须修订(7.7)。 |
| 3.4 | **单胚胎数据集的细胞级泄漏(leakage)。** 在同一胚胎内按细胞划分,会把胚胎状态泄漏进留出集。 | **已解决** — 设计上已否决(ADR 0002);单胚胎/单切片数据集仅入训练集。 |
| 3.5 | **同一胚胎的空间切片。** CS6 fig1/fig2 是同一胚胎的切片;若分开划分会产生泄漏。 | **已解决** — 二者共用 embryo_id、保留不同 section_id;当前全局同胚胎划分保证它们落在同侧。`c088eeb` |
| 3.6 | **没有阶段留出,也没有物种留出。** 当前设计按*胚胎*留出,因此无法度量对未见阶段或训练集内未见物种的泛化。 | **已接受** — 未见物种泛化改由保留的零样本探测物种覆盖(猕猴、猪、豚鼠、热带爪蟾、海鞘、文昌鱼)。阶段留出也并非"无意义":在逐胚胎划分下,中段阶段留出会近乎泄漏(E8.4 训练细胞 ≈ E8.5 留出细胞),末段阶段留出度量的其实是发育时间外推;本设计接受这一盲区——**没有任何指标度量对未见阶段的泛化**。另注意探测物种的构造性警告:探测物种在词表之外,运行于训练中从未见过的 ESM2 构造 token 上,因此探测成败会把 ESM2 token 构造质量与模型泛化混为一谈——这与词表内物种留出是根本不同的度量工具。 |
| 3.7 | **伪重复(S5)。** 327 万细胞折算下来,每个物种 × 阶段组合仅 n = 1–3 个胚胎(人 gastrula(原肠胚期)= 3 个胚胎:1 个 CS6 + 2 个来自不同论文的不同 CS7 数据集——Tyser scRNA 1,170 个细胞 + CS7 Stereo-seq 空间 28,804 个 spot;兔/鸡/果蝇/线虫各为 1 个混合文件)。 | **已设计** — 所有推断在胚胎层面聚合;每张结果表报告每个物种 × 阶段组合的胚胎数 n;n = 1 的分层仅作描述性报告,不做不确定性声明、不用因果措辞。属分析层规则,在报告时强制执行。 |
| 3.8 | **采样加权决策仍待定;实际行为已量化。** BalancedDataset 在模态内均匀有放回抽样,单细胞先按 stage×cell_type 上限筛选,并无物种均衡机制。旧的“果蝇 ≤11 组”说法不再适用于已补注释并映射阶段的语料。 | **待决(策略);审计工具已完成** — `c447651`: 第一轮 pre-QC 投影 2,000,000 次抽样、1,069,876 个唯一观测、930,124 次重复;空间 600,504(30.0252%),果蝇 265,497。报告逐数据集/物种/阶段区分 QC、非训练集、cap 排除与重复。未改变策略;决定后须重跑。 |
| 3.9 | **CS8 同胚胎切片泄漏已修复。** 原常量 section_id 方案无效;当前代码直接按胚胎身份划分,原生切片 ID 保留用于分箱和评估。 | **已解决(代码+真实元数据)** — `3c57776`: 所有模态按 `(species, embryo_id)` 全局划分;任一单胚胎/train-only 文件把同胚胎的所有文件固定到训练集。回归覆盖 CS8 62 切片、跨文件同胚胎与缺失 ID。真实 27 文件的五个空间文件均为 train-only;仍需新 prepare 产物。 |
| 3.10 | **探测物种替代不了词表内物种留出。** 见 3.6 的构造性警告:词表外的 ESM2 构造 token 使探测评估成为另一种度量工具;词表内的未见物种泛化没有任何指标度量。 | **已接受** — 承认这一度量缺口(没有可匀出的词表内物种:语料中全部 8 个词表物种都是阶段覆盖所必需的)。 |
| 3.11 | **切片身份与划分资格已分离。** 强行覆盖 section_id 会合并坐标框架并改变模型输入;因此不再使用常量覆盖作为修复。 | **已解决** — `3c57776` 保留切片身份并按 embryo_id 划分;`fee6970` 的空间副本提取原生切片:CS6 fig1/fig2 各49、CS7 82、CS8 62、CS9 13。全量元数据往返验证通过。 |

## 4. 基因标识、映射覆盖率与直系同源

| # | 问题 | 状态 |
|---|---|---|
| 4.1 | **版本号剥离破坏了非 Ensembl 标识(D3)。** 按 "." 截断毁掉了 8,693 个线虫序列名(`2L52.1`)和 2,073 个斑马鱼旁系同源符号(`acy3.1`);声称的 90% 线虫覆盖率实际只有约 47%。 | **已解决** — 剥离仅限 Ensembl/FBgn/WBGene 模式;覆盖率已按真实代码路径重算。`55225c3` |
| 4.2 | **映射后的重复基因 ID 从未合并(P7)。** 1,107 个人类 / 2,817 个小鼠 / 2,025 个海胆词表基因对应 ≥ 2 个源列 → 构建训练数据集时崩溃,或推理时静默跳过整个文件。 | **已解决** — 重复项按计数求和合并,并在准备报告中以 `duplicate_genes_collapsed` 字段记录。`55225c3` |
| 4.3 | **各物种映射覆盖率曾为 47–82%(整改前数字,S6)。** 覆盖率差异会制造虚假的跨物种分化:某基因若不在物种 A 的映射中,看起来就像"被沉默"。整改后经真实代码路径由校验器实测为 52.7%(Tyser CS7)– 90.2%(线虫)——线虫从修复前的 47% 升至 90.2%。 | **已设计** — 仅使用 Ensembl Compara 一对一 ortholog(直系同源基因)(confidence = 1);海胆覆盖不足时经 S. purpuratus 桥接;抽样 200 对与 OrthoDB/DIOPT 交叉核对。并设**覆盖率下限**:被比较基因 ≥ 60% 有一对一 ortholog、且该物种对全基因组一对一集合 ≥ 5,000 个基因,否则结论降级为单物种发现。**ortholog 表构建尚未开始。** |
| 4.4 | **基因词表命名空间。** 存在分词时查错物种 embedding(嵌入)的风险。 | **已解决(已验证)** — TF-Metazoa 的 12 个词表在物种间经验证互不重叠。 |

## 5. 训练流程正确性(非计算资源)

| # | 问题 | 状态 |
|---|---|---|
| 5.1 | **早停保存的是最终权重而非最佳权重(P4)。** | **已解决** — 验证集改善时快照最佳 checkpoint(检查点)。`7cb9a6c` |
| 5.2 | **续训默认开启且实现损坏(P5)。** 未保存优化器/scaler/步数/RNG 状态;崩溃后重跑会用全新 AdamW 状态覆盖好 checkpoint。 | **已解决** — 周期性原子全状态 checkpoint(保留最近 2 个);真正的续训会恢复全部状态并跳过已完成的微批次。`7cb9a6c` |
| 5.3 | **无 epoch 级打乱(P6)。** 每个 epoch 以相同顺序重放相同细胞。 | **已解决** — 由 `BalancedDataset.set_epoch()` 实现。`7cb9a6c`;持久 worker 的传播也已修复并通过 5.7 回归。 |
| 5.4 | **checkpoint 不完整(P2 训练侧)。** 输出目录没有 config.json/词表 → 训练完成的产物不是可评估的模型。 | **已解决** — `save_finetuned_checkpoint()` 原子性地组装完整 checkpoint 目录(config + 硬链接词表 + 空间词表 + 权重)。`7cb9a6c` |
| 5.5 | **整改后真实语料仍需完整 prepare 验证。** 划分、坐标副本、元数据和阶段映射工具已验证,但未生成正式的完整表达矩阵副本与 27 数据集训练准备产物。 | **待执行 — 训练前闸门** — 先用坐标复制工具生成派生清单,完成待决语料/QC配置后重新运行校验器与 `--prepare-only`;源清单当前缺坐标会 FAIL。元数据审计/合成测试不替代完整语料运行。 |
| 5.6 | **checkpoint 硬链接的可移植性。** save_finetuned_checkpoint 对词表文件使用硬链接;不带 -H 的普通 rsync/cp 会将其复制为独立文件(磁盘膨胀而非损坏——_link_or_copy 会回退为复制)。A40 rsync 时注意。 | **已接受** — 运维备注。 |
| 5.7 | **persistent workers 未收到 epoch 更新。** 多进程回归证实旧实现的第二个 epoch 重放第一个 epoch。 | **已解决** — epoch 使用共享 CPU tensor; fork/spawn 持久 worker 与直接 sampler 一致,跨 epoch 恢复与连续运行的采样序列一致。不改变采样概率。 |
| 5.8 | **训练缺少准备产物完整性门禁。** 旧报告无法证明配置、来源、QC 后成员和划分一致。 | **已解决(代码/有限表达矩阵演练)** — 新报告记录来源行号、配置/资产指纹与文件哈希;训练加载模型/DDP 前校验成员完整性和胚胎隔离。真实两文件共 256 行演练保留 254 行;全库 prepare 仍待决策后执行。 |

## 6. 评估框架的有效性

| # | 问题 | 状态 |
|---|---|---|
| 6.1 | **带空间条件的 checkpoint(检查点)无法评估(P2 评估侧)。** 评估代码从不设置 `spatial_bin` 辅助词表 → strict load_state_dict 直接崩溃。 | **已解决** — 评估端镜像了空间辅助词表的设置。`7cb9a6c` |
| 6.2 | **空间与单细胞按 assay 字符串路由(P3)。** Stereo-seq 标为 "unknown" → 空间留出文件会静默污染单细胞指标。 | **已解决** — 改按准备报告中的清单 `dataset_type` 路由(assay 启发式仅作兜底并告警)。`7cb9a6c` |
| 6.3 | **pseudotime(拟时序)指标既易爆显存又无生物学意义(P8)。** 稠密 n×n float64 kNN 图(10 万细胞约需 80 GB),且跨物种计算一条轨迹。 | **已解决** — 改为按组(物种 → 胚胎 ID 兜底)的稀疏 kNN pseudotime,阶段顺序显式给出。`7cb9a6c` |
| 6.4 | **"微调模型"可能静默默认为基座 checkpoint(P9)** → 基座对基座的零差异比较。 | **已解决** — 评估 CLI 拒绝把基座当微调模型,输出默认写入运行的 output_dir。`7cb9a6c` |
| 6.5 | **pseudotime 按物种分组是死代码。** prepare.py 从不写入 `species` obs 列,评估总是回退到 embryo_id;当前留出集中大多数分组为单阶段 → Spearman = NaN,分组被静默丢弃——该指标退化为对少数多阶段分组取均值。 | **已修复(代码,2026-09-22)** — prepare 写入清单 species、native_stage 与 source_dataset;评估只要存在 species 列就优先按物种分组(包括单物种、多胚胎情况),并报告不可评估分组数与缺失分组标签的观测数。合成 H5AD 准备/划分及伪时序回归已通过;旧产物须重新 prepare,真实语料验证仍受 5.5 阻塞。 |
| 6.6 | **空间指标跨胚胎/切片混合建图。** spatial_neighborhood_consistency 与 Moran's I 在所有空间文件上混合构建一张 kNN 图——来自不同胚胎/切片但坐标相近的 spot 会成为假邻居(与 6.3 的逐组 pseudotime 修复不同)。 | **已修复(代码,2026-09-22)** — 两项指标按 source_dataset/species/embryo_id/section_id 中可用的复合身份逐切片建图;汇总为可评估切片的等权均值,并保留逐切片结果。缺失身份、无效坐标/嵌入、过小切片显式报告;使用行位置兼容重复 obs 名。空间/评估合成回归已通过;真实语料仍待 5.5 的准备运行。 |

## 7. 下游结论的统计与科学有效性

| # | 问题 | 状态 |
|---|---|---|
| 7.1 | **likelihood(似然)下降影响分缺少零模型(S1)。** 删除高表达基因会移除更多 likelihood 质量 → 排名由表达量/检出率主导,而非调控重要性。 | **已设计(已冻结)** — 按物种 × 阶段分层,构建表达量与 dropout 率匹配的 10×10 分位数网格置换零模型;经验 p 值 + z 分数;每层 BH FDR q = 0.05。实现待做(训练后分析)。 |
| 7.2 | **"已知必需基因排名靠前"的验证是循环论证(S1)。** 小鼠来源的知识、小鼠占 53% 的语料、被记住的共表达。 | **已设计(已冻结)** — 8 套外部证伪集(MGI/IMPC、CRISPRz、FlyBase、WormBase RNAi、Jin 2020 Perturb-seq、gastruloid(类原肠胚)筛选、Replogle 阴性对照、海胆 GRN)。判定规则:第 {2,3,4} 号集合(CRISPRz / FlyBase / WormBase)中 ≥ 2 套**非小鼠**集合 AUROC > 0.6 且 FDR < 0.05,且排名不被持家基因主导;仅靠小鼠永远不算证伪通过。母源 mRNA 警告:斑马鱼 F0 crispant(CRISPR 处理的 F0 代个体)因母源 mRNA 沉积掩盖早期作用基因,系统性低估早期阶段必需基因——早期阶段 AUROC 偏低属预期,必须如实报告。 |
| 7.3 | **缺少基座模型对照组(S2)。** 所有头条分析都可以先在零样本基座模型上跑;微调的边际价值原本永远不会被度量。 | **已设计;B1 待修订(见 7.7)** — 基座基线 B1–B4 + 预注册改进标准(≥ 6/8 物种留出 likelihood 提升 ≥ 5% 且无任一物种退化 > 2%(B1);阶段 kNN 纯度绝对提升 ≥ 5 点;探测物种退化 ≤ 2 点;AUROC 下降 ≤ 0.02)。若基座已满足头条结论,微调降级为稳健性检验。 |
| 7.4 | **灾难性遗忘无人监控(S3)。** 胚胎留出集上的提升度量的是域适应,而非探测评估所依赖的零样本能力保持。 | **已设计(阈值已冻结)** — 冻结的非胚胎参照集(CELLxGENE Census 人/小鼠成体组织 + 海绵/酵母金丝雀集(canary set),可选果蝇细胞图谱);每个 checkpoint 计算 likelihood 差值 + 线性 CKA;非回归门限(3% / CKA 0.90)+ 响应阶梯,最终以 LoRA 兜底。金丝雀集仅是总体表征崩溃的跳闸线(P. falciparum 虽在模型词表内但本地无数据集,不能作金丝雀——见设计文档 §4.1);与胚胎发生相关的遗忘监控是 B4 探测物种臂(见 7.3/B4)。**参照集尚未下载/构建。** |
| 7.5 | **因果措辞风险。** likelihood 影响分是关联性指标。 | **已接受(附规则)** — 禁用:"基因 X 驱动/调控阶段 P"(除非有湿实验或外部筛选支持);允许:"在阶段 P 具有 top 级 likelihood 影响分(分箱零模型 z = …,FDR q = …)"。 |
| 7.6 | **第二层反事实验证范围。** 反事实生成是否要用真实扰动数据验证? | **已解决(纳入范围)** — 对照 Jin et al. 2020(35 个 ASD/ND 风险基因的宫内 Perturb-seq):模型预测的下游受影响基因与实测差异表达基因的重合度。用户 2026-09-09 批准。 |
| 7.7 | **B1 六物种留出标准不可达。** 7.3 要求 ≥6/8 训练物种改善,实际投影只有 human/mouse 两物种有 final_holdout;不能由 B4 探测物种补足分母。 | **待决 — 训练前闸门** — `649b702` 的覆盖工具实测并明确输出 blocked,未修改标准。须在查看训练结果之前约定可评估物种范围/新标准,或补充独立胚胎;原阈值保留作历史记录。 |

## 8. 探测物种与 ESM2 嵌入

| # | 问题 | 状态 |
|---|---|---|
| 8.1 | **探测物种不在词表内。** 猕猴、猪、豚鼠、热带爪蟾、海鞘、文昌鱼均非 TF-Metazoa 词表物种 → 其基因没有可学习的 token embedding(嵌入)。 | **已设计** — 按 `preprocess/fasta_manifest_pep.json` 用 ESM2 蛋白 embedding 构建 token;猪和热带爪蟾的 embedding 可下载现成版本;**猕猴(食蟹猴 *M. fascicularis*)、豚鼠、海鞘、文昌鱼须用 `preprocess/protein_embedding.py` 本地生成**(尚未执行——本机内存受限,必须分块推理)。预生成 ESM2 embedding 仅有 *M. mulatta*(另一物种),食蟹猴 embedding 确需本地生成;且 fasta_manifest_pep.json 目前**没有**海鞘、文昌鱼、豚鼠、食蟹猴的条目——须先补条目才能运行 protein_embedding.py(豚鼠此前被静默漏出 embedding 计划,现已补回)。 |
| 8.2 | **探测物种的基因级跨物种陈述需要同一张一对一 ortholog(直系同源)表**(见 4.3);embedding 级比较则不需要。 | **已设计** — 共用 `docs/perturbation-and-baseline-design.md` §6 的 ortholog 框架(非本清单 §6)。 |
| 8.3 | **探测阶段映射已机器化并完成真实标签覆盖检查。** 原文档表已编码到 `preprocess/probe_stage_mappings.json`,按数据集区分 native stage。 | **已解决(映射/校验工具)** — `865bc5f`: 八文件/六物种所有观测阶段均有映射,无缺失或未知标签;12 项回归通过。`scripts/validate_probes.py` 明确列出仍缺的物种词表、四项 FASTA 条目及未确认元数据,因此探测执行仍 blocked。报告不验证基因覆盖或边界敏感性。 |

---

## 致合作者:待您裁定的事项

以下第1–5项需要各位(生物学与数据合作方)裁定;第6项记录已完成的工程工作。我们为每项给出背景、需要回答的问题、候选方案(标注我们的建议)以及各方案的后果;涉及的机器学习侧术语均随文简要说明。各事项相互独立,可按编号分别回复。

### 1. 小鼠 E8–P0 prenatal time-lapse 图谱的去留(对应 1.11、1.2)

**背景。** Nature 2024 的小鼠 prenatal time-lapse(出生前时间序列)图谱覆盖 E8 至出生,共 11,441,407 个细胞核(sci-RNA-seq3),是整个收藏中最大的数据集。它目前在磁盘上,从未进入训练语料。审计已确认:它与语料中其他 12 个小鼠文件无 barcode 重叠;但语料中的 TOME E8.5b 文件(154,313 个细胞)经核实正是该图谱 run_4(E8.0–E8.5)子集的再发布版本(barcode 匹配率 99.54%,计数向量一致)。

**问题。** 是否将这份图谱(或其一部分)纳入微调训练语料?

**选项。**

- **整体排除(我们的建议)。** 后果:语料维持现状。该图谱大部分阶段超出胚胎发生范围(延伸至出生);若整体纳入,小鼠数据占语料的比例将从 53% 升至约 90%,显著加剧本已存在的鼠偏倚,削弱跨物种结论的分量。
- **仅挖掘 E8–E13.5 窗口。** 后果:可补充 neurula(神经胚期)/organogenesis(器官发生期)阶段的小鼠数据;但纳入体量仍需严格控制,以免重演鼠偏倚。

**硬约束(无论选择哪项)。** 只要纳入该图谱的任何部分,就必须先从语料中丢弃 TOME E8.5b——否则同一批细胞会经由两个文件分别进入训练集与留出集(train/holdout split:一部分数据用于训练,另一部分严格保留用于评估),构成 leakage(泄漏),即 1.1 已处理过的 D1 类重复。

### 2. Nature2019 E4.5–E7.5 multi-omics 数据集是否纳入(对应 1.18)

**背景。** 磁盘上还有第二个从未使用的数据集:小鼠 Nature2019 E4.5–E7.5 multi-omics(多组学)数据,共 2,971 个细胞(GSE133725,原始计数,ENSMUSG 基因标识)。它覆盖的窗口恰好是语料目前最薄弱的一段:脊椎动物 blastula(囊胚期)/早期 gastrula(原肠胚期)覆盖单薄——小鼠合计仅 952 个 blastula 细胞,人的 blastula 数据完全缺失(见 1.8)。

**问题。** 是否将其纳入训练语料?

**选项。**

- **纳入,前提是其 QC 检查通过(我们的建议)。** 后果:脊椎动物 blastula 是整个语料最弱的分层,这份数据能直接补强该窗口;2,971 个细胞的体量也不会改变物种构成平衡。
- **记录为排除。** 后果:语料维持现状;blastula 相关结论继续限于小鼠低样本量声明(1.8 的既有警告不变)。

### 3. 采样加权策略(对应 3.8)

**背景。** 实际采样审计已完成(见 3.8):当前算法先按 stage×cell_type 对单细胞池限额,再按模态比例做均匀有放回抽样;它不会按物种均衡。第一轮 pre-QC 投影为 200 万次抽样,其中空间约30%、人38.04%、鼠34.26%、果蝇13.27%;这些比例取决于当前语料与限额,不是固定物种权重。93.0万次为重复抽样。最终 QC 后须重跑审计。

**问题。** 训练配置定稿时采用哪种加权?

**选项。**

- **维持 BalancedDataset。** 后果:保留当前模态混合、分层限额和有放回抽样;物种比例由语料组成决定,不保证物种均衡。请按审计报告评估是否适合研究问题。
- **改为自然加权。** 后果:与基座模型预训练的采样分布一致,实现更简单、无重复;代价是小鼠主导训练,鼠偏倚直接进入模型。

**希望各位提供意见的地方:** 从生物学问题出发——尤其是跨物种同阶段比较(例如各物种 gastrula 期的基因程序对比)——果蝇、线虫、海胆在训练中的代表性不足,是否会损害各位关心的结论?若会,需要另行设计物种加权,当前 BalancedDataset 没有此参数。

### 4. 双联体与质控筛查(对应 1.13、1.5、1.15)

**背景。** 三个相关的数据质量缺口:(a) 目前没有任何数据集带可用的双联体(doublet,一个液滴中混入两个细胞)注释——果蝇图谱自带的 `predicted_doublet` 列全为单一取值 "Singlet",无信息量;(b) 全库没有线粒体比例或环境 RNA(ambient RNA)过滤,每个训练数据集都未经筛查即入库;(c) 小鼠单胚胎时间序列中 27% 的细胞(14,775/54,948)缺乏 developmental_time 分期(NaN),目前带着字符串 "nan" 流入准备流程,未计入阶段构成。

**问题。** 各位从源论文出发,是否有我们应遵循的 QC 预期?

**希望获得的信息。**

- 源论文是否发表过 doublet 判定结果,可供我们按细胞名关联回来?
- 那 27% 无分期细胞,源论文是否因特定 QC 原因将其排除在分期之外?若有理由,我们应当照做。

**若无补充信息(我们的默认方案)。** 训练前运行计算性筛查(Scrublet 式 doublet 评分,即通过模拟双联体为每个细胞打分的算法);NaN 分期细胞保留在训练中(它们仍携带表达信息),但在按阶段解析的指标中一律排除。

### 5. Assay 词表归一化(对应 1.14)

**背景。** 模型输入中有一个 assay(测序平台)token(模型输入的最小单位,此处即平台类别标签),其词表(assay_vocab.json,共 40 个键)含 `sci-RNA-seq` 但不含 `sci-RNA-seq3`;分词器遇到词表外键时会静默映射为 "unknown"。结果:果蝇的 547,805 个细胞(约占语料 17%)、全部 Stereo-seq spot、以及孔板法小鼠时间序列,在模型输入中共用同一个 "unknown" assay token——三个本质不同的平台被混为一谈。

**问题。** 请协助确认每个数据集真实的平台归属:哪些是 10x 3' v3,哪些是 sci-RNA-seq3,哪些是 inDrop,哪些是 Stereo-seq?这些信息在源论文中均有明确记载,各位可以快速核实。

**后续(确认后执行)。** 我们据此归一化各数据集的 assay 标签,使词表内平台各归其 token;对词表确实不覆盖的平台,再决定是显式标注,还是保持 "unknown" 但至少保证不同平台不共享同一标签。

### 6. 空间工程任务完成记录(对应 1.12、3.9、3.11)

**已完成。** 胚胎级隔离已实现并在真实元数据上验证;坐标工具默认只读,显式复制模式生成新文件和派生清单,保留全部原始数据与真实切片标签。412,374 个 spot 的全元数据复制往返检查通过。原先的原地修改与常量切片覆盖方案已废止,不再请求对此旧方案签字。

**仍待执行。** 生成完整表达矩阵副本、确定最终语料/QC配置并运行正式 prepare。训练物种无空间留出;空间指标只能描述训练切片,独立探测评估仍受资源/元数据缺口阻塞。B1 标准另见 7.7。

**如何反馈。** 请按待决编号(1–5)逐项回复;若仅对个别事项有异议,只回复这些项即可。凡在 [留空给项目所有者填期限] 前未收到回复的事项,我们将按上文标注的**建议方案**作为默认执行。

*计算资源类问题(基因 ID 头显存、单轮训练时长、bf16、WSL 内存、A40 部署)有意不在本文范围内;见对抗性评审的 C 类发现与 ADR 0003 的计算部分。*

---
---

# Major Issues for the Multi-Species Embryogenesis Finetune

Aggregated register of every significant issue raised about this finetune — from the adversarial review (`docs/agents/adversarial-review-2026-09-09.md`), the dataset audit (`logs/dataset_audit/`), the remediation program (ADR 0003), and the validation design (`docs/perturbation-and-baseline-design.md`). This register itself passed a three-way adversarial re-review (`docs/agents/register-review-2026-09-14.md`). **Compute-resource issues (VRAM, epoch time, GPU count, WSL RAM) are deliberately out of scope** — they are tracked separately in the review's C-findings and ADR 0003's compute section. Items that need a ruling from our biology collaborators are collected at the end, in *For our collaborators: decisions we need from you*.

**Engineering status:** All five independent readiness tasks are completed and pushed separately; see the [tracker](agents/finetune-readiness-tracker.md) and [tool guide](finetune-readiness-tools.md). Policy/QC/B1 decisions, probe assets, and full preparation remain pending.

**2026-09-22 continuation (historical):** Reproduction evidence is in the [continuation review](agents/continuation-review-2026-09-22.md). Item 3.9 is reopened because the constant-section remedy is ineffective; new items 3.11 and 7.7 cover altered spatial binning and the unachievable six-species B1 gate. These are design findings; implementation fixes have not been applied.

Status key: **resolved** (fixed and verified, commit cited) · **designed** (fix specified and agreed, implementation pending) · **open** (no agreed fix yet) · **accepted** (a limitation we knowingly carry, with a mitigation).

---

## 1. Corpus composition and data integrity

| # | Issue | Status |
|---|---|---|
| 1.1 | **TOME ⊂ gastrulation atlas duplication (D1).** 8 TOME files (E6.75–E8.5a, 105,373 cells) were byte-identical duplicates of the 139k gastrulation atlas, and TOME E6.5 was 78.4% duplicated with identical count vectors. Identical cells could have landed in both train and holdout. | **Resolved** — 9 files were dropped and the atlas kept. `validate_manifest.py` gained a cross-file dedup check that hard-fails when two same-species files share more than 1,000 barcodes; all 106 current pairs pass. Scope limit: the check samples only the first 50,000 obs_names per file. `c088eeb` |
| 1.2 | **TOME E8.5b provenance mystery — solved.** The file (154,313 cells) is a republished slice of the Nature 2024 prenatal time-lapse atlas (see 1.11): its `run_4` (E8.0–E8.5) subset. After stripping both the `run_N_` prefix and the trailing `-<i>` suffix, 99.54% of barcodes match (153,597/154,313), with identical count vectors in 120/120 sampled shared cells; it is unrelated to the rest of TOME. | **Resolved (provenance)** — kept in the manifest: no in-corpus duplication exists as long as the prenatal atlas stays excluded (1.11). **If any part of that atlas is ever included, E8.5b must be dropped first** (D1-style duplication). The 716 unmatched cells (scattered plates) are recorded in the verification script `.scratch/verify_e85b_vs_prenatal.py` and ADR 0003. `59bf940` |
| 1.3 | **Human CS6 fig3 ⊂ fig2 (D2).** 8,445 spots with 100% obs-name intersection; the three fig files are one embryo carrying three embryo_ids. | **Resolved** — fig3 dropped; fig1/fig2 now share `embryo_id: human_cs6` while keeping distinct section_ids. `c088eeb` |
| 1.4 | **The rebuilt Drosophila raw file had no usable metadata.** All 547,805 cells carried `cell_type = "unknown"`, and the assay constant was wrong (10x instead of sci-RNA-seq3). | **Resolved** — `cell_type` (51 categories, 0.55% unknown) and `predicted_doublet` were joined from the annotated Science 2022 file at 100% obs-name match, and the assay was corrected to sci-RNA-seq3 (GSE190147). `c088eeb` |
| 1.5 | **The fly `predicted_doublet` column carries no information** — it holds the single value "Singlet" in the annotated source. | **Accepted** — joined faithfully; this annotation cannot support doublet filtering. |
| 1.6 | **Mouse timecourse "empty" wells.** 4,188 cells labeled `embryo_id == "empty"` (empty plate wells) would have been treated as one "embryo" by per-embryo splitting. | **Resolved** — excluded at the source (59,136 → 54,948 cells, 188 real embryos) and recorded in `uns["empty_well_exclusion"]`. `c088eeb` |
| 1.7 | **Non-integer / processed matrices.** Several source files shipped normalized or scaled values (CS9 scRNA, rabbit atlas, Tyser CS7, fly continuum) instead of raw counts. | **Resolved** — raw layers were rebuilt and re-validated on the full data vector. The file confirmed as scaled, and dropped, was the human CS9 scRNA (2,150 cells, raw_counts=False). The CS9 Stereo-seq spatial file (96,837 spots) was always integer-valued and remains in the corpus. The regenerated audit confirms every manifest dataset is integer-valued. |
| 1.8 | **Vertebrate blastula coverage is thin (S7).** Mouse contributes only 952 cells in total (67–464 per file), and human blastula is absent from the corpus entirely. | **Accepted** — an irreducible limitation of the published atlases; blastula-phase claims must be mouse-only and flagged as low-n. |
| 1.9 | **Species-identity errors.** The sea-urchin dataset is *Lytechinus variegatus*, not *S. purpuratus* as initially assumed, and the manifest previously had no explicit species field. | **Resolved** — all 27 entries carry an explicit `species` field (validator-enforced format). `c088eeb` |
| 1.10 | **Stale audit artifacts.** report.json/summary.txt still described the pre-remediation 37-entry corpus. | **Resolved** — regenerated against the 27-entry manifest (2,855,332 cells across 22 single-cell files + 412,374 spots across 5 spatial files). `85d43fc` |
| 1.11 | **The mouse E8–P0 prenatal time-lapse atlas (Nature 2024) is on disk but entirely unused.** It surfaced while reconciling the user's curated dataset map (`物种.xmind` / `胚胎期单细胞转录组物种与数据集.png`): `Nature_2024_prenatal_time_lapse` exists on disk yet was never audited, never entered the manifest, and was never mentioned in any plan document — and it is the largest dataset in the collection. **Audited 2026-09-09** (direct h5py reads; scripts in `.scratch/`): on disk it is 4 random CELLxGENE shards (UUID filenames, ~34 GB and ~2.86M cells × 45,525 ENSMUSG genes each; `uns/title` = "Whole dataset: Normalized subset N"; obs_names pairwise disjoint; var byte-identical; every shard spans all 43 `author_day` bins and all 16 sequencing runs). **The shards total 11,441,407 nuclei, exactly the published count.** The observations are nuclei, not cells (sci-RNA-seq3, `suspension_type=nucleus`); 74 donor embryos (`donor_id`); 43 `author_day` bins E0800-E0850…P0000 (the paper advertises 45 timepoints), Theiler stages 12–27; `author_cell_type` (190 categories) / `cell_type` (134 CL terms); `X` is log-normalized, with integer raw counts in `raw.X`/`layers["raw.X"]`; obsm holds `X_umap` only. The original audit failed because anndata 0.11 `read_h5ad(backed="r")` eagerly materializes `layers["raw.X"]` (4.88B nnz; the int64 indices alone need 36.4 GiB) and blew the 26 GiB memory cap. Overlap with the training corpus: zero barcode overlap with the other 12 mouse files, **but TOME E8.5b (154,313 cells) matches this atlas's run_4 (E8.0–E8.5) subset at 99.54% of barcodes after stripping the `run_N_` prefix, with identical count vectors in 120/120 sampled shared cells** — E8.5b is a republished slice of this Nature 2024 atlas, which also answers the provenance question in 1.2. | **Open** — we recommend documenting a deliberate exclusion: most of its stages are outside the embryogenesis scope (it runs to birth), and inclusion would push mouse from 53% to ~90% of the corpus, worsening mouse bias. An alternative is to mine only the E8–E13.5 window for extra neurula/organogenesis data. **If any part is included, TOME E8.5b must be dropped first (D1-style duplication).** Needs a user decision. |
| 1.12 | **Coordinate preparation is implemented; source files remain unactivated.** fig1/CS8/CS9 coordinates come from identifiers, fig2 from X_spatial, and CS7 from newx/newy. Copies also preserve native section identities instead of pooling sections through manifest constants. | **Fixed (tooling)** — `fee6970`: `scripts/prepare_spatial_coordinates.py` defaults to read-only auditing; explicit copy mode writes new H5ADs and a derived manifest without changing originals. All 412,374 coordinate rows passed full metadata-copy round-trips; 16 tests pass. Full expression copies and final preparation remain pending (5.5). |
| 1.13 | **No doublet, mitochondrial, or ambient-RNA QC anywhere.** `_apply_qc` supports only min/max genes and counts (the manifest sets only min_genes: 200); no dataset has usable doublet scores (1.5's is fly-only); `percent.mito` exists in fig1/CS9 obs but is unused; and there is no ambient-RNA handling. Every training dataset enters unscreened — the 547k-cell sci-RNA-seq3 fly atlas, the highest doublet risk, is explicitly unfilterable. | **Open** — decide whether to run a computational doublet/QC screen before training. |
| 1.14 | **Assay-vocab token mislabeling.** The model assay vocab (assay_vocab.json, 40 keys) contains `sci-RNA-seq` but NOT `sci-RNA-seq3`, and the tokenizer maps missing keys to "unknown". The fly's 547,805 cells (~17% of the corpus), all Stereo-seq spots, and the plate-based mouse timecourse therefore silently share ONE "unknown" assay token — three platforms conflated in the model input. (Also: composition.md claims inDrop is absent from the assay vocab — wrong; it is key 13.) | **Open** — decide assay-string normalization before training. |
| 1.15 | **27% of the mouse single-embryo timecourse has no stage.** 14,775 of 54,948 cells have NaN developmental_time. Preparation preserves nulls and sampling audits report unknown stages. Pseudotime now excludes missing-stage rows before graph construction and reports their counts, preventing score distortion. | **Training inclusion remains open; evaluation fixed** |
| 1.16 | **Spots are not cells.** The 412k Stereo-seq spots are multi-cell measurements but are trained with the same per-cell likelihood as single cells; only the evaluation routing (6.2) separates the two. This is a resolution/deconvolution caveat for training and for phase-level claims. | **Accepted** — mitigation pending; recorded as a caveat. |
| 1.17 | **The human gastrula spatial flagship is ~87% extraembryonic.** In fig1 (228,028 of 412k spots), PL.EXMC+CTB.Fusion+STB+CTB+MTB total 199,586 (87.5%) and are trophoblast/placental; fig2 is 51% connecting stalk. Unless cell-type-filtered at analysis, human gastrula-phase results will be dominated by extraembryonic tissue. | **Accepted** — analysis-layer filtering rule; recorded as a composition caveat. |
| 1.18 | **Second unused on-disk dataset.** The mouse Nature2019 E4.5–E7.5 multi-omics dataset (2,971 cells, GSE133725, raw counts, ENSMUSG) appears in no audit, manifest, or plan; it partially covers the thin blastula/gastrula window (1.8). | **Open** — document an exclusion or include it. |
| 1.19 | **Tyser CS7 rebuild count discrepancy.** The rebuilt file has 1,170 cells versus 1,195 in the old processed file; obs-name overlap between the two namespaces is zero, so the 25-cell difference is untraceable; the likely cause is a different source QC version. | **Accepted** — noted. |

## 2. Embryogenesis (stage → phase) mapping

| # | Issue | Status |
|---|---|---|
| 2.1 | **Fly sliding-window "inconsistency" (S4).** Overlapping 4 h sampling windows (hrs_06_10 vs hrs_08_12) assigned the same 8–10 h interval to two phases, which looked like a mapping bug. | **Resolved as convention** — each window is assigned one phase **by midpoint** (germ-band ≈ 4–9 h → neurula); the rule is now explicit in `preprocess/stage_phase_mapping.md`. Phase-resolved *analyses* must still deduplicate cells to a single phase via window midpoint — **implementation pending** (analysis layer). |
| 2.2 | **Worm 100–130 min bin misassigned.** Gastrulation begins at the 26–28-cell stage (~100 min), so the bin labeled blastula already overlaps early gastrulation. | **Resolved** — moved to gastrula (user decision, recorded in `stage_phase_mapping.md` and the manifest). `fa5cf1b` |
| 2.3 | **Zebrafish 24 hpf misassigned.** 24 hpf is pharyngula onset, not organogenesis. | **Resolved** — moved to neurula (user decision, recorded). `fa5cf1b` |
| 2.4 | **Boundary calls were uncited.** Five boundary decisions rested on judgment rather than literature. | **Resolved** — full citation table in `docs/perturbation-and-baseline-design.md` §5 (O'Rahilly & Müller, Downs & Davies, Kimmel, Hamburger & Hamilton, Sulston, Campos-Ortega & Hartenstein, Ton 2023, Massri 2021). `1b0196d` |
| 2.5 | **Zebrafish "neurula" is a phylotypic-alignment convention.** Kimmel staging has no neurula period; 14–24 hpf = segmentation/pharyngula. The same applies to fly germ-band and worm comma → neurula: invertebrates have no true neurula. | **Accepted** — documented as convention, not fact; all cross-species claims must acknowledge the coarse phase vocabulary. |
| 2.6 | **Boundary robustness is unverified.** Any single-bin boundary error shifts phase composition. | **Designed** — pre-registered sensitivity analysis: shift every boundary one bin in each direction and rerun the core metrics. Caveat: shifting a boundary recomposes the strata themselves, so hit-list membership changes mechanically — the sensitivity metric should anchor primarily on the stability of cell-level scores (which is shift-invariant), with top-100 per-stratum perturbation-hit retention ≥ 80% under both shifts as the secondary check. Runs post-training. |
| 2.7 | **Species × phase matrix holes beyond the blastula thinness (1.8).** Sea urchin has no neurula stratum (16 hpf gastrula → 18–24 hpf prism → organogenesis); chicken has gastrula/neurula only; rabbit and human have no blastula. Any "all-8-species at phase P" claim silently changes species composition across phases. | **Accepted** — a phase-composition table is required in every cross-species report. |
| 2.8 | **Numeric native stages missed string JSON mapping keys.** Mouse timecourse floats and sea-urchin integer hpf previously bypassed stage_mapping. | **Resolved** — `649b702` shares numeric-to-string-key lookup across preparation, coverage, and sampling while preserving native stages and actual nulls. Only the known 14,775 unstaged mouse observations remain unmapped in the corpus projection; no phase is invented. |

## 3. Dataset splitting and holdout design

| # | Issue | Status |
|---|---|---|
| 3.1 | **Splits were per-file-constant, not per-embryo (D4).** The real per-embryo obs columns (189 mouse timecourse embryo_id values = 188 real embryos + 1 "empty" pseudo-embryo (1.6); 7 human CS12–16 embryos) were never used, and the ADR's "single-embryo datasets are train-only" rule had no implementing mechanism. | **Resolved** — two-pass per-(dataset, embryo) splitting with per-species stratification; every assignment is recorded with its reason in `split_assignments.json`. `55225c3` |
| 3.2 | **The seed-42 split was empirically broken (P1).** Zebrafish landed entirely in validation — never trained on, yet driving early stopping — and the final holdout covered only 2 of 8 species. | **Resolved** — stratified per species; all modalities now use embryo-level eligibility (2026-09-22 update, see 3.9); every species is guaranteed ≥ 1 training embryo. `55225c3` |
| 3.3 | **Holdout representation gap.** The actual pre-QC 27-file projection has final holdout only for human/mouse; worm, rabbit, chicken, fly, zebrafish, and sea urchin have none. All spatial files are train-only. | **Accepted (claim limitation)** — `logs/dataset_audit/holdout_coverage.json` lists observation and unique embryo counts by species × phase × split. No within-species generalization claim is supported for species without holdout; B1 still requires revision (7.7). |
| 3.4 | **Cell-level leakage for single-embryo datasets.** Splitting cells within one embryo would leak embryonic state into the holdout. | **Resolved** — rejected by design (ADR 0002); single-embryo/single-section datasets are train-only. |
| 3.5 | **Same-embryo spatial sections.** CS6 fig1/fig2 are sections of one embryo; splitting them apart would leak. | **Resolved** — they share an embryo_id with distinct section_ids, and global same-embryo assignment now keeps them on the same side. `c088eeb` |
| 3.6 | **No phase holdout and no species holdout.** The current design holds out *embryos*; it can measure neither generalization to an unseen phase nor to an unseen species within the training set. | **Accepted** — unseen-species generalization is covered instead by the reserved zero-shot probe species (macaque, pig, guinea pig, Xenopus tropicalis, ciona, amphioxus). Phase holdout is not "meaningless" either: under per-embryo splits a mid-course phase holdout would be near-leaky (E8.4 train cells ≈ E8.5 holdout cells), and a terminal-phase holdout would measure developmental-time extrapolation; the design accepts the blind spot that NOTHING measures unseen-phase generalization. Note also the probe-construct caveat: probe species are out-of-vocab and run on ESM2-constructed tokens never seen in training, so probe success/failure conflates ESM2 token-construction quality with model generalization — a fundamentally different instrument from an in-vocab species holdout. |
| 3.7 | **Pseudoreplication (S5).** 3.27M cells boil down to n = 1–3 embryos per species × phase (human gastrula = 3 embryos: 1 CS6 + 2 distinct CS7 datasets from different publications — Tyser scRNA 1,170 cells + CS7 Stereo-seq spatial 28,804 spots; rabbit/chicken/fly/worm = 1 pooled file each). | **Designed** — all inference is aggregated at embryo level; every results table reports embryo n per species × phase; n = 1 strata are descriptive-only, with no uncertainty claims and no causal language. An analysis-layer rule, enforced at reporting time. |
| 3.8 | **Sampling policy remains undecided; actual behavior is now measured.** BalancedDataset samples uniformly with replacement within modality, after a stage × cell_type single-cell cap; it has no species-balancing mechanism. The old fly “≤11 groups” claim no longer describes the annotated, phase-mapped corpus. | **Open (policy); audit implemented** — `c447651`: pre-QC epoch 1 projects 2,000,000 draws, 1,069,876 unique rows, and 930,124 repeats; spatial draws 600,504 (30.0252%), fly 265,497. Per-dataset/species/phase reports distinguish QC, split, cap exclusions and repeats. No policy change; regenerate after decisions. |
| 3.9 | **CS8 same-embryo leakage is fixed.** The ineffective constant-section proposal is replaced by direct embryo-level assignment while native section IDs remain available for binning and evaluation. | **Resolved (code + real metadata)** — `3c57776`: every modality splits globally by `(species, embryo_id)`; any singleton/train-only occurrence pins all files of that embryo to training. Regressions cover 62-section CS8, shared embryos, and missing IDs. All five spatial files are train-only in the actual 27-file metadata check; fresh prepared outputs remain required. |
| 3.10 | **Probes are not a substitute for an in-vocab species holdout.** See 3.6's caveat: out-of-vocab ESM2-constructed tokens make probe evaluation a different instrument; unseen-species generalization within the vocab is measured by nothing. | **Accepted** — acknowledged measurement gap (no in-vocab species can be spared: all 8 vocab species in the corpus are needed for phase coverage). |
| 3.11 | **Section identity and split eligibility are separated.** Overwriting section_id pools coordinate frames and changes inputs, so constant overrides are no longer the remedy. | **Resolved** — `3c57776` preserves sections while splitting by embryo_id; `fee6970` copies recover native sections: 49 each for CS6 fig1/fig2, 82 CS7, 62 CS8, 13 CS9. Full metadata round-trips pass. |

## 4. Gene identity, mapping coverage, and orthology

| # | Issue | Status |
|---|---|---|
| 4.1 | **Version-stripping mangled non-Ensembl IDs (D3).** Stripping at "." destroyed 8,693 worm sequence names (`2L52.1`) and 2,073 zebrafish paralog symbols (`acy3.1`); the advertised 90% worm coverage was really ~47%. | **Resolved** — stripping restricted to Ensembl/FBgn/WBGene patterns; coverage recomputed through the real code path. `55225c3` |
| 4.2 | **Duplicate gene IDs after mapping were never collapsed (P7).** 1,107 human / 2,817 mouse / 2,025 urchin vocab genes had ≥ 2 source columns → crash at dataset build, or the whole file silently skipped at inference. | **Resolved** — duplicates collapsed by summing counts, reported as `duplicate_genes_collapsed` in the preparation report. `55225c3` |
| 4.3 | **Mapping coverage ranged 47–82% across species pre-fix (S6).** Differential coverage manufactures false cross-species divergence: a gene absent from species A's mapping looks "silenced". Post-fix, the validator-measured range through the real code path is 52.7% (Tyser CS7) – 90.2% (worm) — worm rose from 47% pre-fix to 90.2%. | **Designed** — Ensembl Compara 1:1 orthologs only (confidence = 1), urchin bridged via S. purpuratus if coverage is thin, a 200-pair spot cross-check against OrthoDB/DIOPT, and a **coverage floor**: ≥ 60% of compared genes with 1:1 orthologs and ≥ 5,000 genome-wide 1:1 genes per species pair, else the claim is downgraded to single-species. **Orthology table build not started.** |
| 4.4 | **Gene-vocab namespaces.** There was a risk of wrong-species embedding lookups at tokenization. | **Resolved (verified)** — the 12 TF-Metazoa vocabs are empirically disjoint across species. |

## 5. Training-pipeline correctness (non-compute)

| # | Issue | Status |
|---|---|---|
| 5.1 | **Early stopping saved final weights, not best (P4).** | **Resolved** — best-checkpoint snapshot on validation improvement. `7cb9a6c` |
| 5.2 | **Resume was default-on and broken (P5).** No optimizer/scaler/step/RNG state was saved; a crashed rerun could clobber a good checkpoint with fresh-AdamW weights. | **Resolved** — periodic atomic full-state checkpoints (keep last 2); a true resume restores all state and skips completed micro-batches. `7cb9a6c` |
| 5.3 | **No epoch shuffling (P6).** Every epoch replayed identical cells in identical order. | **Resolved** — via `BalancedDataset.set_epoch()`. `7cb9a6c`; persistent-worker propagation is also fixed and tested under 5.7. |
| 5.4 | **Checkpoints were incomplete (P2, training half).** No config.json/vocabs in the output dir → a finished run was not an evaluatable model. | **Resolved** — `save_finetuned_checkpoint()` assembles a complete checkpoint dir (config + hardlinked vocabs + spatial vocab + weights) atomically. `7cb9a6c` |
| 5.5 | **The remediated real corpus still needs a full prepare validation.** Splits, coordinate-copy tooling, metadata, and phase mapping have been checked, but full expression copies and final 27-dataset prepared outputs have not been generated. | **Pending — pre-training gate** — generate coordinate copies and a derived manifest, finalize corpus/QC choices, then rerun the validator and `--prepare-only`. The original manifest currently fails missing-coordinate checks. Metadata audits and synthetic tests are not a full-corpus run. |
| 5.6 | **Checkpoint-hardlink portability.** save_finetuned_checkpoint hardlinks vocab files; plain rsync/cp without -H duplicates them (disk bloat, not corruption — _link_or_copy falls back to copy). A note for the A40 rsync. | **Accepted** — operational note. |
| 5.7 | **Persistent workers missed epoch updates.** Multiprocess regressions confirmed that the old implementation replayed epoch one during epoch two. | **Resolved** — shared CPU tensor propagates epochs under fork/spawn; worker draws match the direct sampler and resume across epochs matches uninterrupted sample order. Sampling probabilities are unchanged. |
| 5.8 | **Training lacked a prepared-artifact integrity gate.** Old reports could not establish agreement of configuration, sources, post-QC membership, and splits. | **Resolved (code/bounded expression rehearsal)** — fresh reports record source positions, configuration/asset fingerprints, and file hashes; training validates complete membership and embryo isolation before model/DDP loading. A two-source, 256-row real rehearsal retained 254 rows; full-corpus preparation still awaits decisions. |

## 6. Evaluation-harness validity

| # | Issue | Status |
|---|---|---|
| 6.1 | **Spatial checkpoints were unevaluatable (P2, eval half).** Evaluate never set up the `spatial_bin` aux vocab → strict load_state_dict crash. | **Resolved** — evaluate mirrors the spatial aux setup. `7cb9a6c` |
| 6.2 | **Spatial vs single-cell routing was by assay string (P3).** Stereo-seq labeled "unknown" → spatial holdout files silently contaminated single-cell metrics. | **Resolved** — routing now uses the manifest `dataset_type` from the preparation report (assay-heuristic fallback with warning). `7cb9a6c` |
| 6.3 | **The pseudotime metric was OOM-prone and biologically meaningless (P8).** A dense n×n float64 kNN graph (~80 GB at 100k cells), with one trajectory computed across species. | **Resolved** — sparse kNN pseudotime per group (species → embryo_id fallback) with explicit stage ordering. `7cb9a6c` |
| 6.4 | **"Finetuned" could silently default to the base checkpoint (P9)** → a base-vs-base comparison with zero deltas. | **Resolved** — the evaluate CLI rejects base-as-finetuned and defaults output to the run's output_dir. `7cb9a6c` |
| 6.5 | **Pseudotime per-species grouping is dead code.** prepare.py never writes a `species` obs column, so evaluate always falls back to embryo_id; in the current holdout most groups are single-phase → Spearman = NaN and groups are silently dropped — the metric degenerates to a mean over the few multi-phase groups. | **Fixed in code (2026-09-22)** — preparation writes manifest species, native_stage, and source_dataset; evaluation prefers species whenever the column exists, including a single species spanning multiple embryos, and reports unevaluable groups and observations missing group labels. Synthetic H5AD preparation/split and pseudotime regressions pass. Older outputs need re-preparation; real-corpus validation remains blocked by 5.5. |
| 6.6 | **Spatial metrics pool spots across embryos/sections.** spatial_neighborhood_consistency and Moran's I build one kNN graph over all spatial files pooled, so spots from different embryos/sections with similar coordinates become false neighbors (unlike the per-group pseudotime fix, 6.3). | **Fixed in code (2026-09-22)** — both metrics build graphs per section using the available composite source_dataset/species/embryo_id/section_id identity. Reports retain per-section results and their unweighted mean, explicitly accounting for missing identity, invalid coordinates/embeddings, and undersized sections. Positional alignment supports duplicate obs names. Synthetic spatial/evaluation regressions pass; real-corpus validation still awaits the preparation run in 5.5. |

## 7. Statistical and scientific validity of downstream claims

| # | Issue | Status |
|---|---|---|
| 7.1 | **No null model for likelihood-drop impact scores (S1).** Deleting a highly expressed gene removes more likelihood mass, so rankings are dominated by expression/detection rate rather than regulatory importance. | **Designed (frozen)** — expression- and dropout-matched 10×10 quantile-bin permutation null per species × phase stratum; empirical p-values + z-scores; BH FDR q = 0.05 per stratum. Implementation pending (post-training analysis). |
| 7.2 | **The "known essentials rank high" validation is circular (S1).** Mouse-derived knowledge, a mouse-heavy corpus (53%), and memorized co-expression. | **Designed (frozen)** — 8 external falsification sets (MGI/IMPC, CRISPRz, FlyBase, WormBase RNAi, Jin 2020 Perturb-seq, gastruloid screens, Replogle negative control, urchin GRN). Verdict rule: AUROC > 0.6 and FDR < 0.05 in ≥ 2 **non-mouse** sets among {2,3,4} (CRISPRz / FlyBase / WormBase), and rankings not housekeeping-dominated; mouse alone never counts as falsification. Maternal-mRNA caveat: zebrafish F0 crispants systematically underestimate early-phase essentials (maternal deposition masks early-acting genes), so lower AUROC at early phases is expected and must be reported as such. |
| 7.3 | **No base-model control arm (S2).** Every headline analysis can run on the zero-shot base model, so the marginal value of finetuning was never going to be measured. | **Designed; B1 requires revision (see 7.7)** — base-model baselines B1–B4 with pre-registered improvement criteria (≥ 5% holdout-likelihood gain in ≥ 6/8 species with no species degrading > 2% (B1); ≥ 5-point absolute phase kNN-purity gain; ≤ 2-point probe degradation; ≤ 0.02 AUROC drop). If the base model already satisfies the headline claims, the finetune is demoted to a robustness check. |
| 7.4 | **Catastrophic forgetting is unmonitored (S3).** Improvement on the embryo holdout measures domain adaptation, not retention of the zero-shot ability the probe evaluation depends on. | **Designed (frozen thresholds)** — frozen non-embryo reference set (CELLxGENE Census human/mouse adult + sponge/yeast canaries, optional Fly Cell Atlas); per-checkpoint likelihood delta + linear CKA; non-regression gate (3% / CKA 0.90) with a response ladder ending in the LoRA fallback. The canaries are only a tripwire for gross representational collapse (P. falciparum is in the model vocab but has no local dataset, so it cannot serve as a canary — design doc §4.1); the embryogenesis-relevant forgetting monitor is the B4 probe-species arm (see 7.3/B4). **Reference set not yet downloaded/built.** |
| 7.5 | **Causal-language risk.** Likelihood impact is associational. | **Accepted with rule** — prohibited: "gene X drives/regulates phase P" without wet-lab or external-screen support; permitted: "top-ranked likelihood impact score at phase P (bin-null z = …, FDR q = …)". |
| 7.6 | **Tier-2 counterfactual-validation scope.** Does counterfactual generation get validated against real perturbation data? | **Resolved (in scope)** — against Jin et al. 2020 (35 ASD/ND risk genes, in-utero Perturb-seq): overlap of predicted downstream-affected genes with observed DE genes. User-approved 2026-09-09. |
| 7.7 | **The six-species B1 gate is unachievable.** Item 7.3 requires improvement in ≥6/8 training species; the real projection provides holdout for only human/mouse. B4 probes cannot fill B1’s denominator. | **Open — pre-training gate** — `649b702` measures coverage and explicitly reports blocked without changing the criterion. Before observing results, agree on evaluable species and a revised criterion or acquire independent embryos; the original threshold remains decision history. |

## 8. Probe species and ESM2 embeddings

| # | Issue | Status |
|---|---|---|
| 8.1 | **Probe species are out-of-vocabulary.** Macaque, pig, guinea pig, Xenopus tropicalis, ciona, and amphioxus are not TF-Metazoa vocab species → their genes have no learned token embeddings. | **Designed** — tokens built from ESM2 protein embeddings per `preprocess/fasta_manifest_pep.json`; pig and X. tropicalis embeddings are downloadable pre-generated; **macaque (*Macaca fascicularis*), guinea pig, ciona, and amphioxus must be generated locally** via `preprocess/protein_embedding.py` (not yet done — generation on this host is memory-constrained and must use chunked inference). Pre-generated ESM2 embeddings exist only for *M. mulatta* (a different species), so fascicularis embeddings genuinely need local generation; and fasta_manifest_pep.json currently has NO entries for ciona, amphioxus, guinea pig, or *M. fascicularis* — entries must be added before protein_embedding.py can run (guinea pig had been silently dropped from the embedding plan and is now restored). |
| 8.2 | **Gene-level cross-species statements for probes need the same 1:1 ortholog table** (see 4.3); embedding-level comparisons do not. | **Designed** — shares the orthology framework of `docs/perturbation-and-baseline-design.md` §6 (not §6 of this register). |
| 8.3 | **Probe phase mappings are machine-readable and checked against real labels.** The documented conventions are encoded per dataset in `preprocess/probe_stage_mappings.json`. | **Resolved (mapping/checker)** — `865bc5f`: all observed stages in eight files/six species are covered, with no missing/unknown labels; 12 regressions pass. `scripts/validate_probes.py` explicitly reports missing species vocabularies, four FASTA entries, and unresolved metadata, so probe execution remains blocked. Gene coverage and boundary sensitivity are not validated by this report. |

---

## For our collaborators: decisions we need from you

Items 1–5 need a ruling from our biology and data collaborators; item 6 records completed engineering work. For each we give the background, the question, the candidate options (with our recommendation marked), and the consequence of each option; machine-learning terms are explained inline where they first appear. The items are independent — feel free to answer them separately by number.

### 1. Fate of the mouse E8–P0 prenatal time-lapse atlas (see 1.11, 1.2)

**Background.** The Nature 2024 mouse prenatal time-lapse atlas spans E8 to birth and comprises 11,441,407 nuclei (sci-RNA-seq3) — the largest dataset in the collection. It sits on disk and has never entered the training corpus. Our audit confirmed zero barcode overlap with the other 12 mouse files in the corpus; however, the TOME E8.5b file (154,313 cells) already in the corpus turned out to be a republished slice of this atlas's run_4 (E8.0–E8.5) subset (99.54% barcode match, identical count vectors).

**Question.** Should this atlas — or any part of it — enter the finetune training corpus?

**Options.**

- **Exclude it entirely (our recommendation).** Consequence: the corpus stays as it is. Most of the atlas's stages lie outside the embryogenesis scope (it runs to birth), and full inclusion would push mouse from 53% to ~90% of the corpus, sharply worsening the existing mouse bias and weakening cross-species claims.
- **Mine only the E8–E13.5 window.** Consequence: adds mouse neurula/organogenesis data, but the volume included would still need tight control to avoid recreating the mouse bias.

**Hard constraint (whichever option is chosen).** If any part of the atlas is included, TOME E8.5b must be dropped from the corpus first — otherwise the same cells enter via two files and can land in both train and holdout (the train/holdout split: one part of the data is used for training, the other strictly reserved for evaluation), constituting leakage — the D1 duplication class already resolved in 1.1.

### 2. Whether to include the Nature2019 E4.5–E7.5 multi-omics dataset (see 1.18)

**Background.** A second on-disk dataset has never been used: the mouse Nature2019 E4.5–E7.5 multi-omics dataset, 2,971 cells (GSE133725, raw counts, ENSMUSG gene IDs). Its window partially covers what is currently the corpus's thinnest stratum: vertebrate blastula/early gastrula coverage is thin — mouse contributes only 952 blastula cells in total, and human blastula is absent entirely (see 1.8).

**Question.** Should it be included in the training corpus?

**Options.**

- **Include it, provided its QC checks out (our recommendation).** Consequence: vertebrate blastula is the weakest stratum of the corpus, and this dataset directly reinforces that window; at 2,971 cells it would not shift the species balance.
- **Document an exclusion.** Consequence: the corpus stays as it is; blastula-phase claims remain mouse-only and low-n (the existing 1.8 caveat stands).

### 3. Sampling-weighting strategy (see 3.8)

**Background.** The actual sampler audit is available (3.8): the algorithm caps the single-cell pool by stage × cell_type, then samples uniformly with replacement within modality; it does not balance species. The pre-QC first epoch projects 2 million draws: spatial ~30%, human 38.04%, mouse 34.26%, fly 13.27%, with 930k repeated draws. These shares arise from the current corpus and cap, not fixed species weights. Regenerate after final QC.

**Question.** Which weighting do we finalize for training?

**Options.**

- **Keep BalancedDataset.** Consequence: retain modality mixing, stratified caps, and replacement draws; species shares follow corpus composition, with no species-balance guarantee. Assess the measured exposure against the biological question.
- **Switch to natural weighting.** Consequence: matches the sampling distribution of base-model pretraining and is simpler, with no repeats; the cost is that mouse dominates training and the bias flows straight into the model.

**Where we would like your view:** from the biology side — above all for cross-species same-phase comparisons (e.g. comparing gene programs at gastrula across species) — would fly, worm, and sea urchin being underrepresented in training harm the conclusions you care about? If so, we would need an explicit species-weighting design; the current BalancedDataset has no such parameter.

### 4. Doublet and QC screening (see 1.13, 1.5, 1.15)

**Background.** Three related data-quality gaps: (a) no dataset carries usable doublet annotations (a doublet is two cells captured in one droplet) — the fly atlas's own `predicted_doublet` column is uniformly "Singlet" and uninformative; (b) there is no mitochondrial-fraction or ambient-RNA filtering anywhere, so every training dataset enters unscreened; (c) 27% of the mouse single-embryo timecourse (14,775 of 54,948 cells) lacks developmental_time staging (NaN) and currently flows through preparation as the literal string "nan", uncounted in phase composition.

**Question.** From the source publications, do you have QC expectations we should follow?

**What would help us.**

- Did the source papers publish doublet calls that we could join back by cell name?
- Were the 27% unstaged cells excluded from staging for a specific QC reason in the source paper? If so, we should mirror that.

**If no further information is available (our default).** We run a computational screen before training (Scrublet-style doublet scoring, an algorithm that scores each cell against simulated doublets); the NaN-stage cells are kept in training (they still carry expression signal) but excluded from all phase-resolved metrics.

### 5. Assay-vocabulary normalization (see 1.14)

**Background.** The model input carries an assay (sequencing platform) token (the smallest unit of model input — here, a platform category label) whose vocabulary (assay_vocab.json, 40 keys) contains `sci-RNA-seq` but not `sci-RNA-seq3`; the tokenizer silently maps out-of-vocab keys to "unknown". As a result, the fly's 547,805 cells (~17% of the corpus), all Stereo-seq spots, and the plate-based mouse timecourse share ONE "unknown" assay token — three genuinely different platforms conflated in the model input.

**Question.** Can you confirm the true platform assignment for each dataset — which were 10x 3' v3, which sci-RNA-seq3, which inDrop, and which Stereo-seq? These are stated in the source papers and should be quick for you to verify.

**Next step (after confirmation).** We normalize each dataset's assay label accordingly so that in-vocab platforms get their own token; for platforms the vocabulary genuinely lacks, we then decide between an explicit label and a kept "unknown" that at least is not shared across platforms.

### 6. Spatial engineering completion record (see 1.12, 3.9, 3.11)

**Completed.** Embryo-level isolation is implemented and checked on real metadata. The coordinate tool defaults to read-only auditing; explicit copy mode writes new files and a derived manifest, preserving original data and native sections. Full metadata-copy round-trips cover all 412,374 spots. The in-place mutation and constant-section proposals are superseded; sign-off on those old mechanisms is no longer requested.

**Still pending.** Create full expression copies, finalize corpus/QC configuration, and run preparation. Training species have no spatial holdout; their spatial scores are descriptive, and independent probe evaluation still needs missing assets/metadata. See 7.7 for the separate B1 decision.

**How to respond.** Please reply per pending item number (1–5); if you disagree with only some items, it is fine to answer just those. For anything unanswered by [a deadline the project owner fills in], we will proceed with the **recommended** option marked above as the default.

*Compute-resource issues (gene-ID head VRAM, epoch time, bf16, WSL memory, A40 setup) are intentionally excluded here; see the C-findings in the adversarial review and ADR 0003 §compute.*
