# V6 脚本目录

当前目录为空白重建区。后续新增脚本必须满足：

1. 只读取 `production/episode01/v6_package/`。
2. 只向 `assets/v6/` 和 `production/episode01/v6_*` 写入。
3. Provider固定QuickRouter；视频模型固定 `doubao-seedance-1-5-pro-251215`。
4. 禁止出现火山官方API根地址、Agent Plan地址或自动回退逻辑。
5. 默认只做校验或dry-run；实际提交必须显式指定镜头ID。
6. 对白镜头不得替换音轨、变速、冻结或补帧。
