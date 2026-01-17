#!/usr/bin/env python3
"""
Comprehensive test runner for the sports simulation engine.

Runs all validation tests in sequence to verify the entire pipeline.

Usage: python scripts/run_all_tests.py
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and report results"""
    print("\n" + "="*70)
    print(f"Running: {description}")
    print("="*70)
    print(f"Command: {cmd}\n")

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            capture_output=False,
            text=True
        )
        print(f"\n✅ PASSED: {description}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ FAILED: {description}")
        print(f"Exit code: {e.returncode}")
        return False


def main():
    """Run all tests"""
    print("\n" + "🧪" * 35)
    print("COMPREHENSIVE TEST SUITE")
    print("Sports Simulation Engine")
    print("🧪" * 35)

    results = {}

    # Test 1: Event Tokenizer
    results["tokenizer"] = run_command(
        "python scripts/test_tokenizer.py",
        "Event Tokenizer Tests"
    )

    # Test 2: Synthetic Data Generation
    results["synthetic_data"] = run_command(
        "python scripts/generate_synthetic_data.py --num-games 5",
        "Synthetic Data Generation"
    )

    # Test 3: Model Validation (requires PyTorch)
    if Path("requirements.txt").exists():
        print("\n" + "="*70)
        print("Checking PyTorch installation...")
        print("="*70)

        # Check if PyTorch is installed
        try:
            import torch
            print(f"✓ PyTorch installed: {torch.__version__}")
            results["model_validation"] = run_command(
                "python scripts/validate_model.py",
                "Model Architecture Validation"
            )
        except ImportError:
            print("⚠️  PyTorch not installed. Skipping model tests.")
            print("   Install with: pip install torch")
            results["model_validation"] = None

    # Summary
    print("\n\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASSED" if result is True else "❌ FAILED" if result is False else "⏭️  SKIPPED"
        print(f"  {test_name:20s}: {status}")

    print("="*70)
    print(f"Results: {passed}/{total} passed, {failed} failed, {skipped} skipped")
    print("="*70)

    if failed == 0:
        print("\n🎉 All tests passed! The simulation engine is ready to use.")
        print("\nNext steps:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Collect real data: notebooks/01_data_collection.ipynb")
        print("  3. Train the model: Create notebooks/03_model_training.ipynb")
        print("  4. Run simulations: notebooks/05_simulation_engine.ipynb")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
