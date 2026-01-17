# NBA Data Collection Guide

Complete guide for collecting and processing NBA play-by-play data from 2021-2025.

## Quick Start

**Option 1: Full Pipeline (Recommended)**
```bash
# Install dependencies first
pip install -r requirements.txt

# Run everything in one command
bash scripts/prepare_nba_dataset.sh
```

**Option 2: Test Run (10 games per season)**
```bash
bash scripts/prepare_nba_dataset.sh --test
```

**Option 3: Step by Step**
```bash
# 1. Collect raw data
python scripts/collect_nba_data.py --seasons 2021-22 2022-23 2023-24 2024-25

# 2. Tokenize
python scripts/tokenize_nba_data.py

# 3. Validate
python scripts/validate_tokenized_data.py
```

---

## What Gets Collected

### Seasons
- **2021-22**: ~1,230 games
- **2022-23**: ~1,230 games
- **2023-24**: ~1,230 games
- **2024-25**: ~1,230 games (ongoing)

**Total: ~4,900 games**

### Events Per Game
Each game contains ~80-120 events:
- Shots (2PT, 3PT, FT)
- Rebounds (offensive, defensive)
- Turnovers
- Fouls
- Assists

### Expected Token Count
- **Per game**: ~370 tokens (7 tokens per event × 50-60 events)
- **Per season**: ~450K tokens
- **Total (4 seasons)**: ~1.8M tokens

This is sufficient for training a world model!

---

## Data Collection Scripts

### 1. `collect_nba_data.py` - Fetch Play-by-Play

**What it does:**
- Fetches game IDs for each season
- Downloads play-by-play data from NBA Stats API
- Parses events into Event objects
- Saves raw data to parquet files

**Usage:**
```bash
# Full collection (takes ~2-3 hours with rate limiting)
python scripts/collect_nba_data.py --seasons 2021-22 2022-23 2023-24 2024-25

# Test with 10 games
python scripts/collect_nba_data.py --seasons 2024-25 --max-games 10

# Faster collection (risky - may get rate limited)
python scripts/collect_nba_data.py --seasons 2024-25 --delay 0.3
```

**Options:**
- `--seasons`: Space-separated season names (e.g., `2021-22 2022-23`)
- `--max-games`: Limit number of games per season (default: all)
- `--output-dir`: Where to save raw data (default: `data/raw/nba`)
- `--delay`: Seconds between API requests (default: 0.6)

**Output:**
- One parquet file per game in `data/raw/nba/`
- Filename format: `0022400001.parquet` (NBA game ID)

---

### 2. `tokenize_nba_data.py` - Convert to Tokens

**What it does:**
- Loads all raw game files
- Builds vocabulary (teams, players, event types)
- Tokenizes each game into a sequence
- Saves tokenizer and sequences

**Usage:**
```bash
# Standard tokenization
python scripts/tokenize_nba_data.py

# With custom paths
python scripts/tokenize_nba_data.py --input data/raw/nba --output data/processed

# Limit vocabulary size
python scripts/tokenize_nba_data.py --vocab-size-limit 3000
```

**Options:**
- `--input`: Directory with raw parquet files
- `--output`: Directory for tokenized data
- `--vocab-size-limit`: Max number of unique players (default: 5000)

**Output:**
- `data/processed/tokenizer.json` - Vocabulary mapping
- `data/processed/sequences.pkl` - List of tokenized games
- `data/processed/metadata.pkl` - Dataset statistics

---

### 3. `validate_tokenized_data.py` - Verify Data

**What it does:**
- Loads tokenized data
- Checks format consistency
- Tests with actual model
- Creates train/val/test splits

**Usage:**
```bash
python scripts/validate_tokenized_data.py --data-dir data/processed
```

**Validations:**
- ✓ Metadata consistency
- ✓ Vocabulary completeness
- ✓ Token validity (all tokens in vocab)
- ✓ Sequence length distribution
- ✓ Model compatibility (forward pass works)
- ✓ Perplexity computation

**Output:**
- `data/processed/splits.pkl` - Train/val/test indices

---

## Expected Results

### After Collection
```
Total seasons: 4
Total games: 4,920
Raw data size: ~2-3 GB (parquet files)
Collection time: ~2-3 hours
```

### After Tokenization
```
Games processed: 4,920
Vocabulary size: ~5,500
  Teams: 30
  Players: ~5,000 (top frequent players)
  Event types: ~50
Total tokens: ~1,800,000
Avg tokens/game: ~370
```

### After Validation
```
Train: 3,936 games (80%)
Val: 492 games (10%)
Test: 492 games (10%)

All validation tests: PASSED ✅
Model compatibility: VERIFIED ✅
```

---

## Troubleshooting

### API Rate Limiting
**Error**: `429 Too Many Requests`

**Solution**:
- Increase delay: `--delay 1.0`
- Collection will resume from where it stopped (checks for existing files)
- Run again after a few minutes

### Missing Dependencies
**Error**: `ModuleNotFoundError: No module named 'pandas'`

**Solution**:
```bash
pip install -r requirements.txt
```

### Empty Sequences
**Warning**: Some games have very few events

**Cause**:
- Incomplete game data from API
- Parsing errors for specific event types

**Solution**:
- These are automatically filtered during training
- Less than 1% of games typically affected

### Memory Issues
**Error**: `MemoryError` during tokenization

**Solution**:
- Tokenize in batches (modify script to process seasons separately)
- Reduce `--vocab-size-limit` to use fewer players
- Use machine with more RAM (needs ~8GB for full dataset)

