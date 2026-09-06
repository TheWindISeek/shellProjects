#!/usr/bin/env python3
"""下载网易云「听歌排行」里的歌曲到本地 music/ 目录。

原理：直接调用前端点击播放时用的后端接口，而不是真的开浏览器点：
  1. /api/v1/play/record          —— 拉取听歌排行歌单
  2. /api/song/enhance/player/url/v1 —— 拿可直链下载的 m4a/mp3 地址

部分 VIP/版权歌曲未登录会拿不到链接。可从浏览器复制 MUSIC_U cookie：
  登录 music.163.com -> F12 -> Application -> Cookies -> MUSIC_U
  然后：
    python3 download_netease_rank.py --cookie '你的MUSIC_U值'
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import requests

DEFAULT_UID = 1493188292
API_RECORD = "https://music.163.com/api/v1/play/record"
API_URL_V1 = "https://music.163.com/api/song/enhance/player/url/v1"
API_URL = "https://music.163.com/api/song/enhance/player/url"

# VIP 链常落在 m704/m804，带 authSecret 时 CDN 会 403；这些备用节点更稳
CDN_FALLBACK_HOSTS = (
    "m701.music.126.net",
    "m801.music.126.net",
    "m7.music.126.net",
    "m10.music.126.net",
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://music.163.com/",
    "Origin": "https://music.163.com",
}

INVALID_FS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def sanitize_filename(name: str, max_len: int = 120) -> str:
    name = INVALID_FS.sub("_", name).strip(" .")
    return (name or "unknown")[:max_len]


def song_display_name(song: dict[str, Any]) -> str:
    title = song.get("name") or f"id_{song.get('id')}"
    artists = song.get("ar") or song.get("artists") or []
    artist = "、".join(a.get("name", "") for a in artists if a.get("name"))
    return f"{title} - {artist}" if artist else title


def make_session(cookie: str | None) -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    if cookie:
        # 支持整段 Cookie，或只贴 MUSIC_U 值
        if "=" in cookie and ";" in cookie:
            session.headers["Cookie"] = cookie
        elif cookie.startswith("MUSIC_U="):
            session.headers["Cookie"] = cookie
        else:
            session.headers["Cookie"] = f"MUSIC_U={cookie}"
    return session


def fetch_rank(session: requests.Session, uid: int, week: bool) -> list[dict[str, Any]]:
    # type=-1 全部，type=1 近一周
    resp = session.get(
        API_RECORD,
        params={"uid": uid, "type": 1 if week else -1},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") not in (200, None) and data.get("code") != 200:
        # 隐私排行等情况下 code 可能不是 200
        if data.get("code") == -2:
            raise RuntimeError("该用户听歌排行设置为隐私，无法拉取。")
        if "allData" not in data and "weekData" not in data:
            raise RuntimeError(f"拉取听歌排行失败: {data}")

    songs = data.get("weekData" if week else "allData") or data.get("allData") or data.get("weekData") or []
    if not songs:
        raise RuntimeError("听歌排行为空，或接口未返回数据（可能需要登录 cookie）。")
    return songs


def fetch_play_url(session: requests.Session, song_id: int) -> tuple[str | None, str]:
    """返回 (url, ext)。优先 aac/m4a，失败再回退 mp3。"""
    # 与网页播放器类似：level + encodeType=aac -> 多为 m4a
    for level in ("exhigh", "higher", "standard"):
        resp = session.get(
            API_URL_V1,
            params={
                "ids": f"[{song_id}]",
                "level": level,
                "encodeType": "aac",
            },
            timeout=30,
        )
        resp.raise_for_status()
        item = (resp.json().get("data") or [{}])[0]
        url = item.get("url")
        if url:
            ext = (item.get("type") or "m4a").lower()
            if ext == "aac":
                ext = "m4a"
            return url, ext

    resp = session.get(
        API_URL,
        params={"ids": f"[{song_id}]", "br": 320000},
        timeout=30,
    )
    resp.raise_for_status()
    item = (resp.json().get("data") or [{}])[0]
    url = item.get("url")
    if url:
        ext = (item.get("type") or "mp3").lower()
        return url, ext
    return None, ""


def unique_path(directory: Path, stem: str, ext: str) -> Path:
    path = directory / f"{stem}.{ext}"
    if not path.exists():
        return path
    i = 2
    while True:
        path = directory / f"{stem} ({i}).{ext}"
        if not path.exists():
            return path
        i += 1


def cdn_url_candidates(url: str) -> list[str]:
    """生成可尝试的 CDN 地址。

    近年 VIP 音源返回的 m704/m804 链接带 vuutv/authSecret，
    直接请求常被 CDN 判 auth failed (403)。去掉查询参数或换节点即可下。
    """
    parts = urlsplit(url)
    host = parts.hostname or ""
    candidates: list[str] = []

    def add(scheme: str, netloc: str, path: str, query: str = "") -> None:
        candidates.append(urlunsplit((scheme, netloc, path, query, "")))

    # 优先：原 host 去防盗链参数
    add(parts.scheme, parts.netloc, parts.path)
    # 备用节点 + 去参数
    for h in CDN_FALLBACK_HOSTS:
        if h != host:
            add(parts.scheme, h, parts.path)
    # 再试带参数的备用节点 / 原始完整 URL
    for h in CDN_FALLBACK_HOSTS:
        if h != host:
            add(parts.scheme, h, parts.path, parts.query)
    add(parts.scheme, parts.netloc, parts.path, parts.query)

    # 保序去重
    seen: set[str] = set()
    out: list[str] = []
    for u in candidates:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def download_file(url: str, dest: Path) -> str:
    """下载音频，返回实际成功的 URL。不携带登录 Cookie，避免干扰 CDN。"""
    headers = {
        "User-Agent": HEADERS["User-Agent"],
        "Referer": "https://music.163.com/",
        "Accept": "*/*",
    }
    last_err: Exception | None = None
    tmp = dest.with_suffix(dest.suffix + ".part")

    for candidate in cdn_url_candidates(url):
        try:
            with requests.get(
                candidate, headers=headers, stream=True, timeout=120
            ) as resp:
                if resp.status_code != 200:
                    last_err = RuntimeError(
                        f"HTTP {resp.status_code} for {candidate[:80]}"
                    )
                    continue
                ctype = (resp.headers.get("content-type") or "").lower()
                # 403/错误页有时也会 200 返回极小 html
                first = next(resp.iter_content(chunk_size=64 * 1024), b"")
                if not first or first[:15].lstrip().startswith(
                    (b"<!DOCTYPE", b"<html", b"{")
                ):
                    last_err = RuntimeError(f"非音频响应: {candidate[:80]}")
                    continue
                if "text/html" in ctype and b"ftyp" not in first[:32]:
                    last_err = RuntimeError(f"HTML 响应: {candidate[:80]}")
                    continue

                with tmp.open("wb") as f:
                    f.write(first)
                    for chunk in resp.iter_content(chunk_size=256 * 1024):
                        if chunk:
                            f.write(chunk)

                if tmp.stat().st_size < 10_000:
                    tmp.unlink(missing_ok=True)
                    last_err = RuntimeError(f"文件过小: {candidate[:80]}")
                    continue

                tmp.replace(dest)
                return candidate
        except Exception as e:
            last_err = e
            tmp.unlink(missing_ok=True)
            continue

    raise RuntimeError(f"所有 CDN 候选均失败: {last_err}")


def already_downloaded(directory: Path, stem: str) -> Path | None:
    for ext in ("m4a", "mp3", "flac", "aac"):
        path = directory / f"{stem}.{ext}"
        if path.exists() and path.stat().st_size > 0:
            return path
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="下载网易云听歌排行歌曲")
    parser.add_argument("--uid", type=int, default=DEFAULT_UID, help="用户 uid")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent / "music",
        help="保存目录，默认 ./music",
    )
    parser.add_argument("--week", action="store_true", help="只下近一周排行（默认全部）")
    parser.add_argument(
        "--cookie",
        default=None,
        help="MUSIC_U 值，或整段 Cookie。VIP/版权曲需要登录态",
    )
    parser.add_argument("--limit", type=int, default=0, help="最多下载 N 首，0 表示全部")
    parser.add_argument("--delay", type=float, default=0.35, help="每首间隔秒数，降低风控")
    parser.add_argument("--overwrite", action="store_true", help="已存在同名文件也重新下")
    args = parser.parse_args()

    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    session = make_session(args.cookie)
    # 拿一份 __csrf 等站点 cookie，部分账号态接口更稳
    try:
        session.get("https://music.163.com/", timeout=20)
    except Exception:
        pass

    print(f"拉取听歌排行 uid={args.uid} ({'近一周' if args.week else '全部'}) ...")
    records = fetch_rank(session, args.uid, args.week)
    if args.limit > 0:
        records = records[: args.limit]
    print(f"共 {len(records)} 首，保存到 {out_dir}")

    ok = skip = fail = 0
    for idx, record in enumerate(records, 1):
        song = record.get("song") or record
        song_id = song["id"]
        display = song_display_name(song)
        stem = sanitize_filename(display)

        if not args.overwrite:
            existed = already_downloaded(out_dir, stem)
            if existed:
                print(f"[{idx}/{len(records)}] 跳过已存在: {existed.name}")
                skip += 1
                continue

        try:
            url, ext = fetch_play_url(session, song_id)
        except Exception as e:
            print(f"[{idx}/{len(records)}] 获取链接失败: {display} -> {e}")
            fail += 1
            continue

        if not url:
            print(
                f"[{idx}/{len(records)}] 无可用链接（可能需 VIP/登录）: {display}"
            )
            fail += 1
            time.sleep(args.delay)
            continue

        dest = unique_path(out_dir, stem, ext)
        try:
            print(f"[{idx}/{len(records)}] 下载 {dest.name} ...")
            used = download_file(url, dest)
            size_mb = dest.stat().st_size / (1024 * 1024)
            print(f"    完成 {size_mb:.2f} MB  <- {used[:80]}...")
            ok += 1
        except Exception as e:
            print(f"[{idx}/{len(records)}] 下载失败: {display} -> {e}")
            part = dest.with_suffix(dest.suffix + ".part")
            part.unlink(missing_ok=True)
            if dest.exists():
                dest.unlink(missing_ok=True)
            fail += 1

        time.sleep(args.delay)

    print(f"\n完成: 成功 {ok}，跳过 {skip}，失败 {fail}")
    if fail and not args.cookie:
        print(
            "提示: 失败里不少是 VIP/版权曲。登录网页后复制 MUSIC_U，再加 --cookie 重试。"
        )
    return 0 if ok or skip else 1


if __name__ == "__main__":
    sys.exit(main())
