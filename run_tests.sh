#!/usr/bin/env bash
set -e

# ========================================================
#  Candidate Screening Agent - Test Suite (macOS / Linux)
# ========================================================

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================================"
echo " Running Candidate Screening Agent Test Suite"
echo "========================================================"
echo ""

echo "[1/2] Running Backend Pytest Suite..."
./backend/venv/bin/python -m pytest -v

echo ""
echo "[2/2] Running Frontend Strict TypeScript Build Check..."
(cd frontend && npm run build)

echo ""
echo "========================================================"
echo " ALL TESTS AND TYPE CHECKS PASSED SUCCESSFULLY!"
echo "========================================================"
