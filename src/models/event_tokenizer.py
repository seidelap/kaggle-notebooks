"""
Event Tokenizer for Sports Play-by-Play Data

Converts raw play-by-play events into discrete tokens that can be fed to
the autoregressive world model. Design choices:

1. Granularity: Individual plays (shots, rebounds, turnovers, etc.)
2. Hierarchical encoding: Event type + modifiers (e.g., SHOT_3PT + MAKE)
3. Contextual tokens: Player IDs, positions, game state (score, time)

Token vocabulary example:
- Event types: SHOT_2PT, SHOT_3PT, REBOUND, TURNOVER, FOUL, etc.
- Outcomes: MAKE, MISS, OFFENSIVE, DEFENSIVE
- Players: PLAYER_1, PLAYER_2, ..., PLAYER_500
- Context: QUARTER_1, QUARTER_2, SCORE_DIFF_+5, etc.
"""

import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Event:
    """Represents a single play-by-play event"""
    event_type: str  # e.g., "shot", "rebound", "turnover"
    timestamp: float  # Game clock (seconds remaining in quarter)
    quarter: int
    player_id: Optional[str] = None
    team_id: Optional[str] = None
    outcome: Optional[str] = None  # e.g., "make", "miss"
    shot_type: Optional[str] = None  # e.g., "2PT", "3PT"
    score_home: Optional[int] = None
    score_away: Optional[int] = None
    metadata: Optional[Dict] = None  # Extra info


