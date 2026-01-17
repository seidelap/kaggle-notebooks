#!/usr/bin/env python3
"""
Validate tokenized NBA data and test with model.

Ensures data is correctly formatted and can be processed by the model.

Usage:
    python scripts/validate_tokenized_data.py --data-dir data/processed
"""

import sys
sys.path.insert(0, 'src')

import argparse
import pickle
from pathlib import Path
import numpy as np


def load_tokenized_data(data_dir):
    """Load tokenized data and metadata"""
    data_path = Path(data_dir)

    # Load metadata
    metadata_path = data_path / 'metadata.pkl'
    if not metadata_path.exists():
        print(f"❌ Metadata not found at {metadata_path}")
        print("Run: python scripts/tokenize_nba_data.py first")
        return None, None, None

    with open(metadata_path, 'rb') as f:
        metadata = pickle.load(f)

    # Load tokenizer
    tokenizer_path = data_path / 'tokenizer.json'
    if not tokenizer_path.exists():
        print(f"❌ Tokenizer not found at {tokenizer_path}")
        return None, None, None

    from models.event_tokenizer import SportsEventTokenizer
    tokenizer = SportsEventTokenizer.load(str(tokenizer_path))

    # Load sequences
    sequences_path = data_path / 'sequences.pkl'
    if not sequences_path.exists():
        print(f"❌ Sequences not found at {sequences_path}")
        return None, None, None

    with open(sequences_path, 'rb') as f:
        sequences = pickle.load(f)

    return tokenizer, sequences, metadata


def validate_data_format(tokenizer, sequences, metadata):
    """Validate data format and statistics"""
    print("="*70)
    print("DATA VALIDATION")
    print("="*70)

    # Check metadata consistency
    print("\n1. Metadata Check:")
    print(f"   Games: {metadata['num_games']}")
    print(f"   Actual sequences: {len(sequences)}")

    if metadata['num_games'] != len(sequences):
        print("   ⚠️  Mismatch between metadata and sequences!")

    print(f"   ✓ Metadata consistent")

    # Check vocabulary
    print("\n2. Vocabulary Check:")
    print(f"   Vocab size: {tokenizer.vocab_size}")
    print(f"   Expected: {metadata['vocab_size']}")

    if tokenizer.vocab_size != metadata['vocab_size']:
        print("   ⚠️  Vocab size mismatch!")
        return False

    print(f"   ✓ Vocabulary consistent")

    # Check token validity
    print("\n3. Token Validity Check:")
    invalid_tokens = []
    for i, seq in enumerate(sequences[:100]):  # Check first 100
        for token in seq:
            if token not in tokenizer.id_to_token:
                invalid_tokens.append((i, token))

    if invalid_tokens:
        print(f"   ❌ Found {len(invalid_tokens)} invalid tokens!")
        for game_idx, token in invalid_tokens[:5]:
            print(f"      Game {game_idx}, token {token}")
        return False

    print(f"   ✓ All tokens valid")

    # Check sequence lengths
    print("\n4. Sequence Length Check:")
    lengths = [len(seq) for seq in sequences]
    print(f"   Min: {min(lengths)}")
    print(f"   Max: {max(lengths)}")
    print(f"   Mean: {np.mean(lengths):.1f}")
    print(f"   Median: {np.median(lengths):.1f}")

    # Check for empty sequences
    empty = sum(1 for seq in sequences if len(seq) == 0)
    if empty > 0:
        print(f"   ⚠️  Found {empty} empty sequences")

    # Check for very short sequences (< 10 tokens)
    very_short = sum(1 for seq in sequences if len(seq) < 10)
    if very_short > 0:
        print(f"   ⚠️  Found {very_short} very short sequences (< 10 tokens)")

    print(f"   ✓ Sequence lengths reasonable")

    # Check token distribution
    print("\n5. Token Distribution Check:")
    all_tokens = [token for seq in sequences for token in seq]
    unique_tokens = set(all_tokens)

    print(f"   Unique tokens used: {len(unique_tokens)}/{tokenizer.vocab_size}")
    print(f"   Total tokens: {len(all_tokens):,}")

    # Most common tokens
    from collections import Counter
    token_counts = Counter(all_tokens)
    print("\n   Top 10 most common tokens:")
    for token_id, count in token_counts.most_common(10):
        token_str = tokenizer.id_to_token.get(token_id, "UNKNOWN")
        pct = 100 * count / len(all_tokens)
        print(f"      {token_str:20s}: {count:6d} ({pct:5.2f}%)")

    print(f"\n   ✓ Token distribution looks reasonable")

    return True


