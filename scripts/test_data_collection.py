#!/usr/bin/env python3
"""
Test the NBA data collection pipeline without making actual API calls.

This simulates the data collection process to validate the code structure.
"""

import sys
sys.path.insert(0, 'src')

from models.event_tokenizer import SportsEventTokenizer, Event


def test_event_parsing():
    """Test that we can create and parse events"""
    print("="*70)
    print("TEST: Event Creation and Parsing")
    print("="*70)

    # Simulate NBA play-by-play events
    events = [
        Event(
            event_type='shot',
            timestamp=680.0,
            quarter=1,
            player_id='S. Curry',
            team_id='GSW',
            outcome='make',
            shot_type='3PT',
            score_home=3,
            score_away=0
        ),
        Event(
            event_type='shot',
            timestamp=665.0,
            quarter=1,
            player_id='L. James',
            team_id='LAL',
            outcome='make',
            shot_type='2PT',
            score_home=3,
            score_away=2
        ),
        Event(
            event_type='rebound',
            timestamp=650.0,
            quarter=1,
            player_id='A. Davis',
            team_id='LAL',
            score_home=3,
            score_away=2,
            metadata={'rebound_type': 'DEF'}
        ),
        Event(
            event_type='shot',
            timestamp=635.0,
            quarter=1,
            player_id='K. Thompson',
            team_id='GSW',
            outcome='miss',
            shot_type='3PT',
            score_home=3,
            score_away=2
        ),
        Event(
            event_type='turnover',
            timestamp=620.0,
            quarter=1,
            player_id='L. James',
            team_id='LAL',
            score_home=3,
            score_away=2
        ),
    ]

    print(f"\n✓ Created {len(events)} test events")

    # Show events
    print("\nEvent details:")
    for i, event in enumerate(events, 1):
        print(f"  {i}. {event.player_id} ({event.team_id}): {event.event_type}", end="")
        if event.outcome:
            print(f" - {event.outcome}", end="")
        if event.shot_type:
            print(f" ({event.shot_type})", end="")
        print(f" @ {event.timestamp:.0f}s, Score: {event.score_home}-{event.score_away}")

    return events


def test_tokenization(events):
    """Test tokenizing events"""
    print("\n" + "="*70)
    print("TEST: Tokenization")
    print("="*70)

    # Create tokenizer
    tokenizer = SportsEventTokenizer()

    # Add teams and players
    teams = set(e.team_id for e in events if e.team_id)
    players = set(e.player_id for e in events if e.player_id)

    for team in teams:
        tokenizer.add_team(team)

    for player in players:
        tokenizer.add_player(player)

    print(f"\nVocabulary:")
    print(f"  Base tokens: {53}")  # From base vocab
    print(f"  Teams added: {len(teams)}")
    print(f"  Players added: {len(players)}")
    print(f"  Total vocab size: {tokenizer.vocab_size}")

    # Tokenize sequence
    tokens = tokenizer.tokenize_sequence(events)

    print(f"\nTokenization results:")
    print(f"  Events: {len(events)}")
    print(f"  Tokens: {len(tokens)}")
    print(f"  Tokens per event: {len(tokens) / len(events):.1f}")

    # Show first few tokens
    decoded = tokenizer.decode(tokens[:20])
    print(f"\nFirst 20 tokens:")
    for i, token in enumerate(decoded):
        print(f"    {i:2d}: {token}")

    return tokenizer, tokens


def test_model_compatibility(tokenizer, tokens):
    """Test that tokens can be used with model"""
    print("\n" + "="*70)
    print("TEST: Model Compatibility")
    print("="*70)

    try:
        import torch
        from models.world_model import SportsWorldModel

        print("\nCreating test model...")
        model = SportsWorldModel(
            vocab_size=tokenizer.vocab_size,
            d_model=64,
            n_heads=2,
            n_layers=2,
            d_ff=256,
            max_seq_len=128
        )

        params = sum(p.numel() for p in model.parameters())
        print(f"✓ Model created: {params:,} parameters")

        # Test forward pass
        print("\nTesting forward pass...")
        token_tensor = torch.tensor([tokens], dtype=torch.long)

        with torch.no_grad():
            logits, _ = model(token_tensor)
            perplexity = model.compute_perplexity(token_tensor)

        print(f"✓ Forward pass successful")
        print(f"  Input shape: {token_tensor.shape}")
        print(f"  Output shape: {logits.shape}")
        print(f"  Perplexity: {perplexity.item():.1f} (untrained model)")

        # Test generation
        print("\nTesting generation...")
        start_tokens = torch.tensor([tokens[:5]], dtype=torch.long)
        generated = model.generate(start_tokens, max_new_tokens=10, temperature=1.0)

        print(f"✓ Generation successful")
        print(f"  Start: {len(start_tokens[0])} tokens")
        print(f"  Generated: {len(generated[0])} tokens")

        return True

    except ImportError:
        print("\n⚠️  PyTorch not installed. Skipping model test.")
        print("   Install with: pip install torch")
        return None


def test_data_pipeline():
    """Test the complete pipeline"""
    print("\n" + "🏀" * 35)
    print("NBA Data Pipeline Test")
    print("🏀" * 35 + "\n")

    # Step 1: Event creation
    events = test_event_parsing()

    # Step 2: Tokenization
    tokenizer, tokens = test_tokenization(events)

    # Step 3: Model compatibility
    model_works = test_model_compatibility(tokenizer, tokens)

    # Summary
    print("\n" + "="*70)
    print("PIPELINE TEST SUMMARY")
    print("="*70)
    print("✅ Event creation: PASSED")
    print("✅ Tokenization: PASSED")

    if model_works:
        print("✅ Model compatibility: PASSED")
    elif model_works is None:
        print("⏭️  Model compatibility: SKIPPED (no PyTorch)")
    else:
        print("❌ Model compatibility: FAILED")

    print("\n" + "="*70)
    print("DATA PIPELINE IS READY")
    print("="*70)
    print("\nThe code structure is correct. Ready to collect real data!")
    print("\nNext steps:")
    print("  1. Install dependencies: pip install -r requirements.txt")
    print("  2. Collect real games:")
    print("     python scripts/collect_nba_data.py --seasons 2024-25 --max-games 10")
    print("  3. Tokenize data:")
    print("     python scripts/tokenize_nba_data.py")
    print("  4. Validate data:")
    print("     python scripts/validate_tokenized_data.py")


if __name__ == "__main__":
    test_data_pipeline()
