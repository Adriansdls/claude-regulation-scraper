#!/usr/bin/env python3
"""
Verification script for Research Graph Explorer installation.

Run after installing to verify everything works:
    python scripts/verify_install.py
"""

import sys
from typing import List, Tuple


def check_python_version() -> Tuple[bool, str]:
    """Check Python version >= 3.10"""
    version = sys.version_info
    if version >= (3, 10):
        return True, f"✅ Python {version.major}.{version.minor}.{version.micro}"
    return False, f"❌ Python {version.major}.{version.minor} (need >= 3.10)"


def check_import(module_name: str, display_name: str = None) -> Tuple[bool, str]:
    """Check if module can be imported"""
    display_name = display_name or module_name
    try:
        __import__(module_name)
        return True, f"✅ {display_name}"
    except ImportError as e:
        return False, f"❌ {display_name}: {e}"


def check_cli_entry_point() -> Tuple[bool, str]:
    """Check if CLI is importable"""
    try:
        from src.cli.main import cli
        return True, f"✅ CLI entry point (type: {type(cli).__name__})"
    except Exception as e:
        return False, f"❌ CLI entry point: {e}"


def check_core_modules() -> List[Tuple[bool, str]]:
    """Check core application modules"""
    modules = [
        ("src.agent", "Agent module"),
        ("src.analysis", "Analysis module"),
        ("src.extraction", "Extraction module"),
        ("src.discovery", "Discovery module"),
        ("src.models", "Models module"),
        ("src.cli.main", "CLI module"),
    ]

    results = []
    for module, display in modules:
        results.append(check_import(module, display))
    return results


def check_ui_modules() -> List[Tuple[bool, str]]:
    """Check new UI enhancement modules"""
    modules = [
        ("src.cli.ui", "UI module"),
        ("src.cli.ui.plots", "Terminal plots"),
        ("src.cli.ui.autocomplete", "Autocomplete"),
        ("src.cli.ui.tokens", "Token tracking"),
        ("src.cli.ui.status", "Status bar"),
        ("src.cli.ui.syntax", "Syntax highlighting"),
        ("src.cli.ui.multiline", "Multi-line input"),
    ]

    results = []
    for module, display in modules:
        results.append(check_import(module, display))
    return results


def check_dependencies() -> List[Tuple[bool, str]]:
    """Check key dependencies"""
    deps = [
        # Core
        ("anthropic", "Anthropic API"),
        ("openai", "OpenAI API"),
        ("networkx", "NetworkX"),

        # CLI/UX
        ("rich", "Rich (formatting)"),
        ("click", "Click (CLI)"),

        # New UX features
        ("prompt_toolkit", "prompt-toolkit (autocomplete)"),
        ("plotext", "plotext (terminal plots)"),
        ("pygments", "Pygments (syntax highlighting)"),
        ("tiktoken", "tiktoken (token counting)"),

        # Graph
        ("leidenalg", "Leiden algorithm"),

        # APIs
        ("semanticscholar", "Semantic Scholar"),
        ("arxiv", "arXiv"),
    ]

    results = []
    for module, display in deps:
        results.append(check_import(module, display))
    return results


def check_cli_command() -> Tuple[bool, str]:
    """Check if 'rge' command is available"""
    import subprocess
    try:
        result = subprocess.run(
            ["rge", "--help"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return True, "✅ 'rge' command available"
        return False, f"❌ 'rge' command failed (exit code {result.returncode})"
    except FileNotFoundError:
        return False, "❌ 'rge' command not found (try: pip install -e .)"
    except subprocess.TimeoutExpired:
        return False, "❌ 'rge' command timeout"
    except Exception as e:
        return False, f"❌ 'rge' command error: {e}"


def check_version() -> Tuple[bool, str]:
    """Check package version"""
    try:
        import importlib.metadata
        version = importlib.metadata.version("research-graph-explorer")
        return True, f"✅ Package version: {version}"
    except importlib.metadata.PackageNotFoundError:
        return False, "❌ Package not installed (try: pip install -e .)"
    except Exception as e:
        return False, f"❌ Version check failed: {e}"


def main():
    """Run all verification checks"""
    print("=" * 70)
    print("Research Graph Explorer - Installation Verification")
    print("=" * 70)
    print()

    all_passed = True

    # Python version
    print("[ Python Version ]")
    passed, msg = check_python_version()
    print(msg)
    all_passed = all_passed and passed
    print()

    # Package version
    print("[ Package Version ]")
    passed, msg = check_version()
    print(msg)
    all_passed = all_passed and passed
    print()

    # CLI entry point
    print("[ CLI Entry Point ]")
    passed, msg = check_cli_entry_point()
    print(msg)
    all_passed = all_passed and passed
    print()

    # CLI command
    print("[ CLI Command ]")
    passed, msg = check_cli_command()
    print(msg)
    all_passed = all_passed and passed
    print()

    # Core modules
    print("[ Core Modules ]")
    results = check_core_modules()
    for passed, msg in results:
        print(msg)
        all_passed = all_passed and passed
    print()

    # UI modules
    print("[ UI Enhancement Modules ]")
    results = check_ui_modules()
    for passed, msg in results:
        print(msg)
        all_passed = all_passed and passed
    print()

    # Dependencies
    print("[ Key Dependencies ]")
    results = check_dependencies()
    passed_count = sum(1 for p, _ in results if p)
    total_count = len(results)
    print(f"Checking {total_count} dependencies...")

    failed = [msg for passed, msg in results if not passed]
    if failed:
        print(f"⚠️  {len(failed)} optional dependencies missing:")
        for msg in failed:
            print(f"  {msg}")
    else:
        print(f"✅ All {total_count} dependencies installed!")
    print()

    # Summary
    print("=" * 70)
    if all_passed:
        print("🎉 SUCCESS! Research Graph Explorer is ready to use!")
        print()
        print("Try these commands:")
        print("  rge --help")
        print("  rge chat <knowledge_graph.json>")
        print()
        print("Enjoy the world-class UX! ✨")
    else:
        print("⚠️  PARTIAL: Some checks failed")
        print()
        print("Missing dependencies? Try:")
        print("  pip install -e .")
        print("  pip install -e '.[dev]'")
        print()
        print("Still having issues? Check INSTALL.md")
    print("=" * 70)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
