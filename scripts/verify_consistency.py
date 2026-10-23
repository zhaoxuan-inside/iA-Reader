#!/usr/bin/env python3
"""
verify_consistency.py
产品开发规范与提交前门禁全量自检脚本。
检查三文件一致性、.idx 索引防漂移、DB 迁移 V/U 原子同步、SQL 保留字及 Mock 契约完整性。
"""

import os
import sys
import re
import argparse
from pathlib import Path
from idx_manager import IdxManager


class ConsistencyVerifier:
    def __init__(self, workspace_root: str, strict: bool = False):
        self.root = Path(workspace_root).resolve()
        self.docs_root = self.root / "hs_dev_docs"
        self.mock_root = self.root / "mock"
        self.strict = strict
        self.errors = []
        self.warnings = []

    def check_all(self) -> bool:
        print(f"[*] Starting Consistency & Quality Gate Check at: {self.root}")
        self.errors.clear()
        self.warnings.clear()

        if not self.docs_root.exists() or not (self.docs_root / "_00_hs_dev_docs.idx").exists():
            if (self.root / "demo_project" / "hs_dev_docs").exists():
                self.docs_root = self.root / "demo_project" / "hs_dev_docs"
                self.mock_root = self.root / "demo_project" / "mock"
            elif not self.docs_root.exists():
                self.errors.append("hs_dev_docs directory does not exist! Please run init_hs_dev_docs.py first.")
                self._print_results()
                return False

        # 0. 检查 Skill 自身三处版本号单源一致性（当处于 Skill 根目录时）
        self._check_skill_version()

        # 1. 检查全量 .idx 索引文件
        self._check_indices()

        # 2. 检查任务三文件强一致性
        self._check_task_consistency()

        # 3. 检查数据库迁移脚本原子性 (V & U Sync) 与 SQL 规范
        self._check_database_migrations()

        # 4. 检查 Mock 契约与 Profile 引用
        self._check_mock_profiles()

        # 5. 文档索引库（SQLite）存在性与可查询性（跨平台缓存，非权威源）
        self._check_doc_index_db()

        # 6. 检查多端工程架构卫生与打包产物输出隔离 (Output & Workspace Hygiene)
        self._check_workspace_hygiene()

        # 7. 检查项目术语统一定义词典与防歧义命名规约 (Project Terminology & Anti-Drift Check)
        self._check_project_dictionary()

        # 8. 检查工程附属机制与治理安全 (Auxiliary Governance & Secret Leaks Guard)
        self._check_auxiliary_governance()

        # 9. 检查废弃历史路径与两级 7 大功能域规范对齐 (Deprecated Legacy Paths Guard)
        self._check_deprecated_paths()

        return self._print_results()

    def _check_skill_version(self):
        """检查 Skill 自身三处版本号单源一致性（仅在包含 SKILL.md 的 Skill 根目录触发）"""
        skill_file = self.root / "SKILL.md"
        readme_file = self.root / "README.md"
        if not skill_file.exists():
            return

        print("  -> Checking Skill Package Version Consistency...")
        skill_text = skill_file.read_text(encoding="utf-8")

        m_meta = re.search(r'metadata:\s*\n(?:\s+.*\n)*?\s+version:\s*["\']?([^"\']+)["\']?', skill_text)
        meta_ver = m_meta.group(1).strip() if m_meta else None

        m_body = re.search(r'版本：v?([0-9\.]+)', skill_text)
        body_ver = m_body.group(1).strip() if m_body else None

        if not meta_ver:
            self.errors.append("[SKILL VERSION ERROR] SKILL.md missing metadata.version in frontmatter")
        if not body_ver:
            self.errors.append("[SKILL VERSION ERROR] SKILL.md missing '版本：v...' in body")

        if meta_ver and body_ver and meta_ver != body_ver:
            self.errors.append(
                f"[SKILL VERSION MISMATCH] SKILL.md metadata.version '{meta_ver}' "
                f"does not match body version '{body_ver}'"
            )

        if readme_file.exists():
            readme_text = readme_file.read_text(encoding="utf-8")
            m_readme = re.search(r'badge/skill-v?([0-9\.]+)-blue', readme_text)
            if m_readme:
                readme_ver = m_readme.group(1).strip()
                if meta_ver and readme_ver != meta_ver:
                    self.errors.append(
                        f"[SKILL VERSION MISMATCH] README.md badge version '{readme_ver}' "
                        f"does not match SKILL.md version '{meta_ver}'"
                    )

    def _check_indices(self):
        """遍历并校验所有 .idx 文件"""
        print("  -> Checking all JSONL .idx files...")
        idx_files = list(self.docs_root.rglob("*.idx")) + list(self.mock_root.rglob("*.idx"))
        for idx_file in idx_files:
            try:
                mgr = IdxManager(str(idx_file))
                valid, errs = mgr.verify()
                if not valid:
                    for e in errs:
                        self.errors.append(f"[INDEX ERROR] {idx_file.relative_to(self.root)}: {e}")
            except Exception as ex:
                self.errors.append(f"[INDEX PARSE ERROR] {idx_file.relative_to(self.root)}: {ex}")

    def _check_task_consistency(self):
        """检查 _00_task.idx、task_brief 与 task_detail 三文件一致性"""
        print("  -> Checking Task Triple-File Consistency...")
        task_root_dir = self.docs_root / "_05_task_orchestration"
        task_idx_file = task_root_dir / "_00_task.idx"
        if not task_idx_file.exists():
            task_root_dir = self.docs_root / "_08_dev_process/_09_task"
            task_idx_file = task_root_dir / "_00_task.idx"

        if not task_idx_file.exists():
            return

        mgr = IdxManager(str(task_idx_file))
        brief_dir = task_root_dir / "_01_task_brief"
        detail_dir = task_root_dir / "_02_task_detail"

        # 聚合所有 task_brief 内容
        brief_contents = ""
        for bf in brief_dir.glob("*.md"):
            brief_contents += bf.read_text(encoding="utf-8") + "\n"

        active_entries = list(mgr.entries)
        arch_entries = []
        arch_idx_file = task_root_dir / "_00_task_archive.idx"
        if arch_idx_file.exists():
            arch_mgr = IdxManager(str(arch_idx_file))
            arch_entries = list(arch_mgr.entries)

        all_tasks = [(entry, True) for entry in active_entries] + [(entry, False) for entry in arch_entries]

        for entry, is_active in all_tasks:
            task_id = entry.get("id")
            title = entry.get("title")
            status = entry.get("status")

            # 1. 检查 task_brief 中是否存在该条目
            if f"### 任务简述：{task_id}" not in brief_contents:
                self.errors.append(f"[TASK CONSISTENCY] Task '{task_id}' missing in _01_task_brief/*.md")
            else:
                # 检查简述中的状态
                pattern = rf"### 任务简述：{task_id}[\s\S]*?- \*\*状态\*\*：`([^`]+)`"
                m = re.search(pattern, brief_contents)
                if m:
                    b_status = m.group(1)
                    if b_status != status:
                        self.errors.append(f"[TASK MISMATCH] Task '{task_id}' status mismatch: .idx has '{status}', but brief has '{b_status}'")

            # 2. 检查 task_detail
            rel_path = entry.get("path")
            target_detail = task_root_dir / rel_path
            if not target_detail.exists():
                self.errors.append(f"[TASK CONSISTENCY] Task '{task_id}' detail file missing: {rel_path}")
            else:
                d_content = target_detail.read_text(encoding="utf-8")
                m = re.search(r"- \*\*当前状态\*\*：`([^`]+)`", d_content)
                if m:
                    d_status = m.group(1)
                    if d_status != status:
                        self.errors.append(f"[TASK MISMATCH] Task '{task_id}' status mismatch: .idx has '{status}', but detail has '{d_status}'")

                # change_size：仅活跃任务且缺失时 warning（兼容旧任务）
                if is_active and not re.search(r"- \*\*(?:变更分级|change_size)\*\*：`([SML])`", d_content):
                    self.warnings.append(
                        f"[RIGHT-SIZING] Active task '{task_id}' missing change_size=S|M|L in detail "
                        f"(set via task_manager create --change-size; see references/right_sizing.md)"
                    )

                # 3. 需求追踪矩阵与 100% 覆盖率硬校验 (Requirement Traceability & Coverage Gate)
                req_lines = [l.strip() for l in d_content.splitlines() if l.strip().startswith("|")]
                req_items = []
                for l in req_lines:
                    cols = [c.strip() for c in l.split("|")[1:-1]]
                    if cols and re.match(r"^`?REQ-[A-Za-z0-9_-]+`?$", cols[0]):
                        req_id = cols[0].strip("`")
                        r_status = cols[-1].strip("`").lower()
                        req_items.append((req_id, r_status))

                if req_items:
                    total_reqs = len(req_items)
                    unverified = [r for r in req_items if r[1] not in ["verified", "passed", "done"]]
                    if status and status.upper() in ["COMPLETED", "SUCCEEDED"] and unverified:
                        uv_str = ", ".join([f"{rid} (status: {st})" for rid, st in unverified])
                        self.errors.append(
                            f"[REQUIREMENT COVERAGE ERROR] Task '{task_id}' is marked {status} but has unverified requirement(s): {uv_str}. "
                            f"Requirement Coverage must be 100% ({total_reqs - len(unverified)}/{total_reqs} verified). "
                            f"See references/quality_gates.md §2 (Gate 0d)."
                        )

            # context_pack 同步检查 change_size（仅活跃任务）
            if is_active:
                cp_path = (
                    task_root_dir
                    / f"_03_task_context_pack/_01_{task_id}/_00_context_pack.md"
                )
                if not cp_path.exists():
                    cp_path = (
                        task_root_dir
                        / f"_03_task_context_pack/{task_id}_context_pack.md"
                    )
                if cp_path.exists():
                    cp_text = cp_path.read_text(encoding="utf-8")
                    if not re.search(r"- \*\*change_size\*\*：`([SML])`", cp_text):
                        self.warnings.append(
                            f"[RIGHT-SIZING] Active task '{task_id}' context_pack missing change_size=S|M|L"
                        )

    def _check_database_migrations(self):
        """检查 DB 迁移 V/U 脚本原子配对与 SQL 规范"""
        print("  -> Checking Database Migrations (V/U Sync) and SQL Rules...")
        migration_dirs = list(self.docs_root.rglob("migrations"))
        for m_dir in migration_dirs:
            v_files = list(m_dir.glob("V*.sql"))
            u_files = list(m_dir.glob("U*.sql"))

            v_versions = {}
            for vf in v_files:
                match = re.match(r"V([0-9\._]+__(.+))\.sql", vf.name)
                if match:
                    ver_desc = match.group(1)
                    v_versions[ver_desc] = vf
                else:
                    self.errors.append(f"[DB MIGRATION FORMAT ERROR] {vf.name} does not match V<version>__<description>.sql format")

            for ver_desc, vf in v_versions.items():
                expected_u = m_dir / f"U{ver_desc}.sql"
                if not expected_u.exists():
                    self.errors.append(f"[DB MIGRATION ERROR] Forward migration {vf.name} is missing corresponding rollback script {expected_u.name}")

                # 检查 SQL 中是否含有非法的 desc 字段 (保留字检查)
                v_content = vf.read_text(encoding="utf-8")
                if re.search(r"\bdesc\s+(varchar|text|int|bigint|timestamp|datetime)\b", v_content, re.IGNORECASE):
                    self.errors.append(f"[SQL KEYWORD ERROR] {vf.name} uses forbidden SQL reserved keyword 'desc' as column name. Please rename to 'description'.")

    def _check_mock_profiles(self):
        """检查 Mock Test Profile 的契约引用"""
        print("  -> Checking Mock Profiles...")
        profile_dir = self.mock_root / "_06_test_profile"
        if not profile_dir.exists():
            return

        for pf in profile_dir.glob("*.yaml"):
            content = pf.read_text(encoding="utf-8")
            for line in content.split("\n"):
                if line.startswith("contract_ref:"):
                    ref_path = line.split(":", 1)[1].strip().strip('"').strip("'")
                    target = self.root / ref_path
                    if not target.exists() and (self.docs_root.parent / ref_path).exists():
                        target = self.docs_root.parent / ref_path
                    if not target.exists():
                        self.warnings.append(f"[MOCK PROFILE WARNING] {pf.name} contract_ref not found on disk: {ref_path}")

    def _check_doc_index_db(self):
        """检查 SQLite 文档索引缓存；缺失则告警（不阻断，因可 rebuild）"""
        print("  -> Checking Doc Index DB (SQLite cache)...")
        db_file = self.docs_root / "_00_project_foundation" / "_05_doc_index" / "doc_index.sqlite"
        if not db_file.exists():
            db_file = self.docs_root / "_00_project" / "_18_doc_index" / "doc_index.sqlite"
        idx_files = list(self.docs_root.rglob("*.idx"))
        if not idx_files:
            return
        if not db_file.exists():
            self.warnings.append(
                "[DOC INDEX] Missing doc_index.sqlite — run: python scripts/doc_index_db.py --root . rebuild"
            )
            return
        try:
            from doc_index_db import DocIndexDB

            target_root = self.docs_root.parent
            db = DocIndexDB(target_root)
            st = db.stats()
            db.close()
            if st.get("docs", 0) <= 0:
                self.warnings.append(
                    "[DOC INDEX] SQLite index is empty — run: python scripts/doc_index_db.py --root . rebuild"
                )
        except Exception as ex:
            self.warnings.append(f"[DOC INDEX] Unable to open SQLite cache: {ex}")

    def _check_workspace_hygiene(self):
        """检查工程多端目录卫生：散落二进制产物、配置隔离与 output 规约"""
        print("  -> Checking Workspace Hygiene & Output Directory Isolation...")
        # 1. 检查是否存在直接散落在根目录的安装包或二进制产物 (未收敛至 output/)
        stray_extensions = [".apk", ".aab", ".ipa", ".dmg", ".exe", ".AppImage"]
        for ext in stray_extensions:
            for stray in self.root.glob(f"*{ext}"):
                self.errors.append(
                    f"[ARTIFACT ERROR] Stray binary '{stray.name}' found at workspace root! "
                    f"Must be relocated into output/<platform> directory."
                )

        # 2. 检查敏感环境变量与配置隔离 (.env 存在但无 .env.example)
        dot_env = self.root / ".env"
        dot_env_example = self.root / "config" / ".env.example"
        if not dot_env_example.exists():
            dot_env_example = self.root / ".env.example"
        if dot_env.exists() and not dot_env_example.exists():
            self.warnings.append(
                "[CONFIG WARNING] Local .env exists but missing .env.example template in config/ or root!"
            )

    def _check_project_dictionary(self):
        """
        检查项目统一定义词典 (_02_project_word.dict.yaml) 与防歧义命名规约。
        拦截：
        1. 词典不存在时警告提示；
        2. 词典内同义词冲突或缺少关键字段；
        3. 代码、DB 迁移和设计文档中使用了 forbidden_alias（禁用别名）；
        4. 事件命名动词原形漂移与时间戳混淆（如使用 order.update 或将 updated_at 命名为事件）。
        """
        print("  -> Checking Project Word Dictionary & Terminology Consistency...")
        dict_file = self.docs_root / "_00_project_foundation" / "_02_dictionary" / "_02_project_word.dict.yaml"
        if not dict_file.exists():
            dict_file = self.docs_root / "_00_project" / "_02_project_word.dict.yaml"
        if not dict_file.exists():
            self.warnings.append(
                "[TERMINOLOGY WARNING] Missing project word dictionary (_02_project_word.dict.yaml). "
                "Ubiquitous language dictionary is strongly recommended."
            )
            return

        dict_text = dict_file.read_text(encoding="utf-8")
        data = None
        try:
            import yaml  # type: ignore
            data = yaml.safe_load(dict_text)
        except Exception:
            pass

        # 解析 terms 与 lifecycle_terms
        terms_list = []
        lifecycle_terms_list = []
        if isinstance(data, dict):
            terms_list = data.get("terms", []) or []
            lifecycle_terms_list = data.get("lifecycle_terms", []) or []
        else:
            # 基础简易解析兜底
            current_term = {}
            for line in dict_text.splitlines():
                line = line.strip()
                if line.startswith("- term:"):
                    if current_term and "en_name" in current_term:
                        terms_list.append(current_term)
                    current_term = {"term": line.split(":", 1)[1].strip().strip('"').strip("'")}
                elif line.startswith("en_name:"):
                    current_term["en_name"] = line.split(":", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("forbidden_alias:"):
                    raw = line.split(":", 1)[1].strip().strip("[]")
                    aliases = [a.strip().strip('"').strip("'") for a in raw.split(",") if a.strip()]
                    current_term["forbidden_alias"] = aliases
            if current_term and "en_name" in current_term:
                terms_list.append(current_term)

        # 收集禁用别名映射: alias -> (en_name, concept)
        forbidden_map = {}
        defined_en_names = set()

        for item in terms_list:
            if not isinstance(item, dict):
                continue
            en_name = item.get("en_name")
            if en_name:
                if en_name in defined_en_names:
                    self.errors.append(f"[DICTIONARY ERROR] Duplicate en_name '{en_name}' in _02_project_word.dict.yaml")
                defined_en_names.add(en_name)

            for alias in item.get("forbidden_alias", []) or []:
                alias = str(alias).strip()
                if alias:
                    forbidden_map[alias.lower()] = (en_name or item.get("term", "unknown"), item.get("term", ""))

        for item in lifecycle_terms_list:
            if not isinstance(item, dict):
                continue
            concept = item.get("concept", "")
            cmd = item.get("command", "")
            evt = item.get("event", "")
            for alias in item.get("forbidden_alias", []) or []:
                alias = str(alias).strip()
                if alias:
                    forbidden_map[alias.lower()] = (f"{cmd}/{evt}", concept)

        # 检查内部冲突：forbidden_alias 与 defined_en_names 重合
        for alias, (target, _) in forbidden_map.items():
            if alias in defined_en_names:
                self.errors.append(
                    f"[DICTIONARY CONFLICT] Forbidden alias '{alias}' is also registered as valid en_name '{target}'!"
                )

        # 扫描关键工程目录：DB 迁移、接口设计、方法设计、后端与前端源码
        if forbidden_map:
            scan_dirs = [
                self.docs_root / "_04_engineering_contract" / "_01_db_schema",
                self.docs_root / "_04_engineering_contract" / "_02_interface_design",
                self.docs_root / "_04_engineering_contract" / "_04_method_design",
                self.docs_root / "_04_db_schema",
                self.docs_root / "_05_interface_design",
                self.docs_root / "_06_method_design",
                self.root / "backend",
                self.root / "frontend",
                self.root / "apps",
                self.root / "packages",
                self.root / "src",
            ]
            if (self.root / "demo_project" / "backend").exists() and self.root != self.docs_root.parent:
                scan_dirs.append(self.root / "demo_project" / "backend")

            for sdir in scan_dirs:
                if not sdir.exists():
                    continue
                for fpath in sdir.rglob("*"):
                    if not fpath.is_file() or fpath.suffix not in [
                        ".sql", ".py", ".ts", ".js", ".go", ".rs", ".java", ".md", ".json", ".yaml"
                    ]:
                        continue
                    if fpath.name.endswith(".idx") or fpath.name.endswith(".sqlite") or "project_word.dict.yaml" in fpath.name:
                        continue
                    try:
                        content = fpath.read_text(encoding="utf-8", errors="ignore")
                    except Exception:
                        continue

                    # 扫描禁用词
                    for alias, (approved, concept) in forbidden_map.items():
                        pattern = r'(?<![a-zA-Z0-9_])' + re.escape(alias) + r'(?![a-zA-Z0-9_])'
                        if re.search(pattern, content, re.IGNORECASE):
                            try:
                                rel_p = fpath.relative_to(self.root)
                            except ValueError:
                                rel_p = fpath.name
                            self.errors.append(
                                f"[TERMINOLOGY ERROR] {rel_p} uses forbidden alias '{alias}'. "
                                f"Please use approved term '{approved}' (Concept: {concept}) defined in _02_project_word.dict.yaml."
                            )

        # 检查事件动词原形/时间戳混淆 (Event Semantic Drift)
        drift_pattern = re.compile(r'["\']([a-zA-Z0-9_-]+\.(?:update|create|delete))["\']')
        timestamp_event_pattern = re.compile(r'["\']([a-zA-Z0-9_-]+\.(?:updated_at|created_at|deleted_at))["\']')

        code_scan_dirs = [
            self.docs_root / "_05_interface_design",
            self.root / "backend",
            self.root / "frontend",
            self.root / "apps",
            self.root / "packages",
            self.root / "src",
        ]
        for cdir in code_scan_dirs:
            if not cdir.exists():
                continue
            for fpath in cdir.rglob("*"):
                if not fpath.is_file() or fpath.suffix not in [".py", ".ts", ".js", ".go", ".rs", ".java", ".md"]:
                    continue
                if fpath.name.endswith(".idx"):
                    continue
                try:
                    content = fpath.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue

                for match in drift_pattern.finditer(content):
                    term_found = match.group(1)
                    try:
                        rel_p = fpath.relative_to(self.root)
                    except ValueError:
                        rel_p = fpath.name
                    self.errors.append(
                        f"[EVENT GRAMMAR ERROR] {rel_p} uses imperative verb in event topic '{term_found}'. "
                        f"Domain events must use past participle (e.g., .updated, .created, .deleted)."
                    )
                for match in timestamp_event_pattern.finditer(content):
                    term_found = match.group(1)
                    try:
                        rel_p = fpath.relative_to(self.root)
                    except ValueError:
                        rel_p = fpath.name
                    self.errors.append(
                        f"[EVENT GRAMMAR ERROR] {rel_p} uses timestamp field name '{term_found}' as event topic. "
                        f"Timestamps are properties, not events."
                    )

    def _check_auxiliary_governance(self):
        """
        检查工程附属机制与治理支撑（受 governance_toggle 控制）：
        1. 敏感凭据/密钥硬编码防泄漏扫描 (Zero-Secrets Policy)；
        2. 依赖锁文件存在性检查 (Lockfile Hygiene)；
        3. 环境变量模板契约 (.env.example)；
        4. 受控跳过未启用的机制 (CI/CD, Observability, Data Resilience 默认不启用)。
        """
        try:
            from governance_toggle import is_feature_enabled
        except ImportError:
            is_feature_enabled = lambda root, feat: True

        check_secrets = is_feature_enabled(self.root, "env_and_secrets")
        check_lockfile = is_feature_enabled(self.root, "supply_chain_security")
        check_cicd = is_feature_enabled(self.root, "cicd_and_artifacts")
        check_obs = is_feature_enabled(self.root, "observability_telemetry")
        check_dr = is_feature_enabled(self.root, "data_resilience_dr")

        status_notes = []
        if not check_cicd:
            status_notes.append("cicd=OFF")
        if not check_obs:
            status_notes.append("observability=OFF")
        if not check_dr:
            status_notes.append("data_resilience=OFF")

        note_str = f" [Toggles: {', '.join(status_notes)}]" if status_notes else ""
        print(f"  -> Checking Auxiliary Governance & Secret Leaks Guard{note_str}...")

        # 1. 敏感凭据正则扫描（排除测试与 mock 目录）
        if check_secrets:
            secret_patterns = [
                (re.compile(r'-----BEGIN\s+(?:RSA|OPENSSH|DSA|EC)\s+PRIVATE\s+KEY-----'), "Private Key"),
                (re.compile(r'(?i)\b(?:ghp|gho|ghu|ghs|ghr)_[0-9a-zA-Z]{36}\b'), "GitHub Personal Access Token"),
                (re.compile(r'\bsk-(?:proj-)?[a-zA-Z0-9_-]{20,80}\b'), "OpenAI API Secret Key"),
                (re.compile(r'\bAKIA[0-9A-Z]{16}\b'), "AWS Access Key ID"),
            ]

            code_scan_dirs = [
                self.root / "backend",
                self.root / "frontend",
                self.root / "apps",
                self.root / "packages",
                self.root / "src",
                self.root / "config",
            ]
            if (self.root / "demo_project" / "backend").exists():
                code_scan_dirs.append(self.root / "demo_project" / "backend")

            for sdir in code_scan_dirs:
                if not sdir.exists():
                    continue
                for fpath in sdir.rglob("*"):
                    if not fpath.is_file() or fpath.suffix not in [
                        ".py", ".ts", ".js", ".go", ".rs", ".java", ".json", ".yaml", ".yml", ".env"
                    ]:
                        continue
                    p_str = str(fpath).replace("\\", "/")
                    if "/tests/" in p_str or "/test/" in p_str or "/mock/" in p_str or "test_" in fpath.name:
                        continue
                    try:
                        content = fpath.read_text(encoding="utf-8", errors="ignore")
                    except Exception:
                        continue

                    for pat, label in secret_patterns:
                        if pat.search(content):
                            try:
                                rel_p = fpath.relative_to(self.root)
                            except ValueError:
                                rel_p = fpath.name
                            self.errors.append(
                                f"[SECRET LEAK ERROR] Potential hardcoded {label} detected in {rel_p}! "
                                f"Secrets must be provided via environment variables or secret managers."
                            )

        # 2. 依赖锁文件检查（如果有 package.json，必须有 lockfile）
        if check_lockfile:
            for pkg_json in self.root.rglob("package.json"):
                if "node_modules" in pkg_json.parts or ".hs_cache" in pkg_json.parts:
                    continue
                pkg_dir = pkg_json.parent
                has_lock = any(
                    (pkg_dir / lock_name).exists()
                    for lock_name in ["package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb"]
                )
                if not has_lock:
                    try:
                        rel_p = pkg_json.relative_to(self.root)
                    except ValueError:
                        rel_p = pkg_json.name
                    self.warnings.append(
                        f"[SUPPLY CHAIN WARNING] {rel_p} found but missing immutable lockfile "
                        f"(package-lock.json / pnpm-lock.yaml / yarn.lock). Lockfile is mandatory for deterministic builds."
                    )

        # 3. 可选机制：CI/CD 交付物与 SBOM（当启用时）
        if check_cicd:
            sbom_file = self.root / "output" / "sbom.json"
            if not sbom_file.exists():
                self.warnings.append("[CICD WARNING] Feature 'cicd_and_artifacts' enabled but output/sbom.json missing.")

        # 4. 可选机制：可观测性探针（当启用时）
        if check_obs:
            pass

        # 5. 可选机制：数据韧性（当启用时）
        if check_dr:
            pass

    def _check_deprecated_paths(self):
        """检查文档与模板中是否存在废弃的旧路径（确保符合 v2.42 两级 7 大功能域规范）"""
        target_dirs = [self.root / "references", self.root / "resources" / "templates"]
        legacy_patterns = [
            (re.compile(r'hs_dev_docs/_00_project(?!_foundation)'), "hs_dev_docs/_00_project_foundation"),
            (re.compile(r'hs_dev_docs/_01_product_design'), "hs_dev_docs/_01_product_vision 或 _02_feature_spec"),
            (re.compile(r'hs_dev_docs/_02_product_design'), "hs_dev_docs/_02_feature_spec/_01_human_prd"),
            (re.compile(r'hs_dev_docs/_03_product_figma'), "hs_dev_docs/_02_feature_spec/_03_prototype_html"),
            (re.compile(r'hs_dev_docs/_04_db_schema'), "hs_dev_docs/_04_engineering_contract/_01_db_schema"),
            (re.compile(r'hs_dev_docs/_05_interface_design'), "hs_dev_docs/_04_engineering_contract/_02_interface_design"),
            (re.compile(r'hs_dev_docs/_06_method_design'), "hs_dev_docs/_04_engineering_contract/_04_method_design"),
            (re.compile(r'hs_dev_docs/_06_mock_contract'), "hs_dev_docs/_04_engineering_contract/_03_mock_contract"),
            (re.compile(r'hs_dev_docs/_07_call_chain'), "hs_dev_docs/_04_engineering_contract/_05_call_chain"),
            (re.compile(r'hs_dev_docs/_08_dev_process'), "hs_dev_docs/_06_dev_process 或 _05_task_orchestration"),
        ]

        found_header = False
        for t_dir in target_dirs:
            if not t_dir.exists():
                continue
            for p in t_dir.rglob("*"):
                if not p.is_file() or p.suffix not in [".md", ".yaml", ".yml", ".json", ".html"]:
                    continue
                try:
                    text = p.read_text(encoding="utf-8")
                except Exception:
                    continue
                for idx, line in enumerate(text.splitlines(), 1):
                    for pat, suggestion in legacy_patterns:
                        if pat.search(line):
                            if not found_header:
                                print("  -> Checking Deprecated Legacy Path References...")
                                found_header = True
                            rel = p.relative_to(self.root)
                            self.errors.append(
                                f"[DEPRECATED PATH ERROR] Legacy path pattern '{pat.pattern}' found in {rel}:{idx}! "
                                f"Must be updated to '{suggestion}'."
                            )

    def _print_results(self) -> bool:
        print("\n" + "=" * 60)
        if self.warnings:
            print(f"[!] WARNINGS ({len(self.warnings)}):")
            for w in self.warnings:
                print(f"  {w}")

        if self.strict and self.warnings:
            self.errors.append(
                f"[STRICT GATE ERROR] Strict mode enabled (Zero Warnings Policy): "
                f"{len(self.warnings)} warning(s) treated as blocking error(s)!"
            )

        if not self.errors:
            print("[PASS] All consistency and quality gate checks passed successfully! Ready for commit.")
            print("=" * 60)
            return True
        else:
            print(f"[FAIL] Quality gate check failed with {len(self.errors)} errors:")
            for e in self.errors:
                print(f"  {e}")
            print("=" * 60)
            return False


def main():
    parser = argparse.ArgumentParser(description="Skill Quality Gate & Triple-File Consistency Verifier")
    parser.add_argument("--root", default=".", help="Target workspace root")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Zero-warning mode: treat any warnings as blocking errors (Zero Warnings Policy)",
    )
    args = parser.parse_args()

    verifier = ConsistencyVerifier(args.root, strict=args.strict)
    success = verifier.check_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
