"""把五组无文字故事板加工为可审核的正式规划版。"""

from __future__ import annotations

import json
import math
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = ROOT / "production" / "episode01" / "v6_package"
STORYBOARD_DIR = ROOT / "assets" / "v6" / "storyboards"
FONT_PATH = Path(r"C:\Windows\Fonts\msyh.ttc")

WIDTH = 3840
SIDE = 80
BACKGROUND = "#0D1117"
PANEL = "#161B22"
TEXT = "#F0F3F6"
MUTED = "#A9B4C2"
ACCENT = "#56D6C9"
LINE = "#303A46"


GROUP_REFERENCES = {
    "SB-A": {"roles": ["R04"], "scenes": ["S28_M1", "S28_M2"]},
    "SB-B": {"roles": ["R01"], "scenes": ["S98_HOUSE", "S98_M1", "S02"]},
    "SB-C": {"roles": ["R01", "R02"], "scenes": ["S98_HOUSE", "S98_M2"]},
    "SB-D": {"roles": ["R01", "R02"], "scenes": ["S98_HOUSE", "S98_M2"]},
    "SB-E": {"roles": ["R01", "R02", "R03"], "scenes": ["S98_ST", "S98_M2"]},
}


CHECK_LABELS = {
    "same_art_style": "统一写实画风",
    "same_old_face": "老人身份一致",
    "stool_visible_A03_A04": "A03/A04木凳可见",
    "fall_once": "只倒地一次",
    "wake_once": "只醒来一次",
    "same_bed": "同一张床",
    "open_room_no_bedroom_door": "开放主屋无卧室门",
    "continuous_walk_bed_to_calendar": "床到日历路径连续",
    "no_portrait_slideshow": "无遗像幻灯片",
    "brown_front_door_only": "只用棕色入户门",
    "enter_once": "父亲只进门一次",
    "lunchbox_right_hand": "饭盒持有手连续",
    "D08_before_hug_and_D09": "D08在拥抱与D09前",
    "one_lunchbox": "唯一饭盒",
    "one_iou": "唯一欠条",
    "no_sitting_teleport": "无坐姿瞬移",
    "sleeve_grab_continuous": "抓袖动作连续",
    "one_short_breath": "一次短喘",
    "two_knocks": "两次敲门",
    "one_door_open": "只开门一次",
    "one_entry": "老刘只进门一次",
    "one_shift_sheet": "唯一排班纸",
    "D14_complete": "D14完整结束",
}


def load_json(name: str) -> dict:
    """读取 V6 制作包清单。"""
    return json.loads((PACKAGE_DIR / name).read_text(encoding="utf-8"))


def font(size: int) -> ImageFont.FreeTypeFont:
    """统一使用微软雅黑，避免中文乱码。"""
    return ImageFont.truetype(str(FONT_PATH), size=size)


def wrap(text: str, width: int) -> list[str]:
    """按字符数换行，保证动作说明不越界。"""
    return textwrap.wrap(text, width=width, break_long_words=True, break_on_hyphens=False)


def draw_reference_card(
    canvas: Image.Image,
    x: int,
    y: int,
    width: int,
    height: int,
    image_path: Path,
    label: str,
) -> None:
    """绘制角色或场景锁定引用缩略卡。"""
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((x, y, x + width, y + height), 16, fill=PANEL, outline=LINE, width=2)
    with Image.open(image_path) as source:
        preview = ImageOps.contain(source.convert("RGB"), (width - 24, height - 78))
    px = x + (width - preview.width) // 2
    py = y + 12 + (height - 78 - preview.height) // 2
    canvas.paste(preview, (px, py))
    draw.text((x + 16, y + height - 50), label, fill=TEXT, font=font(23))


def build_reference_maps() -> tuple[dict, dict]:
    """建立角色与场景编号到锁定图片的映射。"""
    characters = load_json("character_manifest.json")
    character_map = {
        item["id"]: {
            "name": item["name"],
            "path": (PACKAGE_DIR / item["reference"]).resolve(),
        }
        for item in characters["characters"]
    }

    scenes = load_json("scene_manifest.json")
    base = (PACKAGE_DIR / scenes["base_path"]).resolve()
    scene_map = {
        item["id"]: {"name": item["name"], "path": base / item["reference"]}
        for item in scenes["scenes"]
    }
    return character_map, scene_map


