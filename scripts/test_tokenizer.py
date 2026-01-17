#!/usr/bin/env python3
"""
Simple test script for the event tokenizer.
Can run without pytest - just validates basic functionality.

Usage: python scripts/test_tokenizer.py
"""

import sys
sys.path.insert(0, 'src')

from models.event_tokenizer import SportsEventTokenizer, Event


def print_test(test_name):
    """Helper to print test headers"""
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print('='*60)


def test_basic_functionality():
    """Test basic tokenizer functionality"""
    print_test("Basic Functionality")

    # Create tokenizer
    tokenizer = SportsEventTokenizer()
    print(f"✓ Tokenizer created with {tokenizer.vocab_size} tokens")

    # Check special tokens
    assert tokenizer.token_to_id["<PAD>"] == 0
    assert tokenizer.token_to_id["<START>"] == 1
    assert tokenizer.token_to_id["<END>"] == 2
    print("✓ Special tokens correct")

    # Check base vocabulary
    assert "SHOT_3PT" in tokenizer.token_to_id
    assert "MAKE" in tokenizer.token_to_id
    assert "MISS" in tokenizer.token_to_id
    print("✓ Base vocabulary loaded")

    return tokenizer


def test_player_team_addition(tokenizer):
    """Test adding players and teams"""
    print_test("Adding Players and Teams")

    initial_size = tokenizer.vocab_size

    # Add players
    tokenizer.add_player("lebron_james")
    tokenizer.add_player("stephen_curry")
    tokenizer.add_player("kevin_durant")

    # Add teams
    tokenizer.add_team("LAL")
    tokenizer.add_team("GSW")
    tokenizer.add_team("BKN")

    new_size = tokenizer.vocab_size
    print(f"✓ Added 3 players and 3 teams")
    print(f"  Vocab size: {initial_size} → {new_size} (+{new_size - initial_size})")

    # Verify they exist
    assert "PLAYER_lebron_james" in tokenizer.token_to_id
    assert "TEAM_LAL" in tokenizer.token_to_id
    print("✓ Players and teams are in vocabulary")


def test_event_tokenization(tokenizer):
    """Test tokenizing a single event"""
    print_test("Event Tokenization")

    # Create a 3PT shot event
    event = Event(
        event_type="shot",
        timestamp=680.0,
        quarter=1,
        player_id="stephen_curry",
        team_id="GSW",
        outcome="make",
        shot_type="3PT",
        score_home=3,
        score_away=0
    )

    tokens = tokenizer.tokenize_event(event)

    print(f"✓ Event tokenized into {len(tokens)} tokens")
    print(f"  Tokens: {tokens[:10]}...")  # Show first 10

    # Decode to see what they are
    decoded = tokenizer.decode(tokens)
    print(f"  Decoded: {decoded}")

    assert len(tokens) > 0
    print("✓ Event tokenization successful")


def test_sequence_tokenization(tokenizer):
    """Test tokenizing a sequence of events"""
    print_test("Sequence Tokenization")

    # Create a mini game sequence
    events = [
        Event(
            event_type="shot",
            timestamp=680.0,
            quarter=1,
            player_id="stephen_curry",
            team_id="GSW",
            outcome="make",
            shot_type="3PT",
            score_home=3,
            score_away=0
        ),
        Event(
            event_type="shot",
            timestamp=665.0,
            quarter=1,
            player_id="lebron_james",
            team_id="LAL",
            outcome="make",
            shot_type="2PT",
            score_home=3,
            score_away=2
        ),
        Event(
            event_type="rebound",
            timestamp=650.0,
            quarter=1,
            player_id="kevin_durant",
            team_id="BKN",
            outcome=None,
            score_home=3,
            score_away=2,
            metadata={"rebound_type": "DEF"}
        ),
    ]

    tokens = tokenizer.tokenize_sequence(events)

    print(f"✓ Sequence of {len(events)} events tokenized into {len(tokens)} tokens")

    # Check START and END tokens
    assert tokens[0] == tokenizer.special_tokens["<START>"]
    assert tokens[-1] == tokenizer.special_tokens["<END>"]
    print("✓ Sequence has START and END tokens")

    # Decode
    decoded = tokenizer.decode(tokens)
    print(f"  First 20 tokens: {decoded[:20]}")

    return tokens


