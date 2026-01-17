#!/usr/bin/env python3
"""
Train the sports world model on CPU.

Optimized for the 500-game synthetic dataset (191K tokens).
Uses a smaller model configuration for faster CPU training.

Usage:
    python scripts/train_model.py --epochs 10
"""

import sys
sys.path.insert(0, 'src')

import argparse
import pickle
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader

from models.world_model import SportsWorldModel
from models.event_tokenizer import SportsEventTokenizer


class TokenSequenceDataset(Dataset):
    """Dataset for token sequences"""

    def __init__(self, sequences, max_len=512):
        self.sequences = sequences
        self.max_len = max_len

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        seq = self.sequences[idx]

        # Truncate if too long
        if len(seq) > self.max_len:
            seq = seq[:self.max_len]

        # Convert to tensor
        tokens = torch.tensor(seq, dtype=torch.long)

        return tokens


def collate_fn(batch):
    """Custom collate function to handle variable length sequences"""
    # Find max length in batch
    max_len = max(len(seq) for seq in batch)

    # Pad sequences
    padded = []
    for seq in batch:
        if len(seq) < max_len:
            # Pad with 0 (PAD token)
            padding = torch.zeros(max_len - len(seq), dtype=torch.long)
            seq = torch.cat([seq, padding])
        padded.append(seq)

    return torch.stack(padded)


def train_epoch(model, dataloader, optimizer, device):
    """Train for one epoch"""
    model.train()
    total_loss = 0
    total_tokens = 0

    for batch_idx, batch in enumerate(dataloader):
        batch = batch.to(device)

        # Forward pass
        logits, _ = model(batch[:, :-1])  # Input: all but last token
        targets = batch[:, 1:]  # Target: all but first token

        # Compute loss
        loss = nn.functional.cross_entropy(
            logits.reshape(-1, model.vocab_size),
            targets.reshape(-1),
            ignore_index=0  # Ignore padding
        )

        # Backward pass
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        # Track stats
        batch_tokens = (targets != 0).sum().item()
        total_loss += loss.item() * batch_tokens
        total_tokens += batch_tokens

        # Print progress every 10 batches
        if (batch_idx + 1) % 10 == 0:
            avg_loss = total_loss / total_tokens
            perplexity = torch.exp(torch.tensor(avg_loss)).item()
            print(f'  Batch {batch_idx+1}/{len(dataloader)}: '
                  f'Loss={avg_loss:.4f}, Perplexity={perplexity:.2f}')

    avg_loss = total_loss / total_tokens
    return avg_loss


def evaluate(model, dataloader, device):
    """Evaluate on validation set"""
    model.eval()
    total_loss = 0
    total_tokens = 0

    with torch.no_grad():
        for batch in dataloader:
            batch = batch.to(device)

            logits, _ = model(batch[:, :-1])
            targets = batch[:, 1:]

            loss = nn.functional.cross_entropy(
                logits.reshape(-1, model.vocab_size),
                targets.reshape(-1),
                ignore_index=0
            )

            batch_tokens = (targets != 0).sum().item()
            total_loss += loss.item() * batch_tokens
            total_tokens += batch_tokens

    avg_loss = total_loss / total_tokens
    return avg_loss


