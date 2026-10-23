#!/usr/bin/env python3
"""
version_tool.py
产品开发 Skill 四段式版本号自主生成与解析工具。
支持格式：v[主版本].[需求版本].[修复版本].[打包版本] (vMAJOR.FEATURE.PATCH.BUILD)
打包版本（BUILD）优先自主生成时间戳格式：MMddHHmmss（10位月日时分秒）。
支持多端包区分后缀（如 +web, +apk, +ipa, +desktop, +srv）。
无需依赖外部 CI/CD 流水线，本地自治生成。
"""

import re
import sys
import argparse
from datetime import datetime
from typing import Optional, Dict, Any


def generate_timestamp_build(dt: Optional[datetime] = None) -> str:
    """生成 10 位时间戳打包版本号：MMddHHmmss"""
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%m%d%H%M%S")


def format_version(
    major: int = 1,
    feature: int = 0,
    patch: int = 0,
    build: Optional[str] = None,
    client: Optional[str] = None,
    env_tier: Optional[str] = None,
) -> str:
    """
    组装四段式多级版本号。
    若未指定 build，则默认生成当前时间戳 MMddHHmmss。
    """
    b_val = str(build).strip() if build is not None else generate_timestamp_build()
    
    # 基础四段式
    ver = f"v{int(major)}.{int(feature)}.{int(patch)}.{b_val}"

    # 环境阶段标识 (如 -alpha, -beta, -rc.1)
    if env_tier:
        tier = env_tier.strip()
        if not tier.startswith("-") and not tier.startswith("."):
            ver += f"-{tier}"
        else:
            ver += tier

    # 客户端包区分后缀 (如 +web, +apk, +ipa, +desktop, +srv)
    if client:
        c_suffix = client.strip().lstrip("+")
        ver += f"+{c_suffix}"

    return ver


def parse_version(version_str: str) -> Dict[str, Any]:
    """
    解析四段式版本号。
    支持形式：
    - v1.2.0.1014172725
    - v1.2.0.1014172725+apk
    - v1.2.0.1014172725-beta+web
    """
    raw = version_str.strip()
    # 匹配核心正则
    pattern = r"^v?(\d+)\.(\d+)\.(\d+)\.([0-9a-zA-Z_-]+?)(?:[-.](alpha|beta|rc(?:\.\d+)?|ga|dev))?(?:\+([0-9a-zA-Z_-]+))?$"
    m = re.match(pattern, raw)
    if not m:
        # 兼容三段式兜底
        alt_pattern = r"^v?(\d+)\.(\d+)\.(\d+)(?:\+([0-9a-zA-Z_-]+))?$"
        alt_m = re.match(alt_pattern, raw)
        if alt_m:
            return {
                "raw": raw,
                "valid": True,
                "major": int(alt_m.group(1)),
                "feature": int(alt_m.group(2)),
                "patch": int(alt_m.group(3)),
                "build": "0",
                "env_tier": None,
                "client": alt_m.group(4),
                "is_timestamp_build": False,
            }
        return {"raw": raw, "valid": False, "error": "Invalid version format"}

    major = int(m.group(1))
    feature = int(m.group(2))
    patch = int(m.group(3))
    build = m.group(4)
    env_tier = m.group(5)
    client = m.group(6)

    # 检查 build 是否为 10 位时间戳 MMddHHmmss
    is_timestamp = bool(re.match(r"^\d{10}$", build))

    return {
        "raw": raw,
        "valid": True,
        "major": major,
        "feature": feature,
        "patch": patch,
        "build": build,
        "env_tier": env_tier,
        "client": client,
        "is_timestamp_build": is_timestamp,
    }


def main():
    parser = argparse.ArgumentParser(
        description="hs-dev-skill 4-segment autonomous version tool (MMddHHmmss timestamp)"
    )
    subparsers = parser.add_subparsers(dest="command")

    # generate 子命令
    gen_parser = subparsers.add_parser("generate", help="Generate 4-segment version")
    gen_parser.add_argument("--major", type=int, default=1, help="Major version (default: 1)")
    gen_parser.add_argument("--feature", type=int, default=0, help="Feature / Minor version (default: 0)")
    gen_parser.add_argument("--patch", type=int, default=0, help="Patch / Fix version (default: 0)")
    gen_parser.add_argument("--build", type=str, default=None, help="Custom build string (default: current MMddHHmmss timestamp)")
    gen_parser.add_argument("--client", type=str, default=None, help="Client sub-package suffix (e.g. web, apk, ipa, desktop, srv)")
    gen_parser.add_argument("--env-tier", type=str, default=None, help="Environment tier (e.g. alpha, beta, rc.1, ga)")
    gen_parser.add_argument("--timestamp-only", action="store_true", help="Print only 10-digit MMddHHmmss timestamp")

    # parse 子命令
    parse_parser = subparsers.add_parser("parse", help="Parse 4-segment version string")
    parse_parser.add_argument("version", type=str, help="Version string to parse")

    # now 子命令（极速获取时间戳）
    subparsers.add_parser("now", help="Get current MMddHHmmss timestamp")

    args = parser.parse_args()

    if args.command == "generate":
        if args.timestamp_only:
            print(generate_timestamp_build())
            sys.exit(0)
        ver = format_version(
            major=args.major,
            feature=args.feature,
            patch=args.patch,
            build=args.build,
            client=args.client,
            env_tier=args.env_tier,
        )
        print(ver)
    elif args.command == "now":
        print(generate_timestamp_build())
    elif args.command == "parse":
        res = parse_version(args.version)
        import json
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        # 默认不传参数时输出当前生成的标准版本号
        print(format_version(1, 0, 0))


if __name__ == "__main__":
    main()