---

## Data Quality

### What's Included
- ✅ All shots (2PT, 3PT, FT) with make/miss
- ✅ All rebounds (offensive, defensive)
- ✅ Turnovers
- ✅ Fouls
- ✅ Assists (when available)
- ✅ Game context (score, time, quarter)

### What's Filtered Out
- ❌ Timeouts (not predictive)
- ❌ Substitutions (too frequent, low signal)
- ❌ Violations (rare events)
- ❌ Jump balls (rare)

### Data Sanity Checks
The validation script checks:
1. All tokens valid (in vocabulary)
2. Scores are monotonically increasing
3. Time decreases properly within quarters
4. Reasonable event distribution

---

## Advanced Usage

### Collecting Specific Seasons
```bash
# Only 2024-25 season
python scripts/collect_nba_data.py --seasons 2024-25

# Multiple specific seasons
python scripts/collect_nba_data.py --seasons 2022-23 2023-24
```

### Resume Failed Collection
Collection automatically resumes if interrupted:
```bash
# Run again - will skip already downloaded games
python scripts/collect_nba_data.py --seasons 2021-22 2022-23 2023-24 2024-25
```

### Custom Vocabulary
```bash
# Include more players (larger vocab)
python scripts/tokenize_nba_data.py --vocab-size-limit 10000

# Include fewer players (smaller vocab, faster training)
python scripts/tokenize_nba_data.py --vocab-size-limit 2000
```

### Inspect Tokenized Data
```python
import pickle
from pathlib import Path

# Load tokenizer
from models.event_tokenizer import SportsEventTokenizer
tokenizer = SportsEventTokenizer.load('data/processed/tokenizer.json')

# Load sequences
with open('data/processed/sequences.pkl', 'rb') as f:
    sequences = pickle.load(f)

# Look at first game
first_game = sequences[0]
print(f"Tokens: {len(first_game)}")
print(f"Decoded: {tokenizer.decode(first_game[:20])}")
```

---

## Dataset Statistics

### Token Distribution (Expected)
```
Special tokens: <START>, <END>, <PAD>, <UNK>
Event types: SHOT_2PT, SHOT_3PT, FREE_THROW, REBOUND_*, etc.
Outcomes: MAKE, MISS
Quarters: Q1, Q2, Q3, Q4, Q5 (OT)
Time buckets: TIME_0, TIME_60, ..., TIME_720
Score diffs: SCORE_DIFF_-30 to SCORE_DIFF_+30
Teams: 30 unique
Players: 5,000 most frequent
```

### Most Common Tokens (Typical)
```
1. SHOT_2PT         ~25%
2. MAKE             ~18%
3. MISS             ~12%
4. REBOUND_DEF      ~10%
5. Q1-Q4            ~8%
6. TIME_*           ~8%
7. SCORE_DIFF_*     ~7%
8. Player tokens    ~10%
9. Team tokens      ~2%
```

---

## Next Steps

After data collection is complete:

1. **Review Statistics**
   - Check `data/processed/metadata.pkl` for dataset info
   - Ensure vocab size is reasonable (<10K)
   - Verify train/val/test splits

2. **Start Training**
   - Open `notebooks/03_model_training.ipynb`
   - Train model to minimize perplexity
   - Goal: Perplexity < 50

3. **Monitor Progress**
   - Training time: ~12-24 hours on GPU
   - Track perplexity every epoch
   - Save checkpoints regularly

4. **Evaluate Model**
   - Run simulations with trained model
   - Compare to baseline predictions
   - Identify +EV betting opportunities

---

## API Information

### NBA Stats API
- **URL**: `https://stats.nba.com/stats`
- **Rate Limit**: ~1 request per second (unofficial)
- **Cost**: Free (no API key required)
- **Reliability**: High (official NBA API)

### Data Freshness
- Historical games: Complete and stable
- Current season: Updates daily
- Playoffs: Included when available

### Alternative Data Sources
If NBA API is down:
- **BALLDONTLIE**: Free API with historical data
- **SportsDataIO**: Paid API ($20/month)
- **ESPN API**: Unofficial, may require scraping

---

## Storage Requirements

### Disk Space
- Raw data: ~2-3 GB (parquet files)
- Tokenized data: ~100-200 MB (pickle files)
- Model checkpoints: ~200 MB per checkpoint
- **Total**: ~5-10 GB for full pipeline

### Memory Requirements
- Data collection: ~2 GB RAM
- Tokenization: ~8 GB RAM
- Training: ~8-16 GB VRAM (GPU)

---

## Legal & Ethics

**Data Usage**:
- NBA Stats API is publicly accessible
- Data is for research/educational purposes
- Do not redistribute raw data commercially
- Respect API rate limits

**Responsible Use**:
- This is for educational research
- Sports betting involves risk
- Only bet what you can afford to lose
- Check local gambling laws

---

## Questions?

**Collection fails**:
- Check internet connection
- Verify seasons format: `2024-25` not `2024-2025`
- Try smaller batch first: `--max-games 10`

**Low token counts**:
- Normal for preseason/early season games
- Some games may have data quality issues
- Less than 1% of games typically problematic

**Need help**:
- Check `TESTING.md` for validation tests
- Run `scripts/test_data_collection.py` to verify setup
- Review error messages in console output

---

**Last Updated**: 2026-01-17
**Scripts Version**: 1.0
**Compatible With**: NBA Stats API v3
