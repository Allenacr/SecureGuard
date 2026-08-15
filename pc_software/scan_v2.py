"""Scan all Python files for compile errors and import issues."""
import py_compile
import os
import sys
import ast
import importlib

out = open("scan_output.txt", "w", encoding="utf-8")

def log(msg=""):
    print(msg)
    out.write(msg + "\n")

py_files = sorted([f for f in os.listdir(".") if f.endswith(".py") and f not in ("scan_all.py", "scan_v2.py")])

# Phase 1
log("=" * 60)
log("PHASE 1: SYNTAX & COMPILE CHECK")
log("=" * 60)

compile_pass = []
compile_fail = []

for f in py_files:
    try:
        py_compile.compile(f, doraise=True)
        compile_pass.append(f)
    except py_compile.PyCompileError as e:
        compile_fail.append((f, str(e)))

for f in compile_pass:
    log(f"  [PASS] {f}")
for f, err in compile_fail:
    log(f"  [FAIL] {f}: {err}")

log(f"\n  Result: {len(compile_pass)} passed, {len(compile_fail)} failed")

# Phase 2
log("\n" + "=" * 60)
log("PHASE 2: IMPORT ANALYSIS")
log("=" * 60)

local_modules = {f[:-3] for f in py_files}

import_issues = []
for f in py_files:
    with open(f, "r", encoding="utf-8", errors="ignore") as fh:
        try:
            tree = ast.parse(fh.read(), filename=f)
        except SyntaxError:
            continue

    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name.split(".")[0]
                if mod in local_modules:
                    continue
                try:
                    importlib.import_module(mod)
                except ImportError:
                    issues.append(f"line {node.lineno}: import {alias.name} -- MODULE NOT FOUND")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mod = node.module.split(".")[0]
                if mod in local_modules:
                    continue
                try:
                    importlib.import_module(mod)
                except ImportError:
                    issues.append(f"line {node.lineno}: from {node.module} import ... -- MODULE NOT FOUND")

    if issues:
        log(f"\n  [WARN] {f}:")
        for issue in issues:
            log(f"         {issue}")
        import_issues.extend(issues)
    else:
        log(f"  [OK]   {f}")

# Phase 3
log("\n" + "=" * 60)
log("PHASE 3: STALE REFERENCE CHECK")
log("=" * 60)

deleted_names = ["decoy_monitor", "DecoyMonitor", "mark_done", "reset_file"]
stale_found = False

for f in py_files:
    with open(f, "r", encoding="utf-8", errors="ignore") as fh:
        lines = fh.readlines()
    for i, line in enumerate(lines, 1):
        for name in deleted_names:
            if name in line and not line.strip().startswith("#"):
                log(f"  [STALE] {f}:{i} -- references '{name}': {line.strip()}")
                stale_found = True

if not stale_found:
    log("  [CLEAN] No stale references to deleted modules found.")

# Phase 4
log("\n" + "=" * 60)
log("PHASE 4: CRITICAL FILE ATTRIBUTE CHECK")
log("=" * 60)

critical_files = ["main.py", "file_protector.py"]
for f in critical_files:
    if not os.path.exists(f):
        log(f"  [SKIP] {f} does not exist")
        continue
    with open(f, "r", encoding="utf-8", errors="ignore") as fh:
        content = fh.read()
    issues = []
    if "self.decoy_monitor" in content:
        issues.append("self.decoy_monitor -- references deleted module")
    if not issues:
        log(f"  [OK]   {f} -- no stale self.decoy_monitor references")
    else:
        for issue in issues:
            log(f"  [WARN] {f}: {issue}")

log("\n" + "=" * 60)
log("SCAN COMPLETE")
log("=" * 60)

out.close()
