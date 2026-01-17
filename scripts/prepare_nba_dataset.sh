#!/bin/bash
# Master script to collect, tokenize, and validate NBA data from 2021-2025
#
# Usage:
#   bash scripts/prepare_nba_dataset.sh           # Full dataset (all 4 seasons)
#   bash scripts/prepare_nba_dataset.sh --test    # Test run (10 games per season)

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀"
echo "NBA Dataset Preparation Pipeline"
echo "Seasons: 2021-22, 2022-23, 2023-24, 2024-25"
echo "🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀🏀"

# Parse arguments
TEST_MODE=false
if [ "$1" == "--test" ]; then
    TEST_MODE=true
    echo -e "${YELLOW}Running in TEST mode (10 games per season)${NC}"
fi

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}Error: Run this script from the project root directory${NC}"
    echo "cd /path/to/kaggle-notebooks && bash scripts/prepare_nba_dataset.sh"
    exit 1
fi

echo ""
echo "=================================================================="
echo "PHASE 1: Data Collection"
echo "=================================================================="

if [ "$TEST_MODE" = true ]; then
    MAX_GAMES="--max-games 10"
else
    MAX_GAMES=""
fi

# Collect data for each season
SEASONS="2021-22 2022-23 2023-24 2024-25"

python scripts/collect_nba_data.py \
    --seasons $SEASONS \
    $MAX_GAMES \
    --output-dir data/raw/nba \
    --delay 0.6

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Data collection failed!${NC}"
    echo "Check if you have the required dependencies:"
    echo "  pip install -r requirements.txt"
    exit 1
fi

echo -e "${GREEN}✓ Data collection complete${NC}"

echo ""
echo "=================================================================="
echo "PHASE 2: Tokenization"
echo "=================================================================="

python scripts/tokenize_nba_data.py \
    --input data/raw/nba \
    --output data/processed \
    --vocab-size-limit 5000

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Tokenization failed!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Tokenization complete${NC}"

echo ""
echo "=================================================================="
echo "PHASE 3: Validation"
echo "=================================================================="

python scripts/validate_tokenized_data.py \
    --data-dir data/processed

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Validation failed!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Validation complete${NC}"

echo ""
echo "=================================================================="
echo "✅ DATASET PREPARATION COMPLETE"
echo "=================================================================="
echo ""
echo "Dataset ready for training:"
echo "  - Tokenizer: data/processed/tokenizer.json"
echo "  - Sequences: data/processed/sequences.pkl"
echo "  - Metadata: data/processed/metadata.pkl"
echo "  - Splits: data/processed/splits.pkl"
echo ""
echo "Next steps:"
echo "  1. Review dataset statistics in the output above"
echo "  2. Start training: notebooks/03_model_training.ipynb"
echo "  3. Monitor perplexity during training (goal: < 50)"
echo ""
echo "=================================================================="
