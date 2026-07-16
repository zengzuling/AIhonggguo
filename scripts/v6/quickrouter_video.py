#!/usr/bin/env python3
"""通过 QuickRouter 顺序生成、查询并下载 V6 视频镜头。"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = PROJECT_ROOT / "production" / "episode01" / "v6_package"
FIRST30_MANIFEST = PACKAGE_DIR / "first30_manifest.json"
SHOT_MANIFEST = PACKAGE_DIR / "shot_manifest.json"
TASK_DIR = PROJECT_ROOT / "production" / "episode01" / "v6_qa" / "quickrouter_tasks"
CLIP_DIR = PROJECT_ROOT / "production" / "episode01" / "v6_clips"
TAIL_DIR = PROJECT_ROOT / "assets" / "v6" / "tail_frames"

API_ROOT = "https://api.quickrouter.ai/volc/v1/contents/generations/tasks"
UPLOAD_URL = "https://imageproxy.zhongzhuan.chat/api/upload"
MODEL = "doubao-seedance-1-5-pro-251215"
ALLOWED_SHOTS = (
    "A01", "A02", "A03", "A04",
    "B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08",
    "B09", "B10", "B11", "B12", "C01", "C02", "C03",
)
INPUT_OVERRIDES = {
    "B04": TAIL_DIR / "B03_tail.png",
    "B05": PROJECT_ROOT / "assets" / "v6" / "scenes" / "S02_1998红星机械厂仓库主机位_v1.png",
    "B06": PROJECT_ROOT / "assets" / "v6" / "first_frames" / "B06_first_frame_v1.png",
    "B07": PROJECT_ROOT / "assets" / "v6" / "first_frames" / "B07_first_frame_v1.png",
    "B08": PROJECT_ROOT / "assets" / "v6" / "first_frames" / "B08_first_frame_v1.png",
    "B09": TAIL_DIR / "B08_tail.png",
    "B10": TAIL_DIR / "B09_tail.png",
    "B11": TAIL_DIR / "B10_tail.png",
    "B12": TAIL_DIR / "B11_tail.png",
    "C01": PROJECT_ROOT / "assets" / "v6" / "first_frames" / "C01_first_frame_v1.png",
    "C02": PROJECT_ROOT / "assets" / "v6" / "first_frames" / "C02_first_frame_v1.png",
    "C03": TAIL_DIR / "C02_tail.png",
}
TERMINAL_SUCCESS = {"succeeded", "success", "completed", "done"}
TERMINAL_FAILURE = {"failed", "error", "cancelled", "canceled", "expired"}


def load_json(path: Path) -> dict[str, Any]:
    """以 UTF-8 读取 JSON 文件。"""
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    """以 UTF-8、无 ASCII 转义方式保存 JSON。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def api_key() -> str:
    """只读取 QuickRouter 密钥，明确拒绝其他供应商密钥回退。"""
    key = os.environ.get("QUICKROUTER_API_KEY", "").strip()
    if not key:
        raise RuntimeError("缺少环境变量 QUICKROUTER_API_KEY")
    return key


def request_json(url: str, method: str = "GET", payload: Any | None = None) -> dict[str, Any]:
    """调用 QuickRouter JSON 接口并返回对象。"""
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key()}",
        "Content-Type": "application/json",
    }
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"QuickRouter HTTP {error.code}: {detail}") from error


