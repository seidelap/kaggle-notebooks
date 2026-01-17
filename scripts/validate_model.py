#!/usr/bin/env python3
"""
Validation script for the world model.
Tests model architecture, forward pass, and basic functionality.

This script can check if the model will work before expensive training.

Usage: python scripts/validate_model.py
"""

import sys
sys.path.insert(0, 'src')


def check_imports():
    """Check if required packages are available"""
    print("="*60)
    print("Checking dependencies...")
    print("="*60)

    missing = []

    try:
        import torch
        print(f"✓ PyTorch: {torch.__version__}")
        print(f"  CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"  CUDA version: {torch.version.cuda}")
            print(f"  GPU: {torch.cuda.get_device_name(0)}")
    except ImportError:
        print("✗ PyTorch not found")
        missing.append("torch")

    try:
        import numpy as np
        print(f"✓ NumPy: {np.__version__}")
    except ImportError:
        print("✗ NumPy not found")
        missing.append("numpy")

    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print("\nInstall with: pip install -r requirements.txt")
        return False

    return True


def test_model_creation():
    """Test creating the model"""
    print("\n" + "="*60)
    print("TEST: Model Creation")
    print("="*60)

    import torch
    from models.world_model import SportsWorldModel

    # Create a small model for testing
    model = SportsWorldModel(
        vocab_size=1000,
        d_model=128,
        n_heads=4,
        n_layers=2,
        d_ff=512,
        max_seq_len=256,
        dropout=0.1
    )

    print(f"✓ Model created successfully")

    # Count parameters
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)

    print(f"  Total parameters: {total_params:,}")
    print(f"  Trainable parameters: {trainable_params:,}")
    print(f"  Model size: ~{total_params * 4 / 1024 / 1024:.2f} MB (fp32)")

    return model


def test_forward_pass(model):
    """Test forward pass"""
    print("\n" + "="*60)
    print("TEST: Forward Pass")
    print("="*60)

    import torch

    batch_size = 4
    seq_len = 32
    vocab_size = 1000

    # Create dummy input
    event_tokens = torch.randint(0, vocab_size, (batch_size, seq_len))

    print(f"  Input shape: {event_tokens.shape}")

    # Forward pass
    logits, _ = model(event_tokens)

    print(f"✓ Forward pass successful")
    print(f"  Output shape: {logits.shape}")
    print(f"  Expected: ({batch_size}, {seq_len}, {vocab_size})")

    assert logits.shape == (batch_size, seq_len, vocab_size), "Output shape mismatch!"
    print("✓ Output shape correct")


def test_perplexity_computation(model):
    """Test perplexity calculation"""
    print("\n" + "="*60)
    print("TEST: Perplexity Computation")
    print("="*60)

    import torch

    batch_size = 4
    seq_len = 32
    vocab_size = 1000

    # Create dummy sequence
    event_tokens = torch.randint(0, vocab_size, (batch_size, seq_len))

    # Compute perplexity
    perplexity = model.compute_perplexity(event_tokens)

    print(f"✓ Perplexity computed successfully")
    print(f"  Perplexity: {perplexity.item():.2f}")
    print(f"  (Random model should have perplexity ≈ vocab_size = {vocab_size})")

    # Untrained model should have high perplexity
    assert perplexity.item() > 100, "Perplexity seems too low for untrained model"
    print("✓ Perplexity in expected range for untrained model")


def test_generation(model):
    """Test sequence generation (sampling)"""
    print("\n" + "="*60)
    print("TEST: Sequence Generation")
    print("="*60)

    import torch

    vocab_size = 1000
    start_tokens = torch.randint(0, vocab_size, (1, 10))

    print(f"  Start tokens: {start_tokens.shape}")

    # Generate
    generated = model.generate(
        start_tokens,
        max_new_tokens=20,
        temperature=1.0,
        top_k=50
    )

    print(f"✓ Generation successful")
    print(f"  Generated sequence shape: {generated.shape}")
    print(f"  Length: {generated.shape[1]} (start: 10 + new: 20 = 30)")

    assert generated.shape[1] == 30, "Generated length incorrect"
    print("✓ Generation length correct")


def test_with_context(model):
    """Test model with context embeddings"""
    print("\n" + "="*60)
    print("TEST: Context Embeddings")
    print("="*60)

    import torch

    batch_size = 2
    seq_len = 16
    vocab_size = 1000
    context_dim = 256

    event_tokens = torch.randint(0, vocab_size, (batch_size, seq_len))
    context = torch.randn(batch_size, context_dim)

    print(f"  Event tokens: {event_tokens.shape}")
    print(f"  Context: {context.shape}")

    # Forward with context
    logits, _ = model(event_tokens, context=context)

    print(f"✓ Forward pass with context successful")
    print(f"  Output shape: {logits.shape}")


def test_memory_usage():
    """Test memory requirements"""
    print("\n" + "="*60)
    print("TEST: Memory Usage")
    print("="*60)

    import torch
    from models.world_model import SportsWorldModel

    # Create model similar to config
    model = SportsWorldModel(
        vocab_size=2000,
        d_model=512,
        n_heads=8,
        n_layers=6,
        d_ff=2048,
        max_seq_len=2048
    )

    total_params = sum(p.numel() for p in model.parameters())
    model_size_mb = total_params * 4 / 1024 / 1024  # fp32

    print(f"  Full model parameters: {total_params:,}")
    print(f"  Model size (fp32): {model_size_mb:.2f} MB")
    print(f"  Model size (fp16): {model_size_mb/2:.2f} MB")

    # Estimate memory for batch
    batch_size = 32
    seq_len = 512

    input_memory = batch_size * seq_len * 4 / 1024 / 1024
    activation_memory = batch_size * seq_len * 512 * 6 * 4 / 1024 / 1024  # Rough estimate

    total_memory = model_size_mb + input_memory + activation_memory

    print(f"\n  Estimated memory for training:")
    print(f"    Batch size: {batch_size}, Sequence length: {seq_len}")
    print(f"    Model: {model_size_mb:.2f} MB")
    print(f"    Activations (est): {activation_memory:.2f} MB")
    print(f"    Total (est): {total_memory:.2f} MB")
    print(f"    Recommended VRAM: {total_memory * 2:.0f}+ MB")

    if torch.cuda.is_available():
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024 / 1024
        print(f"\n  Available GPU memory: {gpu_memory:.0f} MB")
        if gpu_memory > total_memory * 2:
            print("  ✓ Sufficient GPU memory available")
        else:
            print("  ⚠️  May need to reduce batch size or sequence length")


def main():
    """Run all validation tests"""
    print("\n" + "🧪" * 30)
    print("World Model Validation Suite")
    print("🧪" * 30 + "\n")

    # Check dependencies
    if not check_imports():
        print("\n❌ Cannot proceed without required packages")
        return 1

    try:
        import torch

        # Run tests
        model = test_model_creation()
        test_forward_pass(model)
        test_perplexity_computation(model)
        test_generation(model)
        test_with_context(model)
        test_memory_usage()

        print("\n" + "="*60)
        print("✅ ALL VALIDATION TESTS PASSED!")
        print("="*60)
        print("\nThe model architecture is correct and ready for training.")
        print("\nNext steps:")
        print("  1. Collect data: notebooks/01_data_collection.ipynb")
        print("  2. Train model: notebooks/03_model_training.ipynb")
        print("  3. Run simulations: notebooks/05_simulation_engine.ipynb")

    except Exception as e:
        print(f"\n❌ VALIDATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
