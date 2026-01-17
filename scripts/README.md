# Testing & Utility Scripts

This directory contains scripts for testing, validation, and data generation.

## Quick Start

```bash
# Run all tests
python scripts/run_all_tests.py

# Test individual components
python scripts/test_tokenizer.py
python scripts/validate_model.py

# Generate synthetic data for testing
python scripts/generate_synthetic_data.py --num-games 100
```

## Scripts Overview

### `run_all_tests.py`
**Comprehensive test runner** that validates the entire pipeline.

```bash
python scripts/run_all_tests.py
```

Runs:
- Event tokenizer tests
- Synthetic data generation
- Model architecture validation (if PyTorch installed)

### `test_tokenizer.py`
**Unit tests for the event tokenizer** without requiring PyTorch.

```bash
python scripts/test_tokenizer.py
```

Tests:
- Basic tokenizer functionality
- Player/team addition
- Event tokenization
- Sequence tokenization
- Save/load functionality
- Realistic game scenarios

### `validate_model.py`
**Model architecture validation** - requires PyTorch.

```bash
python scripts/validate_model.py
```

Tests:
- Model creation
- Forward pass
- Perplexity computation
- Sequence generation
- Context embeddings
- Memory usage estimation

### `generate_synthetic_data.py`
**Synthetic data generator** for testing the training pipeline.

```bash
# Generate 100 synthetic games
python scripts/generate_synthetic_data.py --num-games 100

# Specify output directory
python scripts/generate_synthetic_data.py --num-games 100 --output-dir data/test
```

Generates:
- Realistic play-by-play sequences
- Multiple teams and players
- Tokenized sequences ready for training
- Saves tokenizer and sequences to disk

**Use cases:**
- Test training pipeline without collecting real data
- Validate model convergence on controlled data
- Quick iteration during development

## Test Coverage

### Tokenizer Tests ✅
- [x] Basic functionality
- [x] Vocabulary building
- [x] Event encoding
- [x] Sequence tokenization
- [x] Save/load
- [x] Unknown token handling
- [x] Temporal context encoding

### Model Tests ⚠️ (Requires PyTorch)
- [x] Architecture creation
- [x] Forward pass
- [x] Perplexity calculation
- [x] Sequence generation
- [x] Context embeddings
- [x] Memory estimation

### Integration Tests ⏭️ (TODO)
- [ ] Full training loop
- [ ] Checkpoint save/load
- [ ] Data loading pipeline
- [ ] Simulation engine
- [ ] Bet evaluation

## Adding New Tests

To add tests for new functionality:

1. **Unit tests**: Add to `test_*.py` files
2. **Integration tests**: Create new `test_integration.py`
3. **Update runner**: Add to `run_all_tests.py`

Example:
```python
# tests/test_new_feature.py
def test_my_feature():
    """Test description"""
    result = my_function()
    assert result == expected
```

## Continuous Integration

These scripts are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run tests
  run: python scripts/run_all_tests.py
```

## Troubleshooting

### "Module not found" errors
```bash
# Install dependencies
pip install -r requirements.txt

# Or run from project root
cd /path/to/kaggle-notebooks
python scripts/test_tokenizer.py
```

### PyTorch tests skipped
```bash
# Install PyTorch
pip install torch

# Or use CPU-only version
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### Import errors
Make sure you're running scripts from the project root:
```bash
cd /path/to/kaggle-notebooks
python scripts/script_name.py
```

## Performance Benchmarks

Run benchmarks to validate performance:

```bash
# Tokenizer speed
python -m timeit -s "from scripts.test_tokenizer import *" "test_sequence_tokenization()"

# Model inference speed
python scripts/validate_model.py  # Shows memory usage and parameter count
```

## Development Workflow

1. **Before committing**: Run `python scripts/run_all_tests.py`
2. **Adding features**: Write tests first (TDD)
3. **Debugging**: Use individual test scripts for faster iteration
4. **Performance**: Use synthetic data for quick validation

## Test Data

Synthetic data is saved to `data/synthetic/`:
- `tokenizer.json` - Vocabulary
- `sequences.pkl` - Tokenized game sequences

This data is .gitignored but can be regenerated anytime.
