"""
Unit tests for the Event Tokenizer

Run with: pytest tests/test_event_tokenizer.py -v
"""

import sys
sys.path.insert(0, '../src')

import pytest
from models.event_tokenizer import SportsEventTokenizer, Event


class TestSportsEventTokenizer:
    """Test suite for the event tokenizer"""

    def test_initialization(self):
        """Test that tokenizer initializes with expected vocab"""
        tokenizer = SportsEventTokenizer()

        # Check special tokens
        assert tokenizer.token_to_id["<PAD>"] == 0
        assert tokenizer.token_to_id["<START>"] == 1
        assert tokenizer.token_to_id["<END>"] == 2
        assert tokenizer.token_to_id["<UNK>"] == 3

        # Check that base vocabulary is built
        assert tokenizer.vocab_size > 10  # Should have many tokens
        assert "SHOT_3PT" in tokenizer.token_to_id
        assert "MAKE" in tokenizer.token_to_id
        assert "Q1" in tokenizer.token_to_id

    def test_add_player(self):
        """Test adding player tokens dynamically"""
        tokenizer = SportsEventTokenizer()
        initial_size = tokenizer.vocab_size

        # Add a player
        player_id = tokenizer.add_player("lebron_james")

        # Vocab should grow
        assert tokenizer.vocab_size == initial_size + 1
        assert "PLAYER_lebron_james" in tokenizer.token_to_id

        # Adding same player again shouldn't increase size
        player_id_2 = tokenizer.add_player("lebron_james")
        assert tokenizer.vocab_size == initial_size + 1
        assert player_id == player_id_2

    def test_add_team(self):
        """Test adding team tokens"""
        tokenizer = SportsEventTokenizer()

        team_id = tokenizer.add_team("LAL")
        assert "TEAM_LAL" in tokenizer.token_to_id

        # Check it's retrievable
        token_id = tokenizer.token_to_id["TEAM_LAL"]
        assert tokenizer.id_to_token[token_id] == "TEAM_LAL"

    def test_tokenize_shot_event(self):
        """Test tokenizing a shot event"""
        tokenizer = SportsEventTokenizer()
        tokenizer.add_player("curry")
        tokenizer.add_team("GSW")

        event = Event(
            event_type="shot",
            timestamp=680.0,
            quarter=1,
            player_id="curry",
            team_id="GSW",
            outcome="make",
            shot_type="3PT",
            score_home=3,
            score_away=0
        )

        tokens = tokenizer.tokenize_event(event)

        # Should have multiple tokens
        assert len(tokens) > 0

        # All tokens should be valid IDs
        for token in tokens:
            assert token in tokenizer.id_to_token

    def test_tokenize_sequence(self):
        """Test tokenizing a full game sequence"""
        tokenizer = SportsEventTokenizer()
        tokenizer.add_player("player1")
        tokenizer.add_player("player2")
        tokenizer.add_team("TEAM1")
        tokenizer.add_team("TEAM2")

        events = [
            Event(
                event_type="shot",
                timestamp=680.0,
                quarter=1,
                player_id="player1",
                team_id="TEAM1",
                outcome="make",
                shot_type="3PT",
                score_home=3,
                score_away=0
            ),
            Event(
                event_type="shot",
                timestamp=665.0,
                quarter=1,
                player_id="player2",
                team_id="TEAM2",
                outcome="miss",
                shot_type="2PT",
                score_home=3,
                score_away=0
            ),
        ]

        tokens = tokenizer.tokenize_sequence(events)

        # Should start with START token
        assert tokens[0] == tokenizer.special_tokens["<START>"]

        # Should end with END token
        assert tokens[-1] == tokenizer.special_tokens["<END>"]

        # Should have more tokens than just START and END
        assert len(tokens) > 2

    def test_decode(self):
        """Test decoding token IDs back to strings"""
        tokenizer = SportsEventTokenizer()

        # Get some token IDs
        token_ids = [
            tokenizer.special_tokens["<START>"],
            tokenizer.token_to_id.get("SHOT_3PT", tokenizer.special_tokens["<UNK>"]),
            tokenizer.token_to_id.get("MAKE", tokenizer.special_tokens["<UNK>"]),
            tokenizer.special_tokens["<END>"]
        ]

        # Decode
        decoded = tokenizer.decode(token_ids)

        assert len(decoded) == len(token_ids)
        assert decoded[0] == "<START>"
        assert decoded[-1] == "<END>"

    def test_save_and_load(self, tmp_path):
        """Test saving and loading tokenizer"""
        tokenizer = SportsEventTokenizer()
        tokenizer.add_player("test_player")
        tokenizer.add_team("TEST_TEAM")

        original_vocab_size = tokenizer.vocab_size

        # Save
        save_path = tmp_path / "test_vocab.json"
        tokenizer.save(str(save_path))

        # Load
        loaded_tokenizer = SportsEventTokenizer.load(str(save_path))

        # Check vocab size matches
        assert loaded_tokenizer.vocab_size == original_vocab_size

        # Check specific tokens exist
        assert "PLAYER_test_player" in loaded_tokenizer.token_to_id
        assert "TEAM_TEST_TEAM" in loaded_tokenizer.token_to_id

    def test_unknown_token_handling(self):
        """Test handling of unknown tokens"""
        tokenizer = SportsEventTokenizer()

        # Create event with player that hasn't been added
        event = Event(
            event_type="shot",
            timestamp=680.0,
            quarter=1,
            player_id="unknown_player",
            team_id="unknown_team",
            outcome="make",
            shot_type="3PT",
            score_home=3,
            score_away=0
        )

        tokens = tokenizer.tokenize_event(event)

        # Should contain UNK tokens for unknown player/team
        unk_id = tokenizer.special_tokens["<UNK>"]
        assert unk_id in tokens

    def test_temporal_context_encoding(self):
        """Test that temporal context (time, score) is encoded"""
        tokenizer = SportsEventTokenizer()
        tokenizer.add_player("player1")

        # Event at different times should produce different tokens
        event1 = Event(
            event_type="shot",
            timestamp=720.0,  # Start of quarter
            quarter=1,
            player_id="player1",
            outcome="make",
            shot_type="2PT",
            score_home=0,
            score_away=0
        )

        event2 = Event(
            event_type="shot",
            timestamp=60.0,  # End of quarter
            quarter=1,
            player_id="player1",
            outcome="make",
            shot_type="2PT",
            score_home=25,
            score_away=20
        )

        tokens1 = tokenizer.tokenize_event(event1)
        tokens2 = tokenizer.tokenize_event(event2)

        # Should have different time tokens
        assert tokens1 != tokens2


class TestEvent:
    """Test the Event dataclass"""

    def test_event_creation(self):
        """Test creating an Event object"""
        event = Event(
            event_type="shot",
            timestamp=680.0,
            quarter=1,
            player_id="test_player",
            team_id="TEST",
            outcome="make",
            shot_type="3PT"
        )

        assert event.event_type == "shot"
        assert event.timestamp == 680.0
        assert event.quarter == 1
        assert event.outcome == "make"


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "--tb=short"])