def create_review_sheet(group: dict, shot_map: dict, character_map: dict, scene_map: dict) -> Path:
    """为单组故事板生成包含引用与动作说明的审核版。"""
    group_id = group["id"]
    refs = GROUP_REFERENCES[group_id]
    raw_path = next(STORYBOARD_DIR.glob(f"{group_id}_连续故事板_v*.png"))
    with Image.open(raw_path) as source:
        raw = source.convert("RGB")

    header_height = 190
    reference_height = 420
    storyboard_width = WIDTH - SIDE * 2
    storyboard_height = round(raw.height * storyboard_width / raw.width)
    notes_height = 440
    footer_height = 120
    total_height = header_height + reference_height + storyboard_height + notes_height + footer_height
    canvas = Image.new("RGB", (WIDTH, total_height), BACKGROUND)
    draw = ImageDraw.Draw(canvas)

    draw.text((SIDE, 42), f"{group_id}｜第 1 集 V6 连续故事板审核版", fill=TEXT, font=font(54))
    chain_text = "；".join(group.get("direct_tail_chains", []) + group.get("state_transfer_chains", []))
    draw.text((SIDE + 2, 116), f"镜头：{' / '.join(group['shots'])}　连续链：{chain_text}", fill=MUTED, font=font(25))
    draw.line((SIDE, 168, WIDTH - SIDE, 168), fill=LINE, width=2)

    ref_items = []
    for role_id in refs["roles"]:
        item = character_map[role_id]
        ref_items.append((item["path"], f"角色 {role_id} · {item['name']}"))
    for scene_id in refs["scenes"]:
        item = scene_map[scene_id]
        ref_items.append((item["path"], f"场景 {scene_id} · {item['name']}"))

    card_gap = 22
    card_width = min(700, (storyboard_width - card_gap * (len(ref_items) - 1)) // len(ref_items))
    cards_width = card_width * len(ref_items) + card_gap * (len(ref_items) - 1)
    card_x = SIDE + (storyboard_width - cards_width) // 2
    card_y = header_height + 10
    for index, (path, label) in enumerate(ref_items):
        draw_reference_card(canvas, card_x + index * (card_width + card_gap), card_y, card_width, 380, path, label)

    storyboard_y = header_height + reference_height
    storyboard = raw.resize((storyboard_width, storyboard_height), Image.Resampling.LANCZOS)
    canvas.paste(storyboard, (SIDE, storyboard_y))

    panel_count = len(group["shots"])
    panel_width = storyboard_width / panel_count
    for index, shot_id in enumerate(group["shots"]):
        x = round(SIDE + index * panel_width)
        draw.rounded_rectangle((x + 16, storyboard_y + 16, x + 142, storyboard_y + 70), 12, fill="#0D1117DD")
        draw.text((x + 34, storyboard_y + 25), shot_id, fill=ACCENT, font=font(30))

    notes_y = storyboard_y + storyboard_height + 24
    note_gap = 18
    note_width = (storyboard_width - note_gap * (panel_count - 1)) // panel_count
    for index, shot_id in enumerate(group["shots"]):
        shot = shot_map[shot_id]
        x = SIDE + index * (note_width + note_gap)
        draw.rounded_rectangle((x, notes_y, x + note_width, notes_y + 390), 16, fill=PANEL, outline=LINE, width=2)
        draw.text((x + 18, notes_y + 16), f"{shot_id} · {shot['duration']}秒", fill=TEXT, font=font(28))
        y = notes_y + 64
        for prefix, content in (("起点", shot["start_state"]), ("终点", shot["end_state"])):
            draw.text((x + 18, y), f"{prefix}：", fill=ACCENT, font=font(21))
            y += 32
            max_chars = max(12, math.floor((note_width - 36) / 23))
            for line in wrap(content, max_chars):
                draw.text((x + 18, y), line, fill=MUTED, font=font(21))
                y += 30
            y += 10

    checks = [CHECK_LABELS.get(item, item) for item in group["critical_checks"]]
    draw.text((SIDE, total_height - 82), "连续性闸门：" + " ｜ ".join(checks), fill=ACCENT, font=font(24))
    draw.text((WIDTH - 530, total_height - 82), "规划图禁止直接提交视频模型", fill=MUTED, font=font(22))

    output = STORYBOARD_DIR / f"{group_id}_连续故事板_审核版_v1.png"
    canvas.save(output, optimize=True)
    return output


def main() -> None:
    """生成五组正式故事板审核图。"""
    storyboard_manifest = load_json("storyboard_manifest.json")
    shot_manifest = load_json("shot_manifest.json")
    shot_map = {item["id"]: item for item in shot_manifest["shots"]}
    character_map, scene_map = build_reference_maps()
    for group in storyboard_manifest["groups"]:
        print(create_review_sheet(group, shot_map, character_map, scene_map))


if __name__ == "__main__":
    main()
