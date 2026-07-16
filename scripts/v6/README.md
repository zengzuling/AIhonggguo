# V6 脚本目录

当前目录为空白重建区。后续新增脚本必须满足：

1. 只读取 `production/episode01/v6_package/`。
2. 只向 `assets/v6/` 和 `production/episode01/v6_*` 写入。
3. Provider固定QuickRouter；视频模型固定 `doubao-seedance-1-5-pro-251215`。
4. 禁止出现火山官方API根地址、Agent Plan地址或自动回退逻辑。
5. 默认只做校验或dry-run；实际提交必须显式指定镜头ID。
6. 对白镜头不得替换音轨、变速、冻结或补帧。

## 前30秒视频生成

先检查全部请求，不调用接口：

```powershell
python scripts/v6/quickrouter_video.py dry-run --shots A01,A02,A03,A04,B01,B02,B03
```

实际提交必须逐镜显式指定，并增加费用确认开关：

```powershell
python scripts/v6/quickrouter_video.py submit --shot A03 --confirm-spend
python scripts/v6/quickrouter_video.py poll --shot A03 --download
```

镜头通过人物、动作、声音和口型验收后，才允许提取尾帧供后继镜头使用：

```powershell
python scripts/v6/quickrouter_video.py tail --shot A03
```

执行依赖见 `production/episode01/v6_package/first30_manifest.json`。脚本只读取
`QUICKROUTER_API_KEY`，不会读取或回退到火山官方密钥。

## 审核总览图

执行 `build_review_contact_sheets.py`，可从 V6 清单和锁定参考图生成角色、道具、场景三张审核总览图。输出目录固定为：

`production/episode01/v6_qa/reference_review/`

执行 `build_storyboard_review_sheets.py`，可把五组无文字故事板加工为带锁定引用、镜号、动作起终点和连续性闸门的正式审核版。输出目录固定为：

`assets/v6/storyboards/`

执行 `build_first_frame_review_sheet.py`，可生成第一轮七张独立起始帧的分类审核总览。输出目录固定为：

`production/episode01/v6_qa/first_frame_review/`
