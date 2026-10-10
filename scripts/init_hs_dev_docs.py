#!/usr/bin/env python3
"""
init_hs_dev_docs.py
一键初始化符合《产品开发 Skill 规格定义书 v2.4》的完整项目目录结构、文档体系及所有 .idx JSONL 索引文件。
"""

import os
import sys
import argparse
from pathlib import Path
from idx_manager import IdxManager


def init_full_workspace(workspace_root: str):
    root = Path(workspace_root).resolve()
    docs_root = root / "hs_dev_docs"
    mock_root = root / "mock"
    test_root = root / "test"

    print(f"[*] Initializing hs-dev workspace at: {root}")

    # 1. 基础项目层级目录
    base_dirs = [
        "backend", "frontend", "linux", "mac", "windows", "android", "ios",
        "output", "logs", "config", "scripts",
        "test/_00_e2e", "test/_01_method_test", "test/_02_integration_test",
        "test/_03_contract_test", "test/_04_regression_test", "test/_05_performance_test",
        "test/_06_security_test", "test/_07_compatibility_test", "test/_08_test_data",
        "mock/_01_mock_server/_01_route", "mock/_01_mock_server/_02_handler",
        "mock/_01_mock_server/_03_middleware", "mock/_01_mock_server/_04_config",
        "mock/_01_mock_server/_05_start_script",
        "mock/_02_mock_data/_01_dataset", "mock/_02_mock_data/_02_schema",
        "mock/_02_mock_data/_03_fixture",
        "mock/_03_scenario", "mock/_04_error_inject", "mock/_05_delay_inject",
        "mock/_06_test_profile"
    ]
    for d in base_dirs:
        (root / d).mkdir(parents=True, exist_ok=True)

    # 2. hs_dev_docs 目录层级
    doc_dirs = [
        "_00_project/_01_dev_rule",
        "_00_project/_03_code_map",
        "_00_project/_04_context_pack_template",
        "_00_project/_05_decision_record",
        "_00_project/_06_known_issue",
        "_00_project/_07_tech_debt",
        "_00_project/_08_dev_command",
        "_00_project/_09_dev_env",
        "_00_project/_10_prompt_template",
        "_00_project/_11_example_lib",
        "_00_project/_12_test_strategy",
        "_00_project/_13_mock_contract",
        "_00_project/_14_observability_rule",
        "_00_project/_15_security_rule",
        "_00_project/_16_data_consistency_rule",
        "_00_project/_17_git_commit_rule",
        "_01_product_design/_01_business_plan",
        "_01_product_design/_02_product_design",
        "_01_product_design/_03_product_figma",
        "_02_tech_select",
        "_03_architecture_design",
        "_04_db_schema",
        "_05_interface_design",
        "_06_method_design",
        "_07_call_chain",
        "_08_dev_process/_01_plan_log",
        "_08_dev_process/_02_change_log",
        "_08_dev_process/_03_verify_log",
        "_08_dev_process/_04_error_recovery",
        "_08_dev_process/_05_session_handoff",
        "_08_dev_process/_06_todo",
        "_08_dev_process/_07_iteration_debt_log",
        "_08_dev_process/_08_next_step",
        "_08_dev_process/_09_task/_01_task_brief",
        "_08_dev_process/_09_task/_02_task_detail",
        "_08_dev_process/_09_task/_03_task_context_pack",
    ]
    for d in doc_dirs:
        (docs_root / d).mkdir(parents=True, exist_ok=True)

    # 3. 初始化所有核心 .idx 索引文件 (JSONL)
    print("[*] Initializing JSONL .idx indices...")

    # 全局根索引
    root_idx = docs_root / "_00_hs_dev_docs.idx"
    r_mgr = IdxManager(str(root_idx))
    r_mgr.init_idx("root", "hs_dev_docs")
    r_mgr.add_entry("domain_project", "项目基础配置与规范域", "_00_project/_00_project.idx", auto_digest=False)
    r_mgr.add_entry("domain_product", "产品需求与规划域", "_01_product_design/_00_product_design.idx", auto_digest=False)
    r_mgr.add_entry("domain_tech", "技术选型域", "_02_tech_select/_00_tech_select.idx", auto_digest=False)
    r_mgr.add_entry("domain_arch", "架构设计域", "_03_architecture_design/_00_architecture_design.idx", auto_digest=False)
    r_mgr.add_entry("domain_db", "数据库与迁移域", "_04_db_schema/_00_db_schema.idx", auto_digest=False)
    r_mgr.add_entry("domain_interface", "接口设计域", "_05_interface_design/_00_interface_design.idx", auto_digest=False)
    r_mgr.add_entry("domain_method", "方法设计域", "_06_method_design/_00_method_design.idx", auto_digest=False)
    r_mgr.add_entry("domain_call_chain", "调用链分析域", "_07_call_chain/_00_call_chain.idx", auto_digest=False)
    r_mgr.add_entry("domain_process", "开发过程与任务域", "_08_dev_process/_00_dev_process.idx", auto_digest=False)

    # 各功能域索引
    domains = [
        ("_00_project/_00_project.idx", "project", "_00_project"),
        ("_01_product_design/_00_product_design.idx", "product_design", "_01_product_design"),
        ("_02_tech_select/_00_tech_select.idx", "tech_select", "_02_tech_select"),
        ("_03_architecture_design/_00_architecture_design.idx", "architecture_design", "_03_architecture_design"),
        ("_04_db_schema/_00_db_schema.idx", "db_schema", "_04_db_schema"),
        ("_05_interface_design/_00_interface_design.idx", "interface_design", "_05_interface_design"),
        ("_06_method_design/_00_method_design.idx", "method_design", "_06_method_design"),
        ("_07_call_chain/_00_call_chain.idx", "call_chain", "_07_call_chain"),
        ("_08_dev_process/_00_dev_process.idx", "dev_process", "_08_dev_process"),
    ]
    for rel_idx, cat, r_name in domains:
        mgr = IdxManager(str(docs_root / rel_idx))
        mgr.init_idx(cat, r_name)

    # 任务体系索引
    task_idx = docs_root / "_08_dev_process/_09_task/_00_task.idx"
    t_mgr = IdxManager(str(task_idx))
    t_mgr.init_idx("task_active", "_09_task")

    task_archive_idx = docs_root / "_08_dev_process/_09_task/_00_task_archive.idx"
    ta_mgr = IdxManager(str(task_archive_idx))
    ta_mgr.init_idx("task_archive", "_09_task")

    task_brief_idx = docs_root / "_08_dev_process/_09_task/_01_task_brief/_00_task_brief.idx"
    tb_mgr = IdxManager(str(task_brief_idx))
    tb_mgr.init_idx("task_brief", "_01_task_brief")

    task_detail_idx = docs_root / "_08_dev_process/_09_task/_02_task_detail/_00_task_detail.idx"
    td_mgr = IdxManager(str(task_detail_idx))
    td_mgr.init_idx("task_detail", "_02_task_detail")

    task_cp_idx = docs_root / "_08_dev_process/_09_task/_03_task_context_pack/_00_context_pack.idx"
    tcp_mgr = IdxManager(str(task_cp_idx))
    tcp_mgr.init_idx("task_context_pack", "_03_task_context_pack")

    # Mock 索引
    mock_idx = mock_root / "_00_mock.idx"
    m_mgr = IdxManager(str(mock_idx))
    m_mgr.init_idx("mock_root", "mock")

    # 4. 生成统一术语词典模板
    dict_file = docs_root / "_00_project/_02_project_word.dict.yaml"
    if not dict_file.exists():
        dict_file.write_text(
            "# 统一项目术语词典\nterms:\n  - term: \"示例实体\"\n    en_name: \"example_entity\"\n    abbr: \"ex_ent\"\n    scope: \"domain_model\"\n",
            encoding="utf-8"
        )

    print("[SUCCESS] Complete hs-dev-skill file tree and JSONL indices initialized successfully!")


def main():
    parser = argparse.ArgumentParser(description="Initialize hs-dev-docs directory structure")
    parser.add_argument("--root", default=".", help="Target workspace root directory")
    args = parser.parse_args()
    init_full_workspace(args.root)


if __name__ == "__main__":
    main()