class SportsEventTokenizer:
    """
    Tokenizer for sports play-by-play sequences.

    Design:
    - Composite tokens: Each event becomes multiple tokens
    - Example: 3PT shot by Player 23 that goes in →
      [PLAYER_23, SHOT_3PT, MAKE, SCORE_DIFF_+3, TIME_360]
    """

    def __init__(self):
        # Core vocabulary
        self.token_to_id: Dict[str, int] = {}
        self.id_to_token: Dict[int, str] = {}

        # Special tokens
        self.special_tokens = {
            "<PAD>": 0,
            "<START>": 1,
            "<END>": 2,
            "<UNK>": 3,
            "<MASK>": 4,
        }

        # Initialize with special tokens
        self.token_to_id.update(self.special_tokens)
        self.id_to_token = {v: k for k, v in self.token_to_id.items()}
        self.next_id = len(self.special_tokens)

        # Build vocabulary
        self._build_base_vocabulary()

    def _build_base_vocabulary(self):
        """Build the base vocabulary of event types"""

        # Event types (NBA example)
        event_types = [
            "SHOT_2PT", "SHOT_3PT", "FREE_THROW",
            "REBOUND_OFF", "REBOUND_DEF",
            "ASSIST", "STEAL", "BLOCK",
            "TURNOVER", "FOUL_PERSONAL", "FOUL_SHOOTING",
            "SUBSTITUTION", "TIMEOUT",
            "JUMP_BALL", "VIOLATION",
        ]

        # Outcomes
        outcomes = ["MAKE", "MISS"]

        # Quarters
        quarters = [f"Q{i}" for i in range(1, 6)]  # 1-4 + OT

        # Time buckets (seconds remaining in quarter)
        time_buckets = [
            f"TIME_{i}" for i in range(0, 721, 60)  # 0, 60, 120, ..., 720 (12 min quarters)
        ]

        # Score differential buckets
        score_diffs = [f"SCORE_DIFF_{i:+d}" for i in range(-30, 31, 5)]

        # Add all to vocabulary
        for token in event_types + outcomes + quarters + time_buckets + score_diffs:
            self._add_token(token)

    def _add_token(self, token: str) -> int:
        """Add a token to the vocabulary if it doesn't exist"""
        if token not in self.token_to_id:
            self.token_to_id[token] = self.next_id
            self.id_to_token[self.next_id] = token
            self.next_id += 1
        return self.token_to_id[token]

    def add_player(self, player_id: str):
        """Dynamically add a player token"""
        token = f"PLAYER_{player_id}"
        return self._add_token(token)

    def add_team(self, team_id: str):
        """Dynamically add a team token"""
        token = f"TEAM_{team_id}"
        return self._add_token(token)

    def tokenize_event(self, event: Event) -> List[int]:
        """
        Convert a single event to a sequence of token IDs.

        Strategy: Each event becomes multiple tokens representing:
        1. Who (player/team)
        2. What (event type + outcome)
        3. When (quarter + time)
        4. Context (score differential)

        Returns:
            List of token IDs
        """
        tokens = []

        # Add player/team
        if event.player_id:
            player_token = f"PLAYER_{event.player_id}"
            tokens.append(self.token_to_id.get(player_token, self.special_tokens["<UNK>"]))

        if event.team_id:
            team_token = f"TEAM_{event.team_id}"
            tokens.append(self.token_to_id.get(team_token, self.special_tokens["<UNK>"]))

        # Add event type
        if event.event_type == "shot":
            shot_token = f"SHOT_{event.shot_type}" if event.shot_type else "SHOT_2PT"
            tokens.append(self.token_to_id.get(shot_token, self.special_tokens["<UNK>"]))
        elif event.event_type == "rebound":
            rebound_type = event.metadata.get("rebound_type", "DEF")
            tokens.append(self.token_to_id.get(f"REBOUND_{rebound_type}", self.special_tokens["<UNK>"]))
        else:
            # Generic event type
            event_token = event.event_type.upper()
            tokens.append(self.token_to_id.get(event_token, self.special_tokens["<UNK>"]))

        # Add outcome
        if event.outcome:
            outcome_token = event.outcome.upper()
            tokens.append(self.token_to_id.get(outcome_token, self.special_tokens["<UNK>"]))

        # Add temporal context
        quarter_token = f"Q{event.quarter}"
        tokens.append(self.token_to_id.get(quarter_token, self.special_tokens["<UNK>"]))

        # Time bucket (discretize time)
        time_bucket = int(event.timestamp // 60) * 60
        time_token = f"TIME_{time_bucket}"
        tokens.append(self.token_to_id.get(time_token, self.special_tokens["<UNK>"]))

        # Score differential (discretize to buckets)
        if event.score_home is not None and event.score_away is not None:
            diff = event.score_home - event.score_away
            # Round to nearest 5
            diff_bucket = (diff // 5) * 5
            diff_bucket = max(-30, min(30, diff_bucket))  # Clip to [-30, 30]
            diff_token = f"SCORE_DIFF_{diff_bucket:+d}"
            tokens.append(self.token_to_id.get(diff_token, self.special_tokens["<UNK>"]))

        return tokens

    def tokenize_sequence(self, events: List[Event]) -> List[int]:
        """
        Tokenize a full game sequence.

        Args:
            events: List of Event objects (play-by-play)

        Returns:
            Flat list of token IDs
        """
        tokens = [self.special_tokens["<START>"]]

        for event in events:
            event_tokens = self.tokenize_event(event)
            tokens.extend(event_tokens)

        tokens.append(self.special_tokens["<END>"])
        return tokens

    def decode(self, token_ids: List[int]) -> List[str]:
        """Convert token IDs back to human-readable tokens"""
        return [self.id_to_token.get(tid, "<UNK>") for tid in token_ids]

    def save(self, path: str):
        """Save vocabulary to disk"""
        vocab_data = {
            "token_to_id": self.token_to_id,
            "id_to_token": self.id_to_token,
            "next_id": self.next_id,
        }
        with open(path, 'w') as f:
            json.dump(vocab_data, f, indent=2)
        print(f"Vocabulary saved to {path}")

    @classmethod
    def load(cls, path: str):
        """Load vocabulary from disk"""
        with open(path, 'r') as f:
            vocab_data = json.load(f)

        tokenizer = cls()
        tokenizer.token_to_id = vocab_data["token_to_id"]
        tokenizer.id_to_token = {int(k): v for k, v in vocab_data["id_to_token"].items()}
        tokenizer.next_id = vocab_data["next_id"]
        print(f"Vocabulary loaded from {path}")
        return tokenizer

    @property
    def vocab_size(self) -> int:
        """Return the size of the vocabulary"""
        return len(self.token_to_id)


if __name__ == "__main__":
    # Example usage
    print("Testing Event Tokenizer...")

    # Create tokenizer
    tokenizer = SportsEventTokenizer()

    # Add some players and teams
    tokenizer.add_player("lebron_james")
    tokenizer.add_player("stephen_curry")
    tokenizer.add_team("LAL")
    tokenizer.add_team("GSW")

    print(f"Vocabulary size: {tokenizer.vocab_size}")

    # Example: Tokenize a sequence of events
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
    ]

    tokens = tokenizer.tokenize_sequence(events)
    print(f"\nTokenized sequence: {tokens}")
    print(f"Decoded: {tokenizer.decode(tokens)}")

    # Save/load test
    tokenizer.save("/tmp/test_vocab.json")
    loaded_tokenizer = SportsEventTokenizer.load("/tmp/test_vocab.json")
    print(f"\nLoaded vocabulary size: {loaded_tokenizer.vocab_size}")
    print("Tokenizer ready!")
