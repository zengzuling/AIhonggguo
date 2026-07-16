"""生成第一轮七张独立起始帧的审核总览图。"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "assets" / "v6" / "first_frames"
OUTPUT_DIR = ROOT / "production" / "episode01" / "v6_qa" / "first_frame_review"
FONT_PATH = Path(r"C:\Windows\Fonts\msyh.ttc")

SHOT_IDS = ["A03", "B01", "B06", "B07", "B08", "C01", "C02"]
SHOT_LABELS = {
    "A03": "疲惫专注 / 胸痛前",
    "B01": "完全躺卧 / 惊醒前",
    "B06": "父亲现身 / 进门起点",
    "B07": "震惊确认 / 说话前",
    "B08": "靠近完成 / 拥抱前",
    "C01": "上楼途中 / 敲门前",
    "C02": "开门起点 / 跨门前",
}


def font(size: int) -> ImageFont.FreeTypeFont:
    """统一使用微软雅黑输出中文标注。"""
    return ImageFont.truetype(str(FONT_PATH), size=size)


def main() -> None:
    """把七张首帧排成四列两行的审核总览。"""
    width = 3600
    side = 70
    gap = 24
    header = 180
    columns = 4
    card_width = (width - side * 2 - gap * (columns - 1)) // columns
    card_height = 1580
    rows = 2
    height = header + rows * card_height + gap + 70

    canvas = Image.new("RGB", (width, height), "#0D1117")
    draw = ImageDraw.Draw(canvas)
    draw.text((side, 40), "第 1 集 V6｜七张独立起始帧审核", fill="#F0F3F6", font=font(52))
    draw.text(
        (side + 2, 112),
        "逐镜单独生成 · 审核人物身份、起始表情、动作起点、手部与关键道具",
        fill="#A9B4C2",
        font=font(25),
    )

    for index, shot_id in enumerate(SHOT_IDS):
        row, column = divmod(index, columns)
        x = side + column * (card_width + gap)
        y = header + row * (card_height + gap)
        draw.rounded_rectangle(
            (x, y, x + card_width, y + card_height),
            radius=18,
            fill="#161B22",
            outline="#303A46",
            width=2,
        )
        source_path = SOURCE_DIR / f"{shot_id}_first_frame_v1.png"
        with Image.open(source_path) as source:
            preview = ImageOps.contain(
                source.convert("RGB"),
                (card_width - 30, card_height - 150),
                Image.Resampling.LANCZOS,
            )
        px = x + (card_width - preview.width) // 2
        py = y + 18
        canvas.paste(preview, (px, py))
        draw.text((x + 20, y + card_height - 112), shot_id, fill="#56D6C9", font=font(32))
        draw.text(
            (x + 20, y + card_height - 65),
            SHOT_LABELS[shot_id],
            fill="#A9B4C2",
            font=font(23),
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / "七张独立起始帧审核总览_v1.png"
    canvas.save(output, optimize=True)
    print(output)


if __name__ == "__main__":
    main()
