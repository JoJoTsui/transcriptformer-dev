# 多物种胚胎发生微调的主要问题清单(中文版)

汇总本次微调的所有重大问题——来源包括对抗性评审(`docs/agents/adversarial-review-2026-09-09.md`)、数据集审计(`logs/dataset_audit/`)、整改计划(ADR 0003)以及验证设计文档(`docs/perturbation-and-baseline-design.md`)。本文自身亦经三方对抗性复核并修订(`docs/agents/register-review-2026-09-14.md`)。**计算资源类问题(显存、单轮训练时长、GPU 数量、WSL 内存)不在本文范围内**——它们单独记录在评审报告的 C 类发现、下方的训练前待决事项清单以及 ADR 0003 的计算部分中。

状态标记:**已解决**(已修复并验证,附提交号)· **已设计**(方案已确定,实现待做)· **待决**(尚无定论)· **已接受**(已知局限,附缓解措施)。

---

## 1. 语料库组成与数据完整性

| # | 问题 | 状态 |
|---|---|---|
| 1.1 | **TOME 与原肠胚图谱重复(D1)。** 8 个 TOME 文件(E6.75–E8.5a,共 105,373 个细胞)与 139k 细胞的原肠胚图谱逐字节重复;TOME E6.5 也有 78.4% 重复且计数向量完全一致。相同细胞可能同时落入训练集和留出集。 | **已解决** — 丢弃 9 个文件,保留图谱;`validate_manifest.py` 新增跨文件去重检查(同一物种文件间共享 barcode 超过 1,000 即硬性失败;当前 106 对比较全部通过;范围限制:该检查每个文件仅抽样前 50,000 个 obs_names)。`c088eeb` |
| 1.2 | **TOME E8.5b 来源之谜——已查明。** 该文件(154,313 细胞)实为 Nature 2024 出生前时间序列图谱(见 1.11)run_4(E8.0–E8.5)子集的再发布:同时去除 `run_N_` 前缀和末尾 `-<i>` 后缀后 barcode 匹配率 99.54%(153,597/154,313),抽样 120 个共享细胞的计数向量完全一致;与 TOME 其余文件无关。 | **已解决(来源)** — 目前保留在清单中:只要 1.11 的出生前图谱保持排除状态,语料内就不存在重复。**但若纳入该图谱的任何部分,必须先丢弃 E8.5b**(D1 式重复)。716 个未匹配细胞(零散孔板)记录于验证脚本 `.scratch/verify_e85b_vs_prenatal.py` 与 ADR 0003。`59bf940` |
| 1.3 | **人 CS6 fig3 ⊂ fig2(D2)。** 8,445 个 spot,obs 名 100% 重合;三个 fig 文件本属同一胚胎却带三个 embryo_id。 | **已解决** — 丢弃 fig3;fig1/fig2 共用 `embryo_id: human_cs6`,保留不同 section_id。`c088eeb` |
| 1.4 | **果蝇重建 raw 文件缺少可用元数据。** 547,805 个细胞的 `cell_type` 全为 "unknown",且 assay 常量错误(应为 sci-RNA-seq3 而非 10x)。 | **已解决** — 从 Science 2022 注释文件按 obs 名 100% 匹配并入 `cell_type`(51 类,仅 0.55% unknown)与 `predicted_doublet`;assay 更正为 sci-RNA-seq3(GSE190147)。`c088eeb` |
| 1.5 | **果蝇 `predicted_doublet` 无信息量** — 注释源中该列为单一取值 "Singlet"。 | **已接受** — 如实并入;该注释无法用于双联体过滤。 |
| 1.6 | **小鼠时间序列的"空孔"。** 4,188 个 `embryo_id == "empty"` 的细胞(空板孔)会被按胚胎划分逻辑当作一个"胚胎"。 | **已解决** — 在源头剔除(59,136 → 54,948 细胞,188 个真实胚胎),记录于 `uns["empty_well_exclusion"]`。`c088eeb` |
| 1.7 | **非整数/已处理矩阵。** 部分源文件提供的是归一化或缩放后的值(CS9 scRNA、兔图谱、Tyser CS7、果蝇连续体)而非原始计数。 | **已解决** — raw 层已重建并全量校验;确属缩放并已剔除的文件是人 CS9 scRNA(2,150 个细胞,raw_counts=False);CS9 Stereo-seq 空间文件(96,837 个 spot)自始至终为整数值,仍保留在语料中;重新生成的审计确认清单内所有数据集均为整数值。 |
| 1.8 | **脊椎动物囊胚期覆盖单薄(S7)。** 小鼠合计仅 952 个细胞(每文件 67–464);人囊胚期数据完全缺失。 | **已接受** — 已发表图谱的固有数据局限;囊胚期结论只能限于小鼠且须标注低样本量。 |
| 1.9 | **物种鉴定错误。** 海胆数据集实为 *Lytechinus variegatus* 而非最初假定的 *S. purpuratus*;清单此前也没有显式物种字段。 | **已解决** — 全部 27 个条目均带显式 `species` 字段(校验器强制格式)。`c088eeb` |
| 1.10 | **审计产物过时。** report.json/summary.txt 描述的还是整改前 37 条目的语料。 | **已解决** — 已按 27 条目清单重新生成(2,855,332 细胞 / 22 个单细胞文件 + 412,374 个 spot / 5 个空间文件)。`85d43fc` |
| 1.11 | **小鼠 E8–P0 出生前时间序列(Nature 2024)在库但完全未使用。** 与用户的物种数据集思维导图(物种.xmind / 胚胎期单细胞转录组物种与数据集.png)核对时发现:`Nature_2024_prenatal_time_lapse` 在磁盘上,但从未进入审计、清单或任何计划文档——它是整个收藏中最大的数据集。**2026-09-09 已补审计**(h5py 直接读取,脚本在 `.scratch/`):磁盘上是 4 个 CELLxGENE 随机分片(UUID 文件名,各约 34 GB、约 286 万 × 45,525 个 ENSMUSG 基因;`uns/title` = "Whole dataset: Normalized subset N";obs 名两两零重叠;var 逐字相同;每个分片都覆盖全部 43 个 `author_day` 分箱和全部 16 个测序 run)。**合计 11,441,407 个细胞核,与论文声明完全一致。** 观测类型为细胞核(sci-RNA-seq3,`suspension_type=nucleus`);74 个供体胚胎(`donor_id`);`author_day` 43 个分箱 E0800-E0850…P0000(论文宣称 45 个时间点),Theiler 12–27;`author_cell_type` 190 类 / `cell_type` 134 个 CL 术语;`X` 为 log 归一化值,整数原始计数在 `raw.X`/`layers["raw.X"]`;obsm 仅 `X_umap`。原审计失败原因:anndata 0.11 的 `read_h5ad(backed="r")` 会把 `layers["raw.X"]`(48.8 亿 nnz,仅 int64 indices 就需 36.4 GiB)整体物化,超出 26 GiB 内存上限。与训练语料的重叠:与其他 12 个小鼠文件 barcode 零重叠;**但 TOME E8.5b(154,313 细胞)去掉 `run_N_` 前缀后 99.54% 的 barcode 落在本图谱 run_4(E8.0–E8.5)子集中,抽样 120 个共享细胞的计数向量完全一致**——E8.5b 实为该 Nature 2024 图谱的再发布切片,这同时解释了 1.2 的来源疑问。 | **待决** — 建议明确记录为排除:其大部分阶段超出胚胎发生范围(延伸至出生),且纳入会让小鼠占比从 53% 升至约 90%,加剧鼠偏倚。可选:仅挖掘其 E8–E13.5 窗口补充神经胚/器官发生期数据。**若任何部分被纳入,必须先丢弃 TOME E8.5b(D1 式重复)。** 需用户裁定。 |
| 1.12 | **5 个空间文件中 3 个的空间坐标缺失。** fig1、CS8、CS9 的 obsm 为**空**(校验器"坐标位于 obsm,暂缓处理"的注释有误):fig1/CS9 的坐标仅嵌在 obs_names 中(如 `EV1-24_2220_14040`),CS8 的嵌在 `spot_id` 中(`slice1_S10_…`);仅 fig2 有 `X_spatial`、CS7 有 obsm `spatial`。照此现状,41.2 万个 spot 中的 35.2 万个无法进行空间分箱,两项空间指标均不可计算;必须按文件定制解析。 | **待决** |
| 1.13 | **全库无双联体/线粒体/环境 RNA 质控。** `_apply_qc` 仅支持 min/max 基因数与 counts(清单只设了 min_genes: 200);没有数据集带可用的双联体分数(1.5 的仅覆盖果蝇),`percent.mito` 虽存在于 fig1/CS9 的 obs 但未被使用,也无环境 RNA 处理。每个训练数据集都未经筛查入库——双联体风险最高的 54.7 万细胞 sci-RNA-seq3 果蝇图谱被明确判为无法过滤。 | **待决** — 裁定是否在训练前运行计算性双联体/质控筛查。 |
| 1.14 | **assay 词表 token 错标。** 模型 assay 词表(assay_vocab.json,40 个键)含 `sci-RNA-seq` 但**不含** `sci-RNA-seq3`,而分词器把缺失键映射为 "unknown":果蝇的 547,805 个细胞(约占语料 17%)、全部 Stereo-seq spot 和孔板法小鼠时间序列静默共用同一个 "unknown" assay token——三个平台在模型输入中被混为一谈。(另:composition.md 声称 inDrop 不在 assay 词表内——错误,它是第 13 号键。) | **待决** — 训练前裁定 assay 字符串归一化。 |
| 1.15 | **小鼠单胚胎时间序列 27% 的细胞无分期。** 54,948 个细胞中有 14,775 个 developmental_time 为 NaN;它们在准备过程中带着字面分期字符串 "nan",在子采样中形成自己的 (nan, unknown) 分层,在评估中带警告排在最后;阶段构成中未计入这批细胞。 | **待决** |
| 1.16 | **spot ≠ 细胞。** 41.2 万个 Stereo-seq spot(多细胞测量)以与单细胞相同的逐细胞似然训练;只有评估路由(6.2)区分二者。对训练和阶段层面结论的分辨率/去卷积警告。 | **已接受** — 缓解措施待定;记录为警告。 |
| 1.17 | **人原肠胚期空间旗舰数据约 87% 为胚外组织。** fig1(41.2 万 spot 中的 228,028 个):PL.EXMC+CTB.Fusion+STB+CTB+MTB = 199,586(87.5%)为滋养层/胎盘;fig2 有 51% 为连接蒂。除非在分析时按细胞类型过滤,人原肠胚期结果将由胚外组织主导。 | **已接受** — 分析层过滤规则;记录为组成警告。 |
| 1.18 | **第二个在库但未使用的数据集。** 小鼠 Nature2019 E4.5–E7.5 多组学(2,971 个细胞,GSE133725,原始计数,ENSMUSG)不在任何审计/清单/计划中;可部分覆盖单薄的囊胚/原肠胚窗口(1.8)。 | **待决** — 记录排除或纳入。 |
| 1.19 | **Tyser CS7 重建细胞数差异。** 重建文件为 1,170 个细胞,旧处理文件为 1,195 个;两个命名空间的 obs 名零重叠,25 个细胞的差异无法追溯;可能源于不同的源 QC 版本。 | **已接受** — 已记录。 |

