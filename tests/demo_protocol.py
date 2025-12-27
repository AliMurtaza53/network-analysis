#!/usr/bin/env python
"""Demo: Complete testing protocol workflow

This demonstrates how to:
1. Run performance tests
2. Compare baseline vs candidate
3. Interpret results for merge decisions
"""
import subprocess
import sys
import os

def run_command(cmd, description):
    """Run a command and print output."""
    print(f"\n{'='*70}")
    print(f"STEP: {description}")
    print(f"{'='*70}")
    print(f"Running: {cmd}\n")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr, file=sys.stderr)
    return result.returncode

def main():
    print("NETWORK ANALYSIS TESTING PROTOCOL DEMO")
    print("=" * 70)
    
    # Step 1: Run tests on current implementation
    step1 = run_command(
        "python -m tests.run_protocol "
        "--tests tests/protocol/siouxfalls_10_aec.txt tests/protocol/siouxfalls_eqm_aec.txt "
        "--func averageExcessCost "
        "--runs 5 "
        "--output demo_current.csv "
        "--json demo_current.json",
        "Run performance tests on current implementation"
    )
    
    if step1 != 0:
        print("\n❌ Failed to run current tests")
        return 1
    
    # Step 2: For demo purposes, we'll compare against itself
    # In real workflow, you'd checkout a different branch
    print("\n" + "="*70)
    print("NOTE: In real workflow, you would:")
    print("  1. Save current results as baseline")
    print("  2. Checkout/modify implementation")
    print("  3. Run tests again as candidate")
    print("  4. Compare the two")
    print("="*70)
    
    # Step 3: Compare (using same file for demo)
    step3 = run_command(
        "python -m tests.compare_results "
        "demo_current.csv demo_current.csv "
        "--format markdown",
        "Compare baseline vs candidate"
    )
    
    # Step 4: Show CSV contents
    print("\n" + "="*70)
    print("DETAILED CSV OUTPUT:")
    print("="*70)
    if os.path.exists("demo_current.csv"):
        with open("demo_current.csv", "r") as f:
            print(f.read())
    
    # Cleanup
    print("\n" + "="*70)
    print("CLEANUP")
    print("="*70)
    for f in ["demo_current.csv", "demo_current.json"]:
        if os.path.exists(f):
            os.remove(f)
            print(f"Removed {f}")
    
    print("\n" + "="*70)
    print("✅ DEMO COMPLETE")
    print("="*70)
    print("\nNext steps:")
    print("1. Read tests/README.md for detailed usage")
    print("2. Create custom test specs in tests/protocol/")
    print("3. Run protocol on your branches to compare implementations")
    print("4. Use GitHub Actions for automatic PR testing")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
