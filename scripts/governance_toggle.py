#!/usr/bin/env python3
"""
governance_toggle.py
产品开发 Skill 工程附属机制与治理功能模式启用控制器。
支持功能模式的动态启用、禁用、持久化与门禁联动。
默认策略：
- 启用：version_control, env_and_secrets, supply_chain_security, security_privacy, agent_guardrails
- 停用 (Disabled)：cicd_and_artifacts, observability_telemetry, data_resilience_dr
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import yaml  # type: ignore
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# 默认功能模式启用清单
DEFAULT_GOVERNANCE_CONFIG: Dict[str, Any] = {
    "version": "1.0",
    "description": "hs-dev-skill 工程治理机制启用控制配置",
    "features": {
        "version_control": True,             # 四段式版本控制与自主时间戳生成 (启用)
        "env_and_secrets": True,             # 环境配置隔离与敏感机密防泄露扫描 (启用)
        "supply_chain_security": True,       # 软件供应链与 Lockfile 不可变校验 (启用)
        "cicd_and_artifacts": False,         # CI/CD 流水线与交付制品防伪机制 (当前不启用)
        "observability_telemetry": False,    # 可观测性与运行时遥测机制 (当前不启用)
        "data_resilience_dr": False,         # 数据韧性与容灾回滚机制 (当前不启用)
        "security_privacy": True,            # 安全防御与 PII 数据脱敏 (启用)
        "agent_guardrails": True,            # Agent 执行安全沙箱与行为护栏 (启用)
    }
}

FEATURE_DESCRIPTIONS: Dict[str, str] = {
    "version_control": "四段式多级版本控制与自主 MMddHHmmss 时间戳生成",
    "env_and_secrets": "环境配置隔离与敏感机密凭据防泄露扫描",
    "supply_chain_security": "软件供应链安全与依赖锁文件强一致校验",
    "cicd_and_artifacts": "CI/CD 自动化流水线与交付制品防伪 SBOM (不启用)",
    "observability_telemetry": "可观测性与运行时遥测 (/livez /readyz 探针与监控) (不启用)",
    "data_resilience_dr": "数据韧性与容灾回滚机制 (RPO/RTO 指标与双向迁移) (不启用)",
    "security_privacy": "安全防御矩阵与个人敏感信息 (PII) 脱敏合规",
    "agent_guardrails": "Agent 执行安全沙箱与高危破坏命令拦截护栏",
}


def find_governance_config_file(workspace_root: Path) -> Path:
    """定位 governance.yaml 配置文件位置，优先 config/governance.yaml"""
    cfg = workspace_root / "config" / "governance.yaml"
    if cfg.exists():
        return cfg
    alt = workspace_root / "governance.yaml"
    if alt.exists():
        return alt
    return cfg


def load_governance_config(workspace_root: Optional[Path] = None) -> Dict[str, Any]:
    """读取并合并治理配置，缺失时自动使用默认配置"""
    if workspace_root is None:
        workspace_root = Path.cwd()
    workspace_root = Path(workspace_root).resolve()

    cfg_file = find_governance_config_file(workspace_root)
    if not cfg_file.exists():
        # 如果是 demo_project 或当前目录未初始化的，看 demo_project
        demo_cfg = workspace_root / "demo_project" / "config" / "governance.yaml"
        if demo_cfg.exists():
            cfg_file = demo_cfg

    if not cfg_file.exists():
        # 返回默认拷贝
        import copy
        return copy.deepcopy(DEFAULT_GOVERNANCE_CONFIG)

    content = cfg_file.read_text(encoding="utf-8")
    data = None
    if HAS_YAML:
        try:
            data = yaml.safe_load(content)
        except Exception:
            data = None

    if not isinstance(data, dict):
        # 简单手工键值解析兜底
        features = {}
        for line in content.splitlines():
            line = line.strip()
            if ":" in line and not line.startswith("#"):
                k, v = line.split(":", 1)
                k = k.strip()
                v = v.split("#")[0].strip().lower()
                if v in ("true", "1", "yes", "on"):
                    features[k] = True
                elif v in ("false", "0", "no", "off"):
                    features[k] = False
        data = {"features": features}

    # 合并默认值
    merged_features = dict(DEFAULT_GOVERNANCE_CONFIG["features"])
    user_features = data.get("features", {})
    if isinstance(user_features, dict):
        for k, v in user_features.items():
            if k in merged_features:
                merged_features[k] = bool(v)

    return {
        "version": data.get("version", "1.0"),
        "features": merged_features,
        "config_file": str(cfg_file) if cfg_file.exists() else None,
    }


def save_governance_config(workspace_root: Path, config: Dict[str, Any]) -> Path:
    """持久化治理能力配置文件"""
    cfg_file = workspace_root / "config" / "governance.yaml"
    cfg_file.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# hs-dev-skill 工程治理机制启用控制配置 (Governance Capabilities Toggle)",
        "# 用于按需开启/禁用特定治理功能模式，支持灵活插拔",
        f"version: \"{config.get('version', '1.0')}\"",
        "",
        "features:",
    ]
    features = config.get("features", DEFAULT_GOVERNANCE_CONFIG["features"])
    for k, v in features.items():
        desc = FEATURE_DESCRIPTIONS.get(k, "")
        val_str = "true" if v else "false"
        lines.append(f"  {k}: {val_str:<5}  # {desc}")

    lines.append("")
    cfg_file.write_text("\n".join(lines), encoding="utf-8")
    return cfg_file


def is_feature_enabled(workspace_root: Optional[Path], feature_name: str) -> bool:
    """查询指定功能是否启用"""
    cfg = load_governance_config(workspace_root)
    features = cfg.get("features", {})
    return features.get(feature_name, DEFAULT_GOVERNANCE_CONFIG["features"].get(feature_name, False))


def main():
    parser = argparse.ArgumentParser(
        description="hs-dev-skill Governance Capabilities & Feature Toggle Controller"
    )
    parser.add_argument("--root", default=".", help="Workspace root directory")
    subparsers = parser.add_subparsers(dest="command")

    # status 命令
    subparsers.add_parser("status", help="Show all governance feature toggle states")

    # enable 命令
    en_parser = subparsers.add_parser("enable", help="Enable a governance feature")
    en_parser.add_argument("feature", choices=list(DEFAULT_GOVERNANCE_CONFIG["features"].keys()))

    # disable 命令
    dis_parser = subparsers.add_parser("disable", help="Disable a governance feature")
    dis_parser.add_argument("feature", choices=list(DEFAULT_GOVERNANCE_CONFIG["features"].keys()))

    # init 命令
    subparsers.add_parser("init", help="Initialize config/governance.yaml with default settings")

    # check 命令
    chk_parser = subparsers.add_parser("check", help="Check if a feature is enabled (exit 0/1)")
    chk_parser.add_argument("feature", choices=list(DEFAULT_GOVERNANCE_CONFIG["features"].keys()))

    args = parser.parse_args()
    root = Path(args.root).resolve()

    if args.command == "status" or not args.command:
        cfg = load_governance_config(root)
        print(f"[*] Governance Feature Toggle Status (Root: {root}):")
        if cfg.get("config_file"):
            print(f"    Loaded from: {cfg['config_file']}")
        else:
            print("    Loaded from: DEFAULT SETTINGS (config/governance.yaml not found)")
        print("-" * 75)
        print(f"{'Feature Name':<26} | {'Status':<10} | {'Description'}")
        print("-" * 75)
        for k, v in cfg["features"].items():
            status_str = "[ENABLED]" if v else "[DISABLED]"
            desc = FEATURE_DESCRIPTIONS.get(k, "")
            print(f"{k:<26} | {status_str:<10} | {desc}")
        print("-" * 75)

    elif args.command == "init":
        p = save_governance_config(root, DEFAULT_GOVERNANCE_CONFIG)
        print(f"[SUCCESS] Governance configuration initialized at: {p}")

    elif args.command == "enable":
        cfg = load_governance_config(root)
        cfg["features"][args.feature] = True
        p = save_governance_config(root, cfg)
        print(f"[SUCCESS] Feature '{args.feature}' ENABLED in: {p}")

    elif args.command == "disable":
        cfg = load_governance_config(root)
        cfg["features"][args.feature] = False
        p = save_governance_config(root, cfg)
        print(f"[SUCCESS] Feature '{args.feature}' DISABLED in: {p}")

    elif args.command == "check":
        enabled = is_feature_enabled(root, args.feature)
        if enabled:
            print(f"Feature '{args.feature}' is ENABLED")
            sys.exit(0)
        else:
            print(f"Feature '{args.feature}' is DISABLED")
            sys.exit(1)


if __name__ == "__main__":
    main()
