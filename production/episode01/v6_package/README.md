# 第1集 V6 后续生成包

本目录是第1集下一轮生成的唯一入口。V4/V5素材已判定不允许直接复用。

## 文件

- `shot_manifest.json`：19个镜头、时长、连续状态、提示词文件和对白ID。
- `character_manifest.json`：四名角色的用户锁定参考图与不可变特征。
- `prop_manifest.json`：13项第一集道具参考图、使用镜头和连续性锁定规则。
- `scene_manifest.json`：1张陈家总平面母版和6张生产场景参考，对应镜头及固定空间关系。
- `dialogue_manifest.json`：唯一台词、说话方式和音轨政策。
- `sfx_manifest.json`：必须后期补齐并逐帧对齐的拟音。
- `storyboard_manifest.json`：五组连续故事板、角色/场景参考和尾帧衔接方式。
- `performance_manifest.json`：19个镜头的起始表情、表情变化、肢体动作终点和口型归属。
- `first_frame_manifest.json`：第一轮七张独立起始帧路径、验收状态及必须由前镜尾帧派生的镜头。
- `prompts/`：可提交给QuickRouter Seedance 1.5 Pro的逐镜提示词。

## 执行顺序

1. 先审核已锁定的四名角色参考图、13项道具参考图和7项场景参考。
2. 制作五组连续故事板；故事板只用于规划，19张干净9:16首帧必须逐镜单独生成，不得从多格图裁切。
3. 只生成连续性测试组：A03/A04、B01/B02、B06/B07/B08、C01/C02/C03。
4. 测试组连播通过后再生成其余镜头。
5. 对白镜头保留自身同步音轨；ASR或口型不通过就重生，不得换旧音轨。
6. 全部镜头通过后才制作字幕、证据文字和拟音。

Provider必须为QuickRouter；视频模型必须为 `doubao-seedance-1-5-pro-251215`。本目录不包含任何已提交任务，不会自行产生费用。

## 隔离目录

V6角色卡、场景、故事板和首帧只能写入 `assets/v6/`；视频、质检和成片只能写入 `production/episode01/v6_clips/`、`v6_qa/` 和 `v6_output/`。禁止重新创建或读取 `v2_*`、`v3_*`、`v4_*`、`v5_*` 目录。