def test_save_load(tokenizer):
    """Test saving and loading tokenizer"""
    print_test("Save and Load")

    import tempfile
    import os

    # Save to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name

    try:
        tokenizer.save(temp_path)
        print(f"✓ Tokenizer saved to {temp_path}")

        # Load it back
        loaded_tokenizer = SportsEventTokenizer.load(temp_path)
        print(f"✓ Tokenizer loaded from {temp_path}")

        # Verify vocab size matches
        assert loaded_tokenizer.vocab_size == tokenizer.vocab_size
        print(f"✓ Vocab sizes match: {loaded_tokenizer.vocab_size}")

        # Verify specific tokens
        assert "PLAYER_stephen_curry" in loaded_tokenizer.token_to_id
        assert "TEAM_GSW" in loaded_tokenizer.token_to_id
        print("✓ All tokens preserved after save/load")

    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_realistic_game_scenario():
    """Test a more realistic game scenario"""
    print_test("Realistic Game Scenario")

    tokenizer = SportsEventTokenizer()

    # Add real NBA teams and players
    teams = ["LAL", "GSW", "BKN", "MIA", "BOS"]
    players = [
        "lebron_james", "anthony_davis",
        "stephen_curry", "klay_thompson",
        "kevin_durant", "kyrie_irving",
        "jimmy_butler", "bam_adebayo",
        "jayson_tatum", "jaylen_brown"
    ]

    for team in teams:
        tokenizer.add_team(team)

    for player in players:
        tokenizer.add_player(player)

    print(f"✓ Added {len(teams)} teams and {len(players)} players")

    # Simulate first quarter of a game
    events = []
    score_home = 0
    score_away = 0
    time = 720.0  # 12 minutes

    # A few possessions
    possessions = [
        ("stephen_curry", "GSW", "shot", "3PT", "make", 3),
        ("lebron_james", "LAL", "shot", "2PT", "make", 2),
        ("klay_thompson", "GSW", "shot", "3PT", "miss", 0),
        ("anthony_davis", "LAL", "rebound", None, None, 0),
        ("lebron_james", "LAL", "shot", "2PT", "make", 2),
    ]

    for player, team, event_type, shot_type, outcome, points in possessions:
        if team == "GSW":
            score_home += points
        else:
            score_away += points

        time -= 24  # Shot clock

        event = Event(
            event_type=event_type,
            timestamp=time,
            quarter=1,
            player_id=player,
            team_id=team,
            outcome=outcome,
            shot_type=shot_type,
            score_home=score_home,
            score_away=score_away,
            metadata={"rebound_type": "DEF"} if event_type == "rebound" else None
        )
        events.append(event)

    tokens = tokenizer.tokenize_sequence(events)

    print(f"✓ Simulated {len(events)} events (first quarter)")
    print(f"  Final score: GSW {score_home}, LAL {score_away}")
    print(f"  Total tokens: {len(tokens)}")
    print(f"  Tokens per event: {len(tokens) / len(events):.1f}")

    # Show sample of tokens
    decoded = tokenizer.decode(tokens[:30])
    print(f"\n  First 30 tokens:")
    for i, token in enumerate(decoded[:30]):
        print(f"    {i:2d}: {token}")


def main():
    """Run all tests"""
    print("\n" + "🏀" * 30)
    print("Event Tokenizer Test Suite")
    print("🏀" * 30)

    try:
        # Run tests in sequence
        tokenizer = test_basic_functionality()
        test_player_team_addition(tokenizer)
        test_event_tokenization(tokenizer)
        test_sequence_tokenization(tokenizer)
        test_save_load(tokenizer)
        test_realistic_game_scenario()

        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\nThe tokenizer is working correctly and ready for model training.")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