## 2. 胚胎发生(分期 → 阶段)映射

| # | 问题 | 状态 |
|---|---|---|
| 2.1 | **果蝇滑动窗口"不一致"(S4)。** 相互重叠的 4 小时采样窗口(hrs_06_10 与 hrs_08_12)把同一段 8–10 小时间隔分到了两个阶段——看似映射错误。 | **已解决(作为约定)** — 每个窗口按**中点**归入唯一阶段(胚带延伸 ≈ 4–9 h → 神经胚期);规则已写入 `preprocess/stage_phase_mapping.md`。但逐阶段*分析*必须按窗口中点把每个细胞去重到单一阶段——**实现待做**(分析层)。 |
| 2.2 | **线虫 100–130 分钟分箱误配。** 线虫原肠胚形成始于 26–28 细胞期(约受精后 100 分钟),原标为囊胚期的该分箱已覆盖早期原肠胚形成。 | **已解决** — 移至原肠胚期(用户裁定,记录于 `stage_phase_mapping.md` 与清单)。`fa5cf1b` |
| 2.3 | **斑马鱼 24 hpf 误配。** 24 hpf 是咽胚期起点,而非器官发生期。 | **已解决** — 移至神经胚期(用户裁定,已记录)。`fa5cf1b` |
| 2.4 | **边界判定缺乏文献依据。** 五项边界判定此前仅凭经验。 | **已解决** — 完整引文表见 `docs/perturbation-and-baseline-design.md` §5(O'Rahilly & Müller、Downs & Davies、Kimmel、Hamburger & Hamilton、Sulston、Campos-Ortega & Hartenstein、Ton 2023、Massri 2021)。`1b0196d` |
| 2.5 | **斑马鱼"神经胚期"是系统型对齐约定。** Kimmel 分期本无"神经胚"一词;14–24 hpf = 体节期/咽胚期。果蝇胚带与线虫 comma 期归入神经胚期同理——无脊椎动物没有真正的神经胚。 | **已接受** — 明确记录为约定而非事实;所有跨物种结论必须承认这一粗粒度阶段词表。 |
| 2.6 | **边界稳健性未验证。** 任何一个分箱边界的错误都会改变阶段构成。 | **已设计** — 预注册敏感性分析:每个边界向两侧各平移一个分箱,重跑核心指标。注意:平移边界会重构分层本身,命中名单的成员资格会机械地随之改变——敏感性指标应以细胞层面分数的稳定性(与平移无关)为主要锚点,每个分层 top-100 扰动命中基因在两种平移下保持 ≥ 80% 重合作为次要校验。训练后执行。 |
| 2.7 | **物种 × 阶段矩阵空洞(超出 1.8 的囊胚单薄问题)。** 海胆无神经胚分层(16 hpf 原肠胚 → 18–24 hpf 棱柱幼体→器官发生);鸡只有原肠胚/神经胚;兔和人均无囊胚期。任何"全部 8 个物种在阶段 P"的陈述都会随阶段静默改变物种构成。 | **已接受** — 每份跨物种报告必须附阶段构成表。 |

## 3. 数据集划分与留出设计

| # | 问题 | 状态 |
|---|---|---|
| 3.1 | **划分按文件常量而非按胚胎(D4)。** 真实的逐胚胎 obs 列(小鼠时间序列 189 个 embryo_id 值 = 188 个真实胚胎 + 1 个 "empty" 伪胚胎(1.6)、人 CS12–16 共 7 个胚胎)从未被使用;ADR 中"单胚胎数据集仅入训练集"的规则没有实现机制。 | **已解决** — 两遍式按(数据集 × 胚胎)划分 + 按物种分层;每条划分连同原因记录于 `split_assignments.json`。`55225c3` |
| 3.2 | **seed-42 划分经实证损坏(P1)。** 斑马鱼整体落入验证集(从未参与训练,却驱动早停);最终留出集仅覆盖 8 个物种中的 2 个。 | **已解决** — 按物种逐一分层;dataset_type 仅通过 train_only/single_section 资格规则进入划分(prepare.py);保证每个物种至少有 1 个胚胎进入训练集。`55225c3` |
| 3.3 | **留出集代表性缺口(3.1 修复的必然结果)。** 混合单胚胎数据集(线虫、兔、鸡、果蝇、斑马鱼)永远只进训练集——留出指标只能来自多胚胎文件(小鼠时间序列、人 CS12–16、空间切片)。 | **已接受** — 依 ADR 0002/0003;留出指标对这五个物种的种内泛化不提供任何信息。跨物种结论须依靠直系同源/阶段分析和零样本探测物种。 |
| 3.4 | **单胚胎数据集的细胞级泄漏。** 在同一胚胎内按细胞划分会把胚胎状态泄漏进留出集。 | **已解决** — 设计上已否决(ADR 0002);单胚胎/单切片数据集仅入训练集。 |
| 3.5 | **同一胚胎的空间切片。** CS6 fig1/fig2 是同一胚胎的切片;分开划分会产生泄漏。 | **已解决** — 共用 embryo_id、保留不同 section_id;按切片划分保证它们同侧。`c088eeb` |
| 3.6 | **没有阶段留出,也没有物种留出。** 当前设计按*胚胎*留出;无法度量对未见阶段或训练集内未见物种的泛化。 | **已接受** — 未见物种泛化改由保留的零样本探测物种覆盖(猕猴、猪、豚鼠、热带爪蟾、海鞘、文昌鱼)。阶段留出并非"无意义":在逐胚胎划分下,中段阶段留出会近乎泄漏(E8.4 训练细胞 ≈ E8.5 留出细胞),末段阶段留出度量的其实是发育时间外推;本设计接受这一盲区——**没有任何指标度量对未见阶段的泛化**。另注意探测物种的构造性警告:探测物种在词表之外,运行于训练中从未见过的 ESM2 构造 token 上,因此探测成败把 ESM2 token 构造质量与模型泛化混为一谈——与词表内物种留出是根本不同的度量工具。 |
| 3.7 | **伪重复(S5)。** 327 万细胞 ≈ 每个 物种 × 阶段 仅 n = 1–3 个胚胎(人原肠胚期 = 3 个胚胎:1 个 CS6 + 2 个来自不同论文的不同 CS7 数据集——Tyser scRNA 1,170 个细胞 + CS7 Stereo-seq 空间 28,804 个 spot;兔/鸡/果蝇/线虫各为 1 个混合文件)。 | **已设计** — 所有推断在胚胎层面聚合;每张结果表报告每个 物种 × 阶段 的胚胎数 n;n = 1 的分层仅作描述性报告,不做不确定性声明、不用因果措辞。属分析层规则,在报告时强制执行。 |
| 3.8 | **采样加权不一致(来自 C8)。** 计划声称"自然采样加权",但 `BalancedDataset` 实际会重复小数据集;清单现已设定 `spatial_fraction: 0.3`(对 41.2 万个 spot 每 epoch 约 1.46× 的 spot 复用——早前"约 2.4× 空间过采样"的数字已过时),其 (stage, cell_type) 上限会把果蝇 54.7 万细胞压缩进 ≤ 11 个组。 | **待决** — 训练配置定稿时需裁定:接受当前 `BalancedDataset` 行为,还是实现真正的自然加权模式。 |
| 3.9 | **【严重】CS8 同胚胎切片泄漏。** 人 CS8 文件是**一个**胚胎,自带原生 `section_id` obs 列(62 个取值,S1–S62)。`_apply_obs_columns` 从不覆盖已存在的列,而空间划分以 section_id 为单位 → 62 个合格单元 → 同一胚胎的切片被分层进训练集**和**留出集。这正是 3.5 为 CS6 修复的泄漏类别,且更糟:fig1/fig2/CS7/CS9 得到常量 section_id → single_section → 仅入训练集,CS8 因而是唯一的空间留出数据——即整个空间留出都是泄漏的。 | **待决** — 正式 prepare 运行前必须修复(如:对单胚胎文件强制常量 section_id,或为空间数据加胚胎级覆盖)。 |
| 3.10 | **探测物种替代不了词表内物种留出。** 见 3.6 新增的构造性警告:词表外的 ESM2 构造 token 使探测评估成为另一种度量工具;词表内的未见物种泛化没有任何指标度量。 | **已接受** — 承认度量缺口(没有可匀出的词表内物种:语料中全部 8 个词表物种都是阶段覆盖所必需的)。 |

## 4. 基因标识、映射覆盖率与直系同源

| # | 问题 | 状态 |
|---|---|---|
| 4.1 | **版本号剥离破坏了非 Ensembl 标识(D3)。** 按 "." 截断毁掉了 8,693 个线虫序列名(`2L52.1`)和 2,073 个斑马鱼旁系同源符号(`acy3.1`);声称的 90% 线虫覆盖率实际只有约 47%。 | **已解决** — 剥离仅限 Ensembl/FBgn/WBGene 模式;覆盖率已按真实代码路径重算。`55225c3` |
| 4.2 | **映射后重复基因 ID 从未合并(P7)。** 1,107 个人类 / 2,817 个小鼠 / 2,025 个海胆词表基因对应 ≥ 2 个源列 → 构建训练数据集时崩溃,或推理时静默跳过整个文件。 | **已解决** — 重复项按计数求和合并,并在准备报告中以 `duplicate_genes_collapsed` 字段记录。`55225c3` |
| 4.3 | **各物种映射覆盖率曾为 47–82%(整改前数字,S6)。** 覆盖率差异会制造虚假的跨物种分化:某基因若不在物种 A 的映射中,看起来就像"被沉默"。整改后经真实代码路径由校验器实测为 52.7%(Tyser CS7)– 90.2%(线虫)——线虫从修复前的 47% 升至 90.2%。 | **已设计** — 仅使用 Ensembl Compara 一对一直系同源(confidence = 1);海胆覆盖不足时经 S. purpuratus 桥接;抽样 200 对与 OrthoDB/DIOPT 交叉核对;并设**覆盖率下限**:被比较基因 ≥ 60% 有一对一直系同源、且该物种对全基因组一对一集合 ≥ 5,000 个基因,否则结论降级为单物种发现。**直系同源表构建尚未开始。** |
| 4.4 | **基因词表命名空间。** 存在分词时查错物种嵌入的风险。 | **已解决(已验证)** — TF-Metazoa 的 12 个词表在物种间经验证互不重叠。 |

## 5. 训练流程正确性(非计算资源)

| # | 问题 | 状态 |
|---|---|---|
| 5.1 | **早停保存的是最终权重而非最佳权重(P4)。** | **已解决** — 验证集改善时快照最佳检查点。`7cb9a6c` |
| 5.2 | **续训默认开启且实现损坏(P5)。** 未保存优化器/scaler/步数/RNG 状态;崩溃后重跑会用全新 AdamW 状态覆盖好检查点。 | **已解决** — 周期性原子全状态检查点(保留最近 2 个);真正的续训恢复全部状态并跳过已完成的微批次。`7cb9a6c` |
| 5.3 | **无 epoch 级打乱(P6)。** 每个 epoch 以相同顺序重放相同细胞。 | **已解决** — `BalancedDataset.set_epoch()`。`7cb9a6c` |
| 5.4 | **检查点不完整(P2 训练侧)。** 输出目录没有 config.json/词表 → 训练完成的产物不是可评估的模型。 | **已解决** — `save_finetuned_checkpoint()` 原子性地组装完整检查点目录(config + 硬链接词表 + 空间词表 + 权重)。`7cb9a6c` |
| 5.5 | **【严重】整改后语料从未跑过 prepare;且当前会硬失败。** 磁盘上唯一的 split_assignments.json/preparation_report.json 是 8 月 26 日在 4 个玩具斑马鱼文件上的冒烟运行。每一项"已解决"的划分/准备修复(3.1、3.2、4.2)与阶段重映射(2.2/2.3)都未在真实的 27 数据集语料上验证过;ADR 0003 以一次重新验证的 prepare-only 运行作为训练闸门。且它会立即失败:prepare.py:243 要求空间数据集具备 spatial_x/spatial_y obs,没有任何清单 obs_columns 映射它们,而 5 个空间文件中有 3 个的坐标连 obsm 里都不存在(1.12)。 | **待决** — 坐标提取工作必须先于 prepare-only 运行。 |
| 5.6 | **检查点硬链接的可移植性。** save_finetuned_checkpoint 对词表文件使用硬链接;不带 -H 的普通 rsync/cp 会将其复制为独立文件(磁盘膨胀而非损坏——_link_or_copy 会回退为复制)。A40 rsync 时注意。 | **已接受** — 运维备注。 |

## 6. 评估框架的有效性

| # | 问题 | 状态 |
|---|---|---|
| 6.1 | **带空间条件的检查点无法评估(P2 评估侧)。** 评估代码从不设置 `spatial_bin` 辅助词表 → strict load_state_dict 直接崩溃。 | **已解决** — 评估端镜像了空间辅助词表的设置。`7cb9a6c` |
| 6.2 | **空间与单细胞按 assay 字符串路由(P3)。** Stereo-seq 标为 "unknown" → 空间留出文件会静默污染单细胞指标。 | **已解决** — 改按准备报告中的清单 `dataset_type` 路由(assay 启发式仅作兜底并告警)。`7cb9a6c` |
| 6.3 | **拟时序指标既易爆显存又无生物学意义(P8)。** 稠密 n×n float64 kNN 图(10 万细胞约需 80 GB),且跨物种计算一条轨迹。 | **已解决** — 改为按组(物种 → 胚胎 ID 兜底)的稀疏 kNN 拟时序,阶段顺序显式给出。`7cb9a6c` |
| 6.4 | **"微调模型"可能静默默认为基座检查点(P9)** → 基座对基座的零差异比较。 | **已解决** — 评估 CLI 拒绝把基座当微调模型,输出默认写入运行的 output_dir。`7cb9a6c` |
| 6.5 | **拟时序按物种分组是死代码。** prepare.py 从不写入 `species` obs 列,评估总是回退到 embryo_id;当前留出集中大多数分组为单阶段 → Spearman = NaN,分组被静默丢弃——该指标退化为对少数多阶段分组取均值。 | **待决** — 在 prepare 运行时把 species 写入准备好的 obs。 |
| 6.6 | **空间指标跨胚胎/切片混合建图。** spatial_neighborhood_consistency 与 Moran's I 在所有空间文件上混合构建一张 kNN 图——来自不同胚胎/切片但坐标相近的 spot 会成为假邻居(与 6.3 的逐组拟时序修复不同)。 | **待决** |

## 7. 下游结论的统计与科学有效性

| # | 问题 | 状态 |
|---|---|---|
| 7.1 | **似然下降影响分缺少零模型(S1)。** 删除高表达基因会移除更多似然质量 → 排名由表达量/检出率主导,而非调控重要性。 | **已设计(已冻结)** — 按 物种 × 阶段 分层,构建表达量与 dropout 率匹配的 10×10 分位数网格置换零模型;经验 p 值 + z 分数;每层 BH FDR q = 0.05。实现待做(训练后分析)。 |
| 7.2 | **"已知必需基因排名靠前"的验证是循环论证(S1)。** 小鼠来源的知识、小鼠占 53% 的语料、被记住的共表达。 | **已设计(已冻结)** — 8 套外部证伪集(MGI/IMPC、CRISPRz、FlyBase、WormBase RNAi、Jin 2020 Perturb-seq、类原肠胚筛选、Replogle 阴性对照、海胆 GRN);判定规则:第 {2,3,4} 号集合(CRISPRz / FlyBase / WormBase)中 ≥ 2 套**非小鼠**集合 AUROC > 0.6 且 FDR < 0.05,且排名不被持家基因主导。仅靠小鼠永远不算证伪通过。母源 mRNA 警告:斑马鱼 F0 crispant 因母源 mRNA 沉积掩盖早期作用基因,系统性低估早期阶段必需基因——早期阶段 AUROC 偏低属预期,必须如实报告。 |
| 7.3 | **缺少基座模型对照组(S2)。** 所有头条分析都可以先在零样本基座模型上跑;微调的边际价值原本永远不会被度量。 | **已设计(已冻结)** — 基座基线 B1–B4 + 预注册改进标准(≥ 6/8 物种留出似然提升 ≥ 5% 且无任一物种退化 > 2%(B1);阶段 kNN 纯度绝对提升 ≥ 5 点;探测物种退化 ≤ 2 点;AUROC 下降 ≤ 0.02)。若基座已满足头条结论,微调降级为稳健性检验。 |
| 7.4 | **灾难性遗忘无人监控(S3)。** 胚胎留出集上的提升度量的是域适应,而非探测评估所依赖的零样本能力保持。 | **已设计(阈值已冻结)** — 冻结的非胚胎参照集(CELLxGENE Census 人/小鼠成体组织 + 海绵/酵母金丝雀集,可选果蝇细胞图谱);每个检查点计算似然差值 + 线性 CKA;非回归门限(3% / CKA 0.90)+ 响应阶梯,最终以 LoRA 兜底。金丝雀集仅是总体表征崩溃的跳闸线(P. falciparum 虽在模型词表内但本地无数据集,不能作金丝雀——见设计文档 §4.1);与胚胎发生相关的遗忘监控是 B4 探测物种臂(见 7.3/B4)。**参照集尚未下载/构建。** |
| 7.5 | **因果措辞风险。** 似然影响分是关联性指标。 | **已接受(附规则)** — 禁用:"基因 X 驱动/调控阶段 P"(除非有湿实验或外部筛选支持);允许:"在阶段 P 具有 top 级似然影响分(分箱零模型 z = …,FDR q = …)"。 |
| 7.6 | **第二层反事实验证范围。** 反事实生成是否要用真实扰动数据验证? | **已解决(纳入范围)** — 对照 Jin et al. 2020(35 个 ASD/ND 风险基因的宫内 Perturb-seq):模型预测的下游受影响基因与实测差异表达基因的重合度。用户 2026-09-09 批准。 |

## 8. 探测物种与 ESM2 嵌入

| # | 问题 | 状态 |
|---|---|---|
| 8.1 | **探测物种不在词表内。** 猕猴、猪、豚鼠、热带爪蟾、海鞘、文昌鱼均非 TF-Metazoa 词表物种 → 其基因没有可学习的 token 嵌入。 | **已设计** — 按 `preprocess/fasta_manifest_pep.json` 用 ESM2 蛋白嵌入构建 token;猪和热带爪蟾的嵌入可下载现成版本;**猕猴(食蟹猴 *M. fascicularis*)、豚鼠、海鞘、文昌鱼须用 `preprocess/protein_embedding.py` 本地生成**(尚未执行——本机内存受限,必须分块推理)。预生成 ESM2 嵌入仅有 *M. mulatta*(另一物种),食蟹猴嵌入确需本地生成;且 fasta_manifest_pep.json 目前**没有**海鞘、文昌鱼、豚鼠、食蟹猴的条目——须先补条目才能运行 protein_embedding.py(豚鼠此前被静默漏出嵌入计划,现已补回)。 |
| 8.2 | **探测物种的基因级跨物种陈述需要同一张一对一直系同源表**(见 4.3);嵌入级比较则不需要。 | **已设计** — 共用 `docs/perturbation-and-baseline-design.md` §6 的直系同源框架(非本清单 §6)。 |
| 8.3 | **【严重】探测物种没有阶段→阶段映射,B4 按设计无法度量。** 探测数据集自带各自的分期体系(猪 E11.5–E15、文昌鱼 G4/N0/N2/N5、猕猴 CS/ME 期、爪蟾 NF 期),但 `preprocess/stage_phase_mapping.md` 只覆盖 8 个训练物种。冻结的改进标准"探测物种同阶段对齐退化 ≤ 2 点"(7.3/B4)需要逐细胞的探测物种阶段标签,当前无法计算。 | **待决** — 将阶段映射表扩展到 6 个探测物种(引文纪律与 2.4 相同)。 |

---

## 训练前待决事项

1. **TOME E8.5b / 小鼠 E8–P0**(1.2/1.11):维持排除,或仅纳入 E8–E13.5 窗口(若纳入须先丢弃 E8.5b)。
2. **【阻塞】空间坐标解析**(1.12)→ 重跑 prepare-only 并复核 split_assignments.json(5.5)。
3. **【阻塞】CS8 切片泄漏修复**(3.9)。
4. **assay 词表归一化**(1.14)。
5. **采样加权裁定**(3.8)。
6. **直系同源表构建**(4.3)。
7. **探测物种阶段映射**(8.3)。
8. **遗忘监控参照集构建**(7.4)。
9. **果蝇逐细胞阶段指派**(2.1)。
10. **ESM2 生成**(8.1):先补 `fasta_manifest_pep.json` 条目(猕猴 fascicularis/海鞘/文昌鱼/豚鼠),再运行 `protein_embedding.py`(内存受限,需分块)。
11. **双联体/质控筛查裁定**(1.13)。
12. **NaN 分期细胞处理**(1.15)。
13. **Nature2019 E4.5–E7.5** 纳入或记录排除(1.18)。

*计算资源类问题(基因 ID 头显存、单轮训练时长、bf16、WSL 内存、A40 部署)有意不在本文范围内;见对抗性评审的 C 类发现与 ADR 0003 的计算部分。*

---
---

# Major Issues for the Multi-Species Embryogenesis Finetune

Aggregated register of every significant issue raised about this finetune — from the
adversarial review (`docs/agents/adversarial-review-2026-09-09.md`), the dataset audit
(`logs/dataset_audit/`), the remediation program (ADR 0003), and the validation design
(`docs/perturbation-and-baseline-design.md`). This register itself passed a three-way
adversarial re-review (`docs/agents/register-review-2026-09-14.md`). **Compute-resource
issues (VRAM, epoch time,
GPU count, WSL RAM) are deliberately out of scope** — they are tracked separately in the
review's C-findings, the open-items list below, and ADR 0003's compute section.

Status key: **resolved** (fixed and verified, commit cited) · **designed** (fix specified and
agreed, implementation pending) · **open** (no agreed fix yet) · **accepted** (a limitation we
knowingly carry, with a mitigation).

---

## 1. Corpus composition and data integrity

| # | Issue | Status |
|---|---|---|
| 1.1 | **TOME ⊂ gastrulation atlas duplication (D1).** 8 TOME files (E6.75–E8.5a, 105,373 cells) were byte-identical duplicates of the 139k gastrulation atlas; TOME E6.5 was 78.4% duplicated with identical count vectors. Identical cells could have landed in train AND holdout. | **Resolved** — 9 files dropped, atlas kept; cross-file dedup check added to `validate_manifest.py` (hard-fail > 1,000 shared barcodes; currently clean across 106 same-species pairs; scope limit: the check samples only the first 50,000 obs_names per file). `c088eeb` |
| 1.2 | **TOME E8.5b provenance mystery — solved.** The file (154,313 cells) is a republished slice of the Nature 2024 prenatal time-lapse atlas (see 1.11): its `run_4` (E8.0–E8.5) subset, at 99.54% barcode match after stripping both the `run_N_` prefix and the trailing `-<i>` suffix (153,597/154,313), with identical count vectors in 120/120 sampled shared cells; unrelated to the rest of TOME. | **Resolved (provenance)** — kept in the manifest: no in-corpus duplication as long as the prenatal atlas stays excluded (1.11). **If any part of that atlas is ever included, E8.5b must be dropped first** (D1-style duplication). 716 unmatched cells (scattered plates) are recorded in the verification script `.scratch/verify_e85b_vs_prenatal.py` and ADR 0003. `59bf940` |
| 1.3 | **Human CS6 fig3 ⊂ fig2 (D2).** 8,445 spots, 100% obs-name intersection; the three fig files are one embryo carrying three embryo_ids. | **Resolved** — fig3 dropped; fig1/fig2 share `embryo_id: human_cs6` with distinct section_ids. `c088eeb` |
| 1.4 | **Drosophila rebuilt raw had no usable metadata.** 547,805 cells with `cell_type = "unknown"` and a wrong assay constant (10x instead of sci-RNA-seq3). | **Resolved** — `cell_type` (51 categories, 0.55% unknown) + `predicted_doublet` joined from the annotated Science 2022 file at 100% obs-name match; assay corrected to sci-RNA-seq3 (GSE190147). `c088eeb` |
| 1.5 | **Fly `predicted_doublet` carries no information** — categorical with the single value "Singlet" in the annotated source. | **Accepted** — joined faithfully; no doublet filtering possible from this annotation. |
| 1.6 | **Mouse timecourse "empty" wells.** 4,188 cells labeled `embryo_id == "empty"` (empty plate wells) would have been treated as an embryo by per-embryo splitting. | **Resolved** — excluded at the source (59,136 → 54,948 cells, 188 real embryos), recorded in `uns["empty_well_exclusion"]`. `c088eeb` |
| 1.7 | **Non-integer / processed matrices.** Several source files shipped normalized or scaled values (CS9 scRNA, rabbit atlas, Tyser CS7, fly continuum) instead of raw counts. | **Resolved** — raw layers rebuilt and re-validated on the full data vector; the scaled-and-dropped file was the human CS9 scRNA (2,150 cells, raw_counts=False); the CS9 Stereo-seq spatial file (96,837 spots) was always integer-valued and remains in the corpus; regenerated audit confirms every manifest dataset is integer-valued. |
| 1.8 | **Vertebrate blastula coverage is thin (S7).** 952 mouse cells total (67–464 per file); human blastula absent entirely from the corpus. | **Accepted** — irreducible data limitation of published atlases; blastula-phase claims must be mouse-only and flagged as low-n. |
| 1.9 | **Species identity errors.** The sea-urchin dataset is *Lytechinus variegatus*, not *S. purpuratus* as initially assumed; no explicit species field existed in the manifest. | **Resolved** — all 27 entries carry an explicit `species` field (validator-enforced format). `c088eeb` |
| 1.10 | **Stale audit artifacts.** report.json/summary.txt described the pre-remediation 37-entry corpus. | **Resolved** — regenerated against the 27-entry manifest (2,855,332 cells / 22 sc files + 412,374 spots / 5 spatial files). `85d43fc` |
| 1.11 | **Mouse E8–P0 prenatal time-lapse (Nature 2024) is on disk but entirely unused.** Found while reconciling the user's curated dataset map (`物种.xmind` / `胚胎期单细胞转录组物种与数据集.png`): `Nature_2024_prenatal_time_lapse` exists on disk but was never audited, never in the manifest, never mentioned in any plan doc — it is the largest dataset in the collection. **Audited 2026-09-09** (direct h5py reads, scripts in `.scratch/`): on disk it is 4 random CELLxGENE shards (UUID filenames, ~34 GB / ~2.86M cells × 45,525 ENSMUSG genes each; `uns/title` = "Whole dataset: Normalized subset N"; obs_names pairwise disjoint; byte-identical var; every shard spans all 43 `author_day` bins and all 16 sequencing runs). **Shard total = 11,441,407 nuclei, exactly the published count.** Nuclei, not cells (sci-RNA-seq3, `suspension_type=nucleus`); 74 donor embryos (`donor_id`); 43 `author_day` bins E0800-E0850…P0000 (the paper advertises 45 timepoints), Theiler stages 12–27; `author_cell_type` (190 categories) / `cell_type` (134 CL terms); `X` is log-normalized, integer raw counts live in `raw.X`/`layers["raw.X"]`; obsm = `X_umap` only. Original-audit failure mode: anndata 0.11 `read_h5ad(backed="r")` eagerly materializes `layers["raw.X"]` (4.88B nnz; the int64 indices alone need 36.4 GiB) and blew the 26 GiB cap. Overlap vs training corpus: zero barcode overlap with the other 12 mouse files; **but TOME E8.5b (154,313 cells) matches this atlas's run_4 (E8.0–E8.5) subset at 99.54% of barcodes after stripping the `run_N_` prefix, with identical count vectors in 120/120 sampled shared cells** — E8.5b is a republished slice of this Nature 2024 atlas, which also answers the provenance question in 1.2. | **Open** — recommend documenting a deliberate exclusion: most stages are outside the embryogenesis scope (runs to birth), and inclusion would push mouse from 53% to ~90% of the corpus, worsening mouse bias. Optional: mine only its E8–E13.5 window for extra neurula/organogenesis data. **If any part is included, TOME E8.5b must be dropped first (D1-style duplication).** Needs a user decision. |
| 1.12 | **Spatial coordinates absent for 3 of 5 spatial files.** fig1, CS8, CS9 have EMPTY obsm (the validator's "coordinates live in obsm, deferred" note is wrong): fig1/CS9 coordinates exist only embedded in obs_names (e.g. `EV1-24_2220_14040`), CS8's in `spot_id` (`slice1_S10_…`); only fig2 has `X_spatial` and CS7 an obsm `spatial`. As-is, spatial binning and both spatial metrics are impossible for 352k of 412k spots; custom per-file parsing is required. | **Open** |
| 1.13 | **No doublet, mitochondrial, or ambient-RNA QC anywhere.** `_apply_qc` supports only min/max genes and counts (the manifest sets only min_genes: 200); no dataset has usable doublet scores (1.5's is fly-only), `percent.mito` exists in fig1/CS9 obs but is unused, and there is no ambient-RNA handling. Every training dataset enters unscreened — the 547k-cell sci-RNA-seq3 fly atlas (highest doublet risk) is explicitly unfilterable. | **Open** — decide whether to run a computational doublet/QC screen before training. |
| 1.14 | **Assay-vocab token mislabeling.** The model assay vocab (assay_vocab.json, 40 keys) contains `sci-RNA-seq` but NOT `sci-RNA-seq3`, and the tokenizer maps missing keys to "unknown": the fly's 547,805 cells (~17% of the corpus), all Stereo-seq spots, and the plate-based mouse timecourse silently share ONE "unknown" assay token — three platforms conflated in the model input. (Also: composition.md claims inDrop is absent from the assay vocab — wrong, it is key 13.) | **Open** — decide assay-string normalization before training. |
| 1.15 | **27% of the mouse single-embryo timecourse has no stage.** 14,775 of 54,948 cells have NaN developmental_time; they carry the literal stage string "nan" through preparation, form their own (nan, unknown) stratum in subsampling, and sort last with a warning in evaluation. Unaccounted in phase composition. | **Open** |
| 1.16 | **Spots are not cells.** 412k Stereo-seq spots (multi-cell measurements) are trained with the same per-cell likelihood as single cells; only evaluation routing (6.2) separates them. Resolution/deconvolution caveat for training and for phase-level claims. | **Accepted** — mitigation pending; recorded as a caveat. |
| 1.17 | **The human gastrula spatial flagship is ~87% extraembryonic.** fig1 (228,028 of 412k spots): PL.EXMC+CTB.Fusion+STB+CTB+MTB = 199,586 (87.5%) trophoblast/placental; fig2 is 51% connecting stalk. Human gastrula-phase results will be dominated by extraembryonic tissue unless cell-type-filtered at analysis. | **Accepted** — analysis-layer filtering rule; recorded as a composition caveat. |
| 1.18 | **Second unused on-disk dataset.** Mouse Nature2019 E4.5–E7.5 multi-omics (2,971 cells, GSE133725, raw counts, ENSMUSG) is in no audit/manifest/plan; partially covers the thin blastula/gastrula window (1.8). | **Open** — document exclusion or include. |
| 1.19 | **Tyser CS7 rebuild count discrepancy.** The rebuilt file has 1,170 cells vs the old processed file's 1,195; zero obs-name overlap between namespaces, so the 25-cell difference is untraceable; likely a different source QC version. | **Accepted** — noted. |

## 2. Embryogenesis (stage → phase) mapping

| # | Issue | Status |
|---|---|---|
| 2.1 | **Fly sliding-window "inconsistency" (S4).** Overlapping 4 h sampling windows (hrs_06_10 vs hrs_08_12) assigned the same 8–10 h interval to two phases — looked like a mapping bug. | **Resolved as convention** — windows are assigned one phase **by midpoint** (germ-band ≈ 4–9 h → neurula); the rule is now explicit in `preprocess/stage_phase_mapping.md`. Phase-resolved *analyses* must deduplicate cells to a single phase via window midpoint — **implementation pending** (analysis layer). |
| 2.2 | **Worm 100–130 min bin misassigned.** Gastrulation begins at the 26–28-cell stage (~100 min), so the bin labeled blastula overlaps early gastrulation. | **Resolved** — moved to gastrula (user decision, recorded in `stage_phase_mapping.md` and the manifest). `fa5cf1b` |
| 2.3 | **Zebrafish 24 hpf misassigned.** 24 hpf is pharyngula onset, not organogenesis. | **Resolved** — moved to neurula (user decision, recorded). `fa5cf1b` |
| 2.4 | **Boundary calls were uncited.** Five boundary decisions rested on judgment, not literature. | **Resolved** — full citation table in `docs/perturbation-and-baseline-design.md` §5 (O'Rahilly & Müller, Downs & Davies, Kimmel, Hamburger & Hamilton, Sulston, Campos-Ortega & Hartenstein, Ton 2023, Massri 2021). `1b0196d` |
| 2.5 | **Zebrafish "neurula" is a phylotypic-alignment convention.** Kimmel staging has no neurula period; 14–24 hpf = segmentation/pharyngula. Same for fly germ-band and worm comma → neurula in invertebrates, which have no true neurula. | **Accepted** — documented as convention, not fact; all cross-species claims must acknowledge the coarse phase vocabulary. |
| 2.6 | **Boundary robustness unverified.** Any single-bin boundary error shifts phase composition. | **Designed** — pre-registered sensitivity analysis: shift every boundary one bin each direction, rerun core metrics. Caveat: shifting a boundary recomposes the strata, so hit-list membership changes mechanically — the sensitivity metric should anchor primarily on cell-level score stability (shift-invariant), with top-100 hit-list retention ≥ 80% under both shifts as the secondary check. Runs post-training. |
| 2.7 | **Species × phase matrix holes beyond blastula thinness (1.8).** Sea urchin has no neurula stratum (16 hpf gastrula → 18–24 hpf prism → organogenesis); chicken has gastrula/neurula only; rabbit and human have no blastula. Any "all-8-species at phase P" claim silently changes species composition across phases. | **Accepted** — a phase-composition table is required in every cross-species report. |

## 3. Dataset splitting and holdout design

| # | Issue | Status |
|---|---|---|
| 3.1 | **Splits were per-file-constant, not per-embryo (D4).** Real per-embryo obs columns (189 mouse timecourse embryo_id values = 188 real embryos + 1 "empty" pseudo-embryo (1.6), 7 human CS12–16 embryos) were never used; the ADR's "single-embryo datasets are train-only" rule had no implementing mechanism. | **Resolved** — two-pass per-(dataset, embryo) splitting with per-species stratification; every assignment recorded with its reason in `split_assignments.json`. `55225c3` |
| 3.2 | **Seed-42 split verified broken (P1).** Zebrafish landed entirely in validation (never trained, yet drove early stopping); the final holdout covered only 2 of 8 species. | **Resolved** — stratified per species; dataset_type enters only via the train_only/single_section eligibility rules (prepare.py); every species guaranteed ≥ 1 training embryo. `55225c3` |
| 3.3 | **Holdout representation gap (consequence of 3.1's fix).** Pooled single-embryo datasets (worm, rabbit, chicken, fly, zebrafish) are always train-only — holdout metrics come only from multi-embryo files (mouse timecourse, human CS12–16, spatial sections). | **Accepted** — per ADR 0002/0003; held-out metrics say nothing about within-species generalization for those five species. Cross-species claims must lean on the orthology/phase analyses and zero-shot probes. |
| 3.4 | **Cell-level leakage for single-embryo datasets.** Splitting cells within one embryo would leak embryonic state into holdout. | **Resolved** — rejected by design (ADR 0002); single-embryo/section datasets are train-only. |
| 3.5 | **Same-embryo spatial sections.** CS6 fig1/fig2 are sections of one embryo; splitting them apart would leak. | **Resolved** — shared embryo_id with distinct section_ids; per-section split keeps them together. `c088eeb` |
| 3.6 | **No phase holdout or species holdout.** Current design holds out *embryos*; it cannot measure generalization to an unseen phase or unseen species within the training set. | **Accepted** — unseen-species generalization is covered instead by the reserved zero-shot probe species (macaque, pig, guinea pig, Xenopus tropicalis, ciona, amphioxus). Phase holdout is not "meaningless": under per-embryo splits a mid-course phase holdout would be near-leaky (E8.4 train cells ≈ E8.5 holdout cells), and a terminal-phase holdout would measure developmental-time extrapolation; the design accepts the blind spot that NOTHING measures unseen-phase generalization. Probe-construct caveat: probe species are out-of-vocab and run on ESM2-constructed tokens never seen in training, so probe success/failure conflates ESM2 token-construction quality with model generalization — a fundamentally different instrument than an in-vocab species holdout. |
| 3.7 | **Pseudoreplication (S5).** 3.27M cells ≈ n = 1–3 embryos per species × phase (human gastrula = 3 embryos: 1 CS6 + 2 distinct CS7 datasets from different publications — Tyser scRNA 1,170 cells + CS7 Stereo-seq spatial 28,804 spots; rabbit/chicken/fly/worm = 1 pooled file each). | **Designed** — all inference aggregated at embryo level; embryo n reported per species × phase in every results table; n = 1 strata are descriptive-only with no uncertainty claims and no causal language. Analysis-layer rule, enforced at reporting time. |
| 3.8 | **Sampling-weighting mismatch (from C8).** The plan claimed "natural sampling weighting" but `BalancedDataset` repeats small datasets; the manifest now sets `spatial_fraction: 0.3` (≈1.46× spot reuse per epoch over 412k spots — the earlier "~2.4× spatial oversampling" figure is stale), and its (stage, cell_type) caps decimate the fly's 547k cells into ≤ 11 groups. | **Open** — decide at training setup whether the implemented weighting is the intended one or needs a true natural-weighting mode. |
| 3.9 | **[CRITICAL] CS8 same-embryo section leakage.** The human CS8 file is ONE embryo with a NATIVE `section_id` obs column (62 values, S1–S62). `_apply_obs_columns` never overwrites existing columns and spatial splitting uses section_id as the unit → 62 eligible units → sections of the same embryo are stratified into train AND holdout. This is exactly the leakage class 3.5 fixed for CS6, and worse: fig1/fig2/CS7/CS9 get constant section_ids → single_section → train-only, so CS8 is the ONLY spatial holdout data — i.e. the entire spatial holdout is leaky. | **Open** — fix before the real prepare run (e.g. force constant section_id per single-embryo file, or an embryo-level override for spatial). |
| 3.10 | **Probes are not a substitute for an in-vocab species holdout.** See 3.6's new caveat: out-of-vocab ESM2-constructed tokens make probe evaluation a different instrument; unseen-species generalization within the vocab is measured by nothing. | **Accepted** — acknowledged measurement gap (no in-vocab species is spare: all 8 vocab species in the corpus are needed for phase coverage). |

## 4. Gene identity, mapping coverage, and orthology

| # | Issue | Status |
|---|---|---|
| 4.1 | **Version-stripping mangled non-Ensembl IDs (D3).** Stripping at "." destroyed 8,693 worm sequence names (`2L52.1`) and 2,073 zebrafish paralog symbols (`acy3.1`); advertised 90% worm coverage was really ~47%. | **Resolved** — stripping restricted to Ensembl/FBgn/WBGene patterns; coverage recomputed through the real code path. `55225c3` |
| 4.2 | **Duplicate gene IDs after mapping never collapsed (P7).** 1,107 human / 2,817 mouse / 2,025 urchin vocab genes had ≥ 2 source columns → crash at dataset build or silent file skip. | **Resolved** — duplicates collapsed by summing counts, reported as `duplicate_genes_collapsed` in the preparation report. `55225c3` |
| 4.3 | **Mapping coverage ranged 47–82% across species pre-fix (S6).** Differential coverage manufactures false cross-species divergence: a gene absent from species A's mapping looks "silenced". Post-fix validator-measured range is 52.7% (Tyser CS7) – 90.2% (worm) — worm went from 47% pre-fix to 90.2% through the real code path. | **Designed** — Ensembl Compara 1:1 orthologs only (confidence = 1), urchin bridge via S. purpuratus if Metazoa coverage is thin, 200-pair cross-check against OrthoDB/DIOPT, and a **coverage floor**: ≥ 60% of compared genes with 1:1 orthologs and ≥ 5,000 genome-wide 1:1 genes per pair, else the claim is downgraded to single-species. **Orthology table build not started.** |
| 4.4 | **Gene vocab namespaces.** Risk of wrong-species embedding lookups at tokenization. | **Resolved (verified)** — the 12 TF-Metazoa vocabs are empirically disjoint across species. |

## 5. Training-pipeline correctness (non-compute)

| # | Issue | Status |
|---|---|---|
| 5.1 | **Early stopping saved final weights, not best (P4).** | **Resolved** — best-checkpoint snapshot on validation improvement. `7cb9a6c` |
| 5.2 | **Resume was default-on and broken (P5).** No optimizer/scaler/step/RNG state saved; a crashed rerun could clobber a good checkpoint with fresh-AdamW weights. | **Resolved** — periodic atomic full-state checkpoints (keep last 2); true resume restores all state and skips completed micro-batches. `7cb9a6c` |
| 5.3 | **No epoch shuffling (P6).** Every epoch replayed identical cells in identical order. | **Resolved** — `BalancedDataset.set_epoch()`. `7cb9a6c` |
| 5.4 | **Checkpoints were incomplete (P2, training half).** No config.json/vocabs in the output dir → a finished run was not an evaluatable model. | **Resolved** — `save_finetuned_checkpoint()` assembles a complete checkpoint dir (config + hardlinked vocabs + spatial vocab + weights) atomically. `7cb9a6c` |
| 5.5 | **[CRITICAL] prepare_run has never executed on the remediated corpus — and would hard-fail today.** The only split_assignments.json/preparation_report.json on disk is the Aug-26 smoke run on 4 toy zebrafish files. Every "resolved" split/prepare fix (3.1, 3.2, 4.2) and stage re-mapping (2.2/2.3) is unvalidated on the real 27-dataset corpus; ADR 0003 gates training on a fresh re-validated prepare-only run. Moreover it would fail immediately: prepare.py:243 requires spatial_x/spatial_y obs for spatial datasets, no manifest obs_columns maps them, and for 3 of 5 files the coordinates don't even exist in obsm (1.12). | **Open** — coordinate-lift work must precede the prepare-only run. |
| 5.6 | **Checkpoint hardlink portability.** save_finetuned_checkpoint hardlinks vocab files; plain rsync/cp without -H duplicates them (disk bloat, not corruption — _link_or_copy falls back to copy). Note for the A40 rsync. | **Accepted** — operational note. |

## 6. Evaluation-harness validity

| # | Issue | Status |
|---|---|---|
| 6.1 | **Spatial checkpoints were unevaluatable (P2, eval half).** Evaluate never set up the `spatial_bin` aux vocab → strict load_state_dict crash. | **Resolved** — evaluate mirrors the spatial aux setup. `7cb9a6c` |
| 6.2 | **Spatial vs single-cell routed by assay string (P3).** Stereo-seq labeled "unknown" → spatial holdout files silently contaminated single-cell metrics. | **Resolved** — routing by manifest `dataset_type` from the preparation report (assay-heuristic fallback with warning). `7cb9a6c` |
| 6.3 | **Pseudotime metric was OOM-prone and meaningless (P8).** Dense n×n float64 kNN graph (~80 GB at 100k cells), one trajectory computed across species. | **Resolved** — sparse kNN pseudotime per group (species → embryo_id fallback), explicit stage ordering. `7cb9a6c` |
| 6.4 | **"Finetuned" could silently default to the base checkpoint (P9)** → base-vs-base comparison with zero deltas. | **Resolved** — evaluate CLI rejects base-as-finetuned, defaults output to the run's output_dir. `7cb9a6c` |
| 6.5 | **Pseudotime per-species grouping is dead code.** prepare.py never writes a `species` obs column, so evaluate always falls back to embryo_id; in the current holdout most groups are single-phase → Spearman = NaN and groups are silently dropped — the metric degenerates to a mean over the few multi-phase groups. | **Open** — write species into prepared obs during the prepare run. |
| 6.6 | **Spatial metrics pool spots across embryos/sections.** spatial_neighborhood_consistency and Moran's I build one kNN graph over all spatial files pooled — spots from different embryos/sections with similar coordinates become false neighbors (unlike the per-group pseudotime fix, 6.3). | **Open** |

## 7. Statistical and scientific validity of downstream claims

| # | Issue | Status |
|---|---|---|
| 7.1 | **No null model for likelihood-drop impact scores (S1).** Deleting a highly expressed gene removes more likelihood mass → rankings dominated by expression/detection rate, not regulatory importance. | **Designed (frozen)** — expression- and dropout-matched 10×10 quantile-bin permutation null per species × phase stratum, empirical p-values + z-scores, BH FDR q = 0.05 per stratum. Implementation pending (post-training analysis). |
| 7.2 | **"Known essentials rank high" validation is circular (S1).** Mouse-derived knowledge, mouse-heavy corpus (53%), memorized co-expression. | **Designed (frozen)** — 8 external falsification sets (MGI/IMPC, CRISPRz, FlyBase, WormBase RNAi, Jin 2020 Perturb-seq, gastruloid screens, Replogle negative control, urchin GRN); verdict rule: AUROC > 0.6, FDR < 0.05 in ≥ 2 **non-mouse** sets among {2,3,4} (CRISPRz / FlyBase / WormBase), and rankings not housekeeping-dominated. Mouse alone never counts. Maternal-mRNA caveat: zebrafish F0 crispants systematically bias against early-phase essentials (maternal deposition masks early-acting genes), so lower AUROC at early phases is expected and must be reported. |
| 7.3 | **No base-model control arm (S2).** Every headline analysis can run on the zero-shot base model; the marginal value of finetuning was never going to be measured. | **Designed (frozen)** — base-model baselines B1–B4 with pre-registered improvement criteria (≥ 5% holdout likelihood in ≥ 6/8 species with no species degrading > 2% (B1), ≥ 5-point phase-purity gain, ≤ 2-point probe degradation, ≤ 0.02 AUROC drop). If base already satisfies the claims, finetune is demoted to a robustness check. |
| 7.4 | **Catastrophic forgetting unmonitored (S3).** Embryo-holdout improvement measures domain adaptation, not retention of the zero-shot ability the probe evaluation depends on. | **Designed (frozen thresholds)** — frozen non-embryo reference set (CELLxGENE Census human/mouse adult + sponge/yeast canaries, optional Fly Cell Atlas), per-checkpoint likelihood delta + linear CKA, non-regression gate (3% / CKA 0.90) with a response ladder ending in the LoRA fallback. The canaries are only a tripwire for gross representational collapse (P. falciparum is in the model vocab but has no local dataset — design doc §4.1); the embryogenesis-relevant forgetting monitor is the B4 probe-species arm (see 7.3/B4). **Reference set not yet downloaded/built.** |
| 7.5 | **Causal language risk.** Likelihood impact is associational. | **Accepted with rule** — prohibited: "gene X drives/regulates phase P" without wet-lab/external-screen support; permitted: "top-ranked likelihood impact score (bin-null z = …, FDR q = …)". |
| 7.6 | **Tier-2 counterfactual validation scope.** Does counterfactual generation get validated against real perturbation data? | **Resolved (in scope)** — Jin et al. 2020 (35 ASD/ND risk genes, in-utero Perturb-seq): overlap of predicted downstream-affected genes with observed DE genes. User-approved 2026-09-09. |

## 8. Probe species and ESM2 embeddings

| # | Issue | Status |
|---|---|---|
| 8.1 | **Probe species are out-of-vocabulary.** Macaque, pig, guinea pig, Xenopus tropicalis, ciona, amphioxus are not TF-Metazoa vocab species → their genes have no learned token embeddings. | **Designed** — tokens built from ESM2 protein embeddings per `preprocess/fasta_manifest_pep.json`; pig and X. tropicalis embeddings are downloadable pre-generated; **macaque (*Macaca fascicularis*), guinea pig, ciona, and amphioxus must be generated locally** via `preprocess/protein_embedding.py` (not yet done — generation on this host is memory-constrained and must use chunked inference). Pre-generated ESM2 embeddings exist only for *M. mulatta* (a different species), so fascicularis embeddings genuinely need local generation; fasta_manifest_pep.json currently has NO entries for ciona, amphioxus, guinea pig, or *M. fascicularis* — entries must be added before protein_embedding.py can run (guinea pig had been silently dropped from the embedding plan and is now restored). |
| 8.2 | **Gene-level cross-species statements for probes need the same 1:1 ortholog table** (4.3); embedding-level comparisons do not. | **Designed** — shares the orthology framework of `docs/perturbation-and-baseline-design.md` §6 (not §6 of this register). |
| 8.3 | **[CRITICAL] Probe species have no stage→phase mapping — criterion B4 is unmeasurable as designed.** Probe datasets carry their own stage systems (pig E11.5–E15, amphioxus G4/N0/N2/N5, macaque CS/ME stages, xenopus NF stages) but `preprocess/stage_phase_mapping.md` covers only the 8 training species. The frozen improvement criterion "probe-species same-phase alignment degrades ≤ 2 points" (7.3/B4) requires per-cell probe phase labels that cannot currently be computed. | **Open** — extend the phase-mapping table to the 6 probe species (with the same citation discipline as 2.4). |

---

## Open items requiring a decision before training

1. **TOME E8.5b / mouse E8–P0** (1.2/1.11): keep excluded, or include only the E8–E13.5 window (if any part is included, E8.5b must be dropped first).
2. **[blocker] Spatial-coordinate parsing** (1.12) → rerun prepare-only and re-review split_assignments.json (5.5).
3. **[blocker] CS8 section-leakage fix** (3.9).
4. **Assay-vocab normalization** (1.14).
5. **Sampling-weighting decision** (3.8).
6. **Orthology table build** (4.3).
7. **Probe-species phase mapping** (8.3).
8. **Forgetting-reference-set build** (7.4).
9. **Fly per-cell phase assignment** (2.1).
10. **ESM2 generation** (8.1): add the `fasta_manifest_pep.json` entries first (macaque fascicularis / ciona / amphioxus / guinea pig), then run `protein_embedding.py` (chunked inference, memory-capped).
11. **Doublet/QC screen decision** (1.13).
12. **NaN-stage cell handling** (1.15).
13. **Nature2019 E4.5–E7.5** include or document exclusion (1.18).

*Compute-resource issues (gene-ID head VRAM, epoch time, bf16, WSL memory, A40 setup) are intentionally excluded here; see the C-findings in the adversarial review and ADR 0003 §compute.*
