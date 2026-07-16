"""生成第 1 集 V6 锁定素材审核总览图。"""

from __future__ import annotations

import json
import math
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = ROOT / "production" / "episode01" / "v6_package"
OUTPUT_DIR = ROOT / "production" / "episode01" / "v6_qa" / "reference_review"
FONT_PATH = Path(r"C:\Windows\Fonts\msyh.ttc")

BACKGROUND = "#0D1117"
PANEL = "#161B22"
PANEL_ALT = "#1C2430"
TEXT = "#F0F3F6"
MUTED = "#A9B4C2"
ACCENT = "#56D6C9"
WARNING = "#F0B45A"
LINE = "#303A46"


def load_json(name: str) -> dict:
    """按 UTF-8 读取制作包清单。"""
    return json.loads((PACKAGE_DIR / name).read_text(encoding="utf-8"))


def font(size: int) -> ImageFont.FreeTypeFont:
    """统一使用微软雅黑，保证中文标注可读。"""
    return ImageFont.truetype(str(FONT_PATH), size=size)


def fit_image(source: Image.Image, box: tuple[int, int]) -> Image.Image:
    """保持原图比例缩放，并居中放入深色画布。"""
    width, height = box
    image = source.convert("RGB")
    image.thumbnail((width, height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", box, "#090C10")
    x = (width - image.width) // 2
    y = (height - image.height) // 2
    canvas.paste(image, (x, y))
    return canvas


def wrap_cn(text: str, max_chars: int) -> list[str]:
    """按中文字符宽度近似换行，避免审核说明溢出卡片。"""
    return textwrap.wrap(
        text,
        width=max_chars,
        break_long_words=True,
        break_on_hyphens=False,
    )


def draw_header(
    draw: ImageDraw.ImageDraw,
    title: str,
    subtitle: str,
    width: int,
) -> int:
    """绘制审核图统一页眉并返回内容起始坐标。"""
    draw.text((80, 54), title, fill=TEXT, font=font(54))
    draw.text((82, 124), subtitle, fill=MUTED, font=font(24))
    draw.line((80, 176, width - 80, 176), fill=LINE, width=2)
    return 210


def draw_card(
    canvas: Image.Image,
    xy: tuple[int, int],
    size: tuple[int, int],
    image_path: Path,
    label: str,
    details: list[str],
    badge: str,
    badge_color: str = ACCENT,
) -> None:
    """绘制一张包含原图、编号、状态与锁定说明的审核卡片。"""
    x, y = xy
    width, height = size
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(
        (x, y, x + width, y + height), radius=20, fill=PANEL, outline=LINE, width=2
    )

    image_margin = 18
    text_height = max(190, int(height * 0.28))
    image_box = (width - image_margin * 2, height - text_height - image_margin * 2)
    with Image.open(image_path) as source:
        preview = fit_image(source, image_box)
    canvas.paste(preview, (x + image_margin, y + image_margin))

    text_y = y + height - text_height + 14
    draw.text((x + 22, text_y), label, fill=TEXT, font=font(28))

    badge_font = font(20)
    badge_box = draw.textbbox((0, 0), badge, font=badge_font)
    badge_width = badge_box[2] - badge_box[0] + 24
    badge_x = x + width - badge_width - 22
    draw.rounded_rectangle(
        (badge_x, text_y + 2, badge_x + badge_width, text_y + 34),
        radius=16,
        fill=badge_color,
    )
    draw.text((badge_x + 12, text_y + 5), badge, fill="#08110F", font=badge_font)

    detail_y = text_y + 49
    detail_font = font(20)
    max_chars = max(18, int((width - 44) / 21))
    for detail in details:
        for line in wrap_cn(detail, max_chars):
            if detail_y + 28 > y + height - 12:
                return
            draw.text((x + 22, detail_y), line, fill=MUTED, font=detail_font)
            detail_y += 28


def create_sheet(
    filename: str,
    title: str,
    subtitle: str,
    cards: list[dict],
    columns: int,
    width: int,
    card_height: int,
) -> Path:
    """根据卡片数量自动计算画布高度并输出 PNG。"""
    side = 80
    gap = 24
    rows = math.ceil(len(cards) / columns)
    card_width = (width - side * 2 - gap * (columns - 1)) // columns
    top = 210
    height = top + rows * card_height + (rows - 1) * gap + 80
    canvas = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    draw_header(draw, title, subtitle, width)

    for index, card in enumerate(cards):
        row, column = divmod(index, columns)
        x = side + column * (card_width + gap)
        y = top + row * (card_height + gap)
        draw_card(canvas, (x, y), (card_width, card_height), **card)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / filename
    canvas.save(output, format="PNG", optimize=True)
    return output


def character_cards() -> list[dict]:
    """从角色清单构建四张用户锁定角色卡。"""
    manifest = load_json("character_manifest.json")
    cards = []
    for item in manifest["characters"]:
        path = (PACKAGE_DIR / item["reference"]).resolve()
        cards.append(
            {
                "image_path": path,
                "label": f'{item["id"]} · {item["name"]}',
                "details": [
                    f'年龄：{item["age"]}岁；{item["appearance"]}',
                    f'服装锁定：{item["wardrobe"]}',
                ],
                "badge": "用户锁定",
            }
        )
    return cards


def prop_cards() -> list[dict]:
    """从道具清单构建十三张结构审核卡。"""
    manifest = load_json("prop_manifest.json")
    base = (PACKAGE_DIR / manifest["base_path"]).resolve()
    return [
        {
            "image_path": base / item["reference"],
            "label": f'{item["id"]} · {item["name"]}',
            "details": [item["lock"]],
            "badge": "结构锁定",
        }
        for item in manifest["props"]
    ]


def scene_cards() -> list[dict]:
    """构建七张生产场景卡，并追加一张用户空间参考卡。"""
    manifest = load_json("scene_manifest.json")
    base = (PACKAGE_DIR / manifest["base_path"]).resolve()
    cards: list[dict] = []
    for item in manifest["scenes"]:
        cards.append(
            {
                "image_path": base / item["reference"],
                "label": f'{item["id"]} · {item["name"]}',
                "details": [f'用于镜头：{", ".join(item["shots"])}', item["lock"]],
                "badge": "待视觉确认",
            }
        )
        if item["id"] == "S98_HOUSE":
            cards.append(
                {
                    "image_path": base / item["source_reference"],
                    "label": "S98_LAYOUT · 陈家总平面用户参考",
                    "details": ["仅用于校验空间关系，不直接作为视频生产场景。"],
                    "badge": "辅助参考",
                    "badge_color": WARNING,
                }
            )
    return cards


def main() -> None:
    """生成三张分类审核总览图。"""
    outputs = [
        create_sheet(
            "01_角色锁定审核总览.png",
            "第 1 集 V6｜角色锁定审核",
            "4 张用户锁定参考图 · 审核脸型、年龄、发型、服装与体型",
            character_cards(),
            columns=2,
            width=3200,
            card_height=1080,
        ),
        create_sheet(
            "02_道具锁定审核总览.png",
            "第 1 集 V6｜道具结构审核",
            "13 项道具参考图 · 审核数量、结构、颜色及跨镜连续性",
            prop_cards(),
            columns=4,
            width=3840,
            card_height=760,
        ),
        create_sheet(
            "03_场景锁定审核总览.png",
            "第 1 集 V6｜场景空间审核",
            "7 张生产场景 + 1 张用户空间参考 · 审核门、床、桌、机位与人物路径",
            scene_cards(),
            columns=4,
            width=3840,
            card_height=900,
        ),
    ]
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