def main():
    parser = argparse.ArgumentParser(description="Train sports world model")
    parser.add_argument('--data-dir', type=str, default='data/processed',
                        help='Data directory')
    parser.add_argument('--epochs', type=int, default=5,
                        help='Number of epochs')
    parser.add_argument('--batch-size', type=int, default=8,
                        help='Batch size')
    parser.add_argument('--lr', type=float, default=0.0003,
                        help='Learning rate')
    parser.add_argument('--d-model', type=int, default=128,
                        help='Model dimension')
    parser.add_argument('--n-layers', type=int, default=3,
                        help='Number of layers')
    parser.add_argument('--n-heads', type=int, default=4,
                        help='Number of attention heads')

    args = parser.parse_args()

    print("🏀" * 35)
    print("Sports World Model Training")
    print("🏀" * 35)

    # Load data
    print(f"\nLoading data from {args.data_dir}...")
    data_path = Path(args.data_dir)

    tokenizer = SportsEventTokenizer.load(str(data_path / 'tokenizer.json'))
    print(f"✓ Tokenizer loaded: {tokenizer.vocab_size} tokens")

    with open(data_path / 'sequences.pkl', 'rb') as f:
        sequences = pickle.load(f)
    print(f"✓ Sequences loaded: {len(sequences)} games")

    with open(data_path / 'splits.pkl', 'rb') as f:
        splits = pickle.load(f)

    # Create datasets
    train_sequences = [sequences[i] for i in splits['train']]
    val_sequences = [sequences[i] for i in splits['val']]

    train_dataset = TokenSequenceDataset(train_sequences, max_len=512)
    val_dataset = TokenSequenceDataset(val_sequences, max_len=512)

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=collate_fn
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        collate_fn=collate_fn
    )

    print(f"✓ Train batches: {len(train_loader)}")
    print(f"✓ Val batches: {len(val_loader)}")

    # Create model
    print(f"\nCreating model...")
    device = torch.device('cpu')  # Use CPU

    model = SportsWorldModel(
        vocab_size=tokenizer.vocab_size,
        d_model=args.d_model,
        n_heads=args.n_heads,
        n_layers=args.n_layers,
        d_ff=args.d_model * 4,
        max_seq_len=512
    ).to(device)

    n_params = sum(p.numel() for p in model.parameters())
    print(f"✓ Model created: {n_params:,} parameters")
    print(f"  Architecture: d_model={args.d_model}, layers={args.n_layers}, heads={args.n_heads}")
    print(f"  Device: {device}")

    # Create optimizer
    optimizer = optim.Adam(model.parameters(), lr=args.lr)

    # Training loop
    print(f"\nTraining for {args.epochs} epochs...")
    print("="*70)

    best_val_loss = float('inf')

    for epoch in range(args.epochs):
        epoch_start = time.time()
        print(f"\nEpoch {epoch+1}/{args.epochs}")
        print("-" * 70)

        # Train
        train_loss = train_epoch(model, train_loader, optimizer, device)
        train_perplexity = torch.exp(torch.tensor(train_loss)).item()

        # Validate
        val_loss = evaluate(model, val_loader, device)
        val_perplexity = torch.exp(torch.tensor(val_loss)).item()

        epoch_time = time.time() - epoch_start

        print(f"\nEpoch {epoch+1} Summary:")
        print(f"  Train Loss: {train_loss:.4f}, Perplexity: {train_perplexity:.2f}")
        print(f"  Val Loss: {val_loss:.4f}, Perplexity: {val_perplexity:.2f}")
        print(f"  Time: {epoch_time:.1f}s")

        # Save best model
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            checkpoint_dir = Path('models/checkpoints')
            checkpoint_dir.mkdir(parents=True, exist_ok=True)

            checkpoint = {
                'epoch': epoch + 1,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'train_loss': train_loss,
                'val_loss': val_loss,
                'train_perplexity': train_perplexity,
                'val_perplexity': val_perplexity,
                'vocab_size': tokenizer.vocab_size,
                'd_model': args.d_model,
                'n_layers': args.n_layers,
                'n_heads': args.n_heads
            }

            torch.save(checkpoint, checkpoint_dir / 'best_model.pt')
            print(f"  ✓ Saved checkpoint (best val perplexity: {val_perplexity:.2f})")

    print("\n" + "="*70)
    print("✅ TRAINING COMPLETE")
    print("="*70)
    print(f"\nBest validation perplexity: {torch.exp(torch.tensor(best_val_loss)).item():.2f}")
    print(f"Model saved to: models/checkpoints/best_model.pt")

    # Test generation
    print("\nTesting generation...")
    model.eval()
    test_seq = sequences[0][:10]
    start_tokens = torch.tensor([test_seq], dtype=torch.long)

    with torch.no_grad():
        generated = model.generate(start_tokens, max_new_tokens=20, temperature=1.0)

    print(f"✓ Generated {len(generated[0])} tokens from {len(test_seq)} start tokens")
    print("\nModel ready for simulation!")


if __name__ == "__main__":
    main()