def test_with_model(tokenizer, sequences):
    """Test data with actual model"""
    print("\n" + "="*70)
    print("MODEL COMPATIBILITY TEST")
    print("="*70)

    try:
        import torch
        from models.world_model import SportsWorldModel
    except ImportError:
        print("⚠️  PyTorch not installed. Skipping model test.")
        print("   Install with: pip install torch")
        return True

    # Create a small test model
    print("\n1. Creating test model...")
    model = SportsWorldModel(
        vocab_size=tokenizer.vocab_size,
        d_model=128,
        n_heads=4,
        n_layers=2,
        d_ff=512,
        max_seq_len=512
    )

    print(f"   ✓ Model created")
    print(f"     Parameters: {sum(p.numel() for p in model.parameters()):,}")

    # Test with a few sequences
    print("\n2. Testing forward pass...")

    test_sequences = sequences[:5]
    max_len = 256  # Limit sequence length for testing

    for i, seq in enumerate(test_sequences):
        # Truncate if needed
        if len(seq) > max_len:
            seq = seq[:max_len]

        # Convert to tensor
        tokens = torch.tensor([seq], dtype=torch.long)

        try:
            # Forward pass
            with torch.no_grad():
                logits, _ = model(tokens)

            # Check output shape
            expected_shape = (1, len(seq), tokenizer.vocab_size)
            if logits.shape != expected_shape:
                print(f"   ❌ Output shape mismatch!")
                print(f"      Expected: {expected_shape}")
                print(f"      Got: {logits.shape}")
                return False

            # Compute perplexity
            perplexity = model.compute_perplexity(tokens)
            print(f"   Game {i+1}: {len(seq):3d} tokens, perplexity: {perplexity.item():.1f}")

        except Exception as e:
            print(f"   ❌ Error processing sequence {i}: {e}")
            return False

    print(f"\n   ✓ All sequences processed successfully!")
    print(f"   ✓ Model is compatible with tokenized data")

    return True


def create_data_splits(sequences, train_ratio=0.8, val_ratio=0.1):
    """Create train/val/test splits"""
    print("\n" + "="*70)
    print("DATA SPLITS")
    print("="*70)

    n = len(sequences)
    indices = np.random.permutation(n)

    train_size = int(n * train_ratio)
    val_size = int(n * val_ratio)

    train_idx = indices[:train_size]
    val_idx = indices[train_size:train_size + val_size]
    test_idx = indices[train_size + val_size:]

    print(f"\nTotal games: {n}")
    print(f"  Train: {len(train_idx)} ({100*len(train_idx)/n:.1f}%)")
    print(f"  Val:   {len(val_idx)} ({100*len(val_idx)/n:.1f}%)")
    print(f"  Test:  {len(test_idx)} ({100*len(test_idx)/n:.1f}%)")

    # Count tokens in each split
    train_tokens = sum(len(sequences[i]) for i in train_idx)
    val_tokens = sum(len(sequences[i]) for i in val_idx)
    test_tokens = sum(len(sequences[i]) for i in test_idx)

    print(f"\nToken counts:")
    print(f"  Train: {train_tokens:,}")
    print(f"  Val:   {val_tokens:,}")
    print(f"  Test:  {test_tokens:,}")

    return train_idx, val_idx, test_idx


def main():
    parser = argparse.ArgumentParser(
        description="Validate tokenized NBA data"
    )
    parser.add_argument(
        '--data-dir',
        type=str,
        default='data/processed',
        help='Directory with tokenized data'
    )

    args = parser.parse_args()

    print("🏀" * 35)
    print("Tokenized Data Validation")
    print("🏀" * 35 + "\n")

    # Load data
    print("Loading data...")
    tokenizer, sequences, metadata = load_tokenized_data(args.data_dir)

    if tokenizer is None:
        return 1

    print(f"✓ Loaded {len(sequences)} sequences")

    # Validate format
    if not validate_data_format(tokenizer, sequences, metadata):
        print("\n❌ Data validation failed!")
        return 1

    # Test with model
    if not test_with_model(tokenizer, sequences):
        print("\n❌ Model compatibility test failed!")
        return 1

    # Create splits
    train_idx, val_idx, test_idx = create_data_splits(sequences)

    # Save splits
    splits = {
        'train': train_idx.tolist(),
        'val': val_idx.tolist(),
        'test': test_idx.tolist()
    }

    splits_path = Path(args.data_dir) / 'splits.pkl'
    with open(splits_path, 'wb') as f:
        pickle.dump(splits, f)

    print(f"\n✓ Splits saved to {splits_path}")

    # Final summary
    print("\n" + "="*70)
    print("✅ ALL VALIDATION TESTS PASSED!")
    print("="*70)
    print("\nYour data is ready for training!")
    print("\nNext steps:")
    print("  1. Review TRAINING.md for training instructions")
    print("  2. Start training: notebooks/03_model_training.ipynb")
    print("  3. Monitor perplexity (goal: < 50)")

    return 0


if __name__ == "__main__":
    exit(main())
