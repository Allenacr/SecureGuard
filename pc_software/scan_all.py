"""Scan all Python files for compile errors and import issues."""
import py_compile
import os
import sys
import ast
import importlib

# ── Phase 1: Syntax / compile check ──
print("=" * 60)
print("PHASE 1: SYNTAX & COMPILE CHECK")
print("=" * 60)

py_files = sorted([f for f in os.listdir(".") if f.endswith(".py") and f != "scan_all.py"])
compile_pass = []
compile_fail = []

for f in py_files:
    try:
        py_compile.compile(f, doraise=True)
        compile_pass.append(f)
    except py_compile.PyCompileError as e:
        compile_fail.append((f, str(e)))

for f in compile_pass:
    print(f"  [PASS] {f}")
for f, err in compile_fail:
    print(f"  [FAIL] {f}: {err}")

print(f"\n  Result: {len(compile_pass)} passed, {len(compile_fail)} failed")

# ── Phase 2: Import analysis ──
print("\n" + "=" * 60)
print("PHASE 2: IMPORT ANALYSIS")
print("=" * 60)

# Collect all local module names
local_modules = {f[:-3] for f in py_files}

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
                    issues.append(f"line {node.lineno}: import {alias.name} — MODULE NOT FOUND")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mod = node.module.split(".")[0]
                if mod in local_modules:
                    continue
                try:
                    importlib.import_module(mod)
                except ImportError:
                    issues.append(f"line {node.lineno}: from {node.module} import ... — MODULE NOT FOUND")

    if issues:
        print(f"\n  [WARN] {f}:")
        for issue in issues:
            print(f"         {issue}")
    else:
        print(f"  [OK]   {f}")

# ── Phase 3: Cross-reference check — look for references to deleted modules ──
print("\n" + "=" * 60)
print("PHASE 3: STALE REFERENCE CHECK")
print("=" * 60)

deleted_names = ["decoy_monitor", "DecoyMonitor", "mark_done", "reset_file"]
stale_found = False

for f in py_files:
    with open(f, "r", encoding="utf-8", errors="ignore") as fh:
        lines = fh.readlines()
    for i, line in enumerate(lines, 1):
        for name in deleted_names:
            if name in line and not line.strip().startswith("#"):
                print(f"  [STALE] {f}:{i} — references '{name}': {line.strip()}")
                stale_found = True

if not stale_found:
    print("  [CLEAN] No stale references to deleted modules found.")

# ── Phase 4: Check for undefined name usage via AST ──
print("\n" + "=" * 60)
print("PHASE 4: UNDEFINED VARIABLE / ATTRIBUTE SPOT-CHECK")
print("=" * 60)

# Quick check: does main.py reference self.decoy_monitor anywhere?
critical_files = ["main.py", "file_protector.py"]
for f in critical_files:
    if not os.path.exists(f):
        print(f"  [SKIP] {f} does not exist")
        continue
    with open(f, "r", encoding="utf-8", errors="ignore") as fh:
        content = fh.read()
    issues = []
    if "self.decoy_monitor" in content:
        issues.append("self.decoy_monitor — references deleted module")
    if "decoy_monitor" in content and "import" not in content.split("decoy_monitor")[0].split("\n")[-1]:
        # more nuanced check
        pass
    if not issues:
        print(f"  [OK]   {f} — no stale self.decoy_monitor references")
    else:
        for issue in issues:
            print(f"  [WARN] {f}: {issue}")

print("\n" + "=" * 60)
print("SCAN COMPLETE")
print("=" * 60)