def upload_image(path: Path) -> str:
    """把本地起始帧上传到 QuickRouter 文档指定图床。"""
    boundary = f"----codex-{uuid.uuid4().hex}"
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    parts = [
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'.encode(),
        f"Content-Type: {mime}\r\n\r\n".encode(),
        path.read_bytes(),
        f"\r\n--{boundary}--\r\n".encode(),
    ]
    request = urllib.request.Request(
        UPLOAD_URL,
        data=b"".join(parts),
        headers={
            "Authorization": f"Bearer {api_key()}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"图床上传 HTTP {error.code}: {detail}") from error
    url = result.get("url")
    if not isinstance(url, str) or not url.startswith("https://"):
        raise RuntimeError(f"图床未返回有效 HTTPS 地址: {result}")
    return url


def first30_entries() -> dict[str, dict[str, Any]]:
    """返回前30秒镜头配置索引。"""
    manifest = load_json(FIRST30_MANIFEST)
    return {item["shot"]: item for item in manifest["timeline"]}


def shot_entries() -> dict[str, dict[str, Any]]:
    """返回全片镜头配置索引。"""
    manifest = load_json(SHOT_MANIFEST)
    return {item["id"]: item for item in manifest["shots"]}


def local_input_path(shot_id: str) -> Path:
    """解析独立起始帧或已通过前镜的尾帧路径。"""
    if shot_id in INPUT_OVERRIDES:
        return INPUT_OVERRIDES[shot_id]
    source = first30_entries()[shot_id]["input"]
    if "path" in source:
        return (PACKAGE_DIR / source["path"]).resolve()
    return TAIL_DIR / f"{source['from_shot']}_tail.png"


def prompt_text(shot_id: str) -> str:
    """读取单镜头锁定提示词。"""
    shot = shot_entries()[shot_id]
    return (PACKAGE_DIR / shot["prompt"]).read_text(encoding="utf-8").strip()


def build_payload(shot_id: str, image_url: str) -> dict[str, Any]:
    """构造 Seedance 1.5 图生视频请求体。"""
    duration = shot_entries()[shot_id]["generation_duration"]
    return {
        "model": MODEL,
        "content": [
            {"type": "text", "text": prompt_text(shot_id)},
            {"type": "image_url", "image_url": {"url": image_url}, "role": "first_frame"},
        ],
        "generate_audio": True,
        "ratio": "9:16",
        "duration": duration,
        "watermark": False,
    }


def parse_shots(raw: str) -> list[str]:
    """解析并校验显式镜头列表。"""
    shots = [item.strip().upper() for item in raw.split(",") if item.strip()]
    invalid = [shot for shot in shots if shot not in ALLOWED_SHOTS]
    if not shots or invalid:
        raise ValueError(f"镜头必须显式指定且仅限 {','.join(ALLOWED_SHOTS)}；无效值: {invalid}")
    return shots


def dry_run(shots: list[str]) -> None:
    """打印脱敏后的提交计划，不上传也不产生费用。"""
    for shot_id in shots:
        input_path = local_input_path(shot_id)
        print(json.dumps({
            "shot": shot_id,
            "input_path": str(input_path),
            "input_exists": input_path.is_file(),
            "endpoint": API_ROOT,
            "payload": build_payload(shot_id, "<uploaded-first-frame-url>"),
        }, ensure_ascii=False, indent=2))


def submit(shot_id: str, confirm_spend: bool) -> str:
    """上传起始帧并提交一个付费生成任务。"""
    if not confirm_spend:
        raise RuntimeError("实际提交必须增加 --confirm-spend")
    input_path = local_input_path(shot_id)
    if not input_path.is_file():
        raise FileNotFoundError(f"缺少起始帧，不能提交 {shot_id}: {input_path}")
    uploaded_url = upload_image(input_path)
    response = request_json(API_ROOT, method="POST", payload=build_payload(shot_id, uploaded_url))
    task_id = response.get("id")
    if not isinstance(task_id, str) or not task_id:
        raise RuntimeError(f"提交响应缺少任务 ID: {response}")
    save_json(TASK_DIR / f"{shot_id}.json", {
        "shot": shot_id,
        "task_id": task_id,
        "input_path": str(input_path),
        "uploaded_url": uploaded_url,
        "submit_response": response,
    })
    print(json.dumps({"shot": shot_id, "task_id": task_id, "status": response.get("status")}, ensure_ascii=False))
    return task_id


def task_id_for(shot_id: str) -> str:
    """读取镜头已保存的 QuickRouter 任务 ID。"""
    path = TASK_DIR / f"{shot_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"找不到 {shot_id} 的任务记录: {path}")
    return load_json(path)["task_id"]


def status_value(data: dict[str, Any]) -> str:
    """兼容读取常见任务状态字段。"""
    for key in ("status", "state", "task_status"):
        value = data.get(key)
        if isinstance(value, str):
            return value.lower()
    return "unknown"


def find_video_url(data: Any) -> str | None:
    """递归查找任务响应中的 MP4 或视频 URL。"""
    if isinstance(data, dict):
        for key in ("video_url", "url", "file_url", "download_url"):
            value = data.get(key)
            if isinstance(value, str) and value.startswith("http") and (".mp4" in value or "video" in key):
                return value
        for value in data.values():
            found = find_video_url(value)
            if found:
                return found
    elif isinstance(data, list):
        for value in data:
            found = find_video_url(value)
            if found:
                return found
    return None


def poll(shot_id: str, interval: int, timeout: int) -> dict[str, Any]:
    """轮询一个任务直到成功、失败或超时。"""
    task_id = task_id_for(shot_id)
    deadline = time.monotonic() + timeout
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last = request_json(f"{API_ROOT}/{task_id}")
        state = status_value(last)
        print(json.dumps({"shot": shot_id, "task_id": task_id, "status": state}, ensure_ascii=False), flush=True)
        record_path = TASK_DIR / f"{shot_id}.json"
        record = load_json(record_path)
        record["latest_response"] = last
        save_json(record_path, record)
        if state in TERMINAL_SUCCESS or find_video_url(last):
            return last
        if state in TERMINAL_FAILURE:
            raise RuntimeError(f"{shot_id} 生成失败: {last}")
        time.sleep(interval)
    raise TimeoutError(f"{shot_id} 在 {timeout} 秒内未完成，最后响应: {last}")


def download(shot_id: str, result: dict[str, Any] | None = None) -> Path:
    """下载已完成任务的视频文件。"""
    if result is None:
        record = load_json(TASK_DIR / f"{shot_id}.json")
        result = record.get("latest_response") or request_json(f"{API_ROOT}/{record['task_id']}")
    url = find_video_url(result)
    if not url:
        raise RuntimeError(f"{shot_id} 响应中没有视频地址: {result}")
    CLIP_DIR.mkdir(parents=True, exist_ok=True)
    output = CLIP_DIR / f"{shot_id}_generated.mp4"
    request = urllib.request.Request(url, headers={"User-Agent": "Codex-V6/1.0"})
    with urllib.request.urlopen(request, timeout=300) as response, output.open("wb") as target:
        while chunk := response.read(1024 * 1024):
            target.write(chunk)
    print(str(output))
    return output


def extract_tail(shot_id: str) -> Path:
    """从已下载视频末尾前0.2秒提取后继镜头起始帧。"""
    clip = CLIP_DIR / f"{shot_id}_generated.mp4"
    if not clip.is_file():
        raise FileNotFoundError(f"缺少视频，不能提取尾帧: {clip}")
    TAIL_DIR.mkdir(parents=True, exist_ok=True)
    output = TAIL_DIR / f"{shot_id}_tail.png"
    command = [
        "ffmpeg", "-y", "-sseof", "-0.2", "-i", str(clip),
        "-frames:v", "1", "-vf", "scale=941:1672:force_original_aspect_ratio=decrease,pad=941:1672:(ow-iw)/2:(oh-ih)/2",
        str(output),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if completed.returncode != 0 or not output.is_file():
        raise RuntimeError(f"ffmpeg 提取尾帧失败: {completed.stderr[-2000:]}")
    print(str(output))
    return output


def main() -> int:
    """命令行入口。"""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    dry_parser = subparsers.add_parser("dry-run", help="打印计划，不调用接口")
    dry_parser.add_argument("--shots", required=True, help="逗号分隔的显式镜头 ID")

    submit_parser = subparsers.add_parser("submit", help="提交一个付费任务")
    submit_parser.add_argument("--shot", required=True, choices=ALLOWED_SHOTS)
    submit_parser.add_argument("--confirm-spend", action="store_true")

    poll_parser = subparsers.add_parser("poll", help="轮询已提交任务")
    poll_parser.add_argument("--shot", required=True, choices=ALLOWED_SHOTS)
    poll_parser.add_argument("--interval", type=int, default=15)
    poll_parser.add_argument("--timeout", type=int, default=1800)
    poll_parser.add_argument("--download", action="store_true")

    download_parser = subparsers.add_parser("download", help="下载已完成视频")
    download_parser.add_argument("--shot", required=True, choices=ALLOWED_SHOTS)

    tail_parser = subparsers.add_parser("tail", help="提取已通过镜头的尾帧")
    tail_parser.add_argument("--shot", required=True, choices=ALLOWED_SHOTS)

    args = parser.parse_args()
    if args.command == "dry-run":
        dry_run(parse_shots(args.shots))
    elif args.command == "submit":
        submit(args.shot, args.confirm_spend)
    elif args.command == "poll":
        result = poll(args.shot, args.interval, args.timeout)
        if args.download:
            download(args.shot, result)
    elif args.command == "download":
        download(args.shot)
    elif args.command == "tail":
        extract_tail(args.shot)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, FileNotFoundError, TimeoutError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
