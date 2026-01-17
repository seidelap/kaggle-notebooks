#!/usr/bin/env python3
"""
Generate synthetic sports data for testing the pipeline.

This creates realistic-looking play-by-play sequences that can be used
to validate the full training pipeline before collecting real data.

Usage: python scripts/generate_synthetic_data.py --num-games 100
"""

import sys
sys.path.insert(0, 'src')

import argparse
import random
from pathlib import Path
import pickle

from models.event_tokenizer import SportsEventTokenizer, Event


class SyntheticGameGenerator:
    """Generate synthetic NBA-style games"""

    def __init__(self):
        self.event_types = [
            ("shot", "2PT", 0.55, 2),  # (type, subtype, make_prob, points)
            ("shot", "3PT", 0.36, 3),
            ("free_throw", None, 0.75, 1),
            ("rebound", "OFF", 1.0, 0),
            ("rebound", "DEF", 1.0, 0),
            ("turnover", None, 1.0, 0),
            ("assist", None, 1.0, 0),
            ("foul_personal", None, 1.0, 0),
        ]

    def generate_possession(
        self,
        team_id: str,
        players: list,
        quarter: int,
        time: float,
        score_home: int,
        score_away: int
    ) -> list:
        """Generate events for a single possession"""
        events = []

        # Randomly pick an event type
        event_type, subtype, success_prob, points = random.choice(self.event_types)
        player = random.choice(players)

        if event_type == "shot":
            # Shot outcome
            made = random.random() < success_prob
            outcome = "make" if made else "miss"

            if made:
                if team_id.endswith("_home"):
                    score_home += points
                else:
                    score_away += points

            events.append(Event(
                event_type="shot",
                timestamp=time,
                quarter=quarter,
                player_id=player,
                team_id=team_id,
                outcome=outcome,
                shot_type=subtype,
                score_home=score_home,
                score_away=score_away
            ))

            if made and random.random() < 0.3:  # 30% chance of assist
                assist_player = random.choice([p for p in players if p != player])
                events.append(Event(
                    event_type="assist",
                    timestamp=time,
                    quarter=quarter,
                    player_id=assist_player,
                    team_id=team_id,
                    score_home=score_home,
                    score_away=score_away
                ))

            if not made:  # Rebound
                rebound_team = team_id if random.random() < 0.3 else "opponent"
                rebound_type = "OFF" if rebound_team == team_id else "DEF"
                events.append(Event(
                    event_type="rebound",
                    timestamp=time - 1,
                    quarter=quarter,
                    player_id=random.choice(players),
                    team_id=team_id,
                    outcome=None,
                    score_home=score_home,
                    score_away=score_away,
                    metadata={"rebound_type": rebound_type}
                ))

        elif event_type == "turnover":
            events.append(Event(
                event_type="turnover",
                timestamp=time,
                quarter=quarter,
                player_id=player,
                team_id=team_id,
                score_home=score_home,
                score_away=score_away
            ))

        elif event_type == "foul_personal":
            events.append(Event(
                event_type="foul_personal",
                timestamp=time,
                quarter=quarter,
                player_id=player,
                team_id=team_id,
                score_home=score_home,
                score_away=score_away
            ))

        return events, score_home, score_away

    def generate_game(self, game_id: int) -> list:
        """Generate a full game"""
        # Team setup
        team_home = f"TEAM_{game_id % 10}_home"
        team_away = f"TEAM_{(game_id + 5) % 10}_away"

        players_home = [f"player_{team_home}_{i}" for i in range(5)]
        players_away = [f"player_{team_away}_{i}" for i in range(5)]

        all_events = []
        score_home = 0
        score_away = 0

        # Generate 4 quarters
        for quarter in range(1, 5):
            time = 720.0  # 12 minutes

            # About 20-25 possessions per quarter
            num_possessions = random.randint(20, 25)

            for _ in range(num_possessions):
                # Alternate possessions (roughly)
                if random.random() < 0.5:
                    team, players = team_home, players_home
                else:
                    team, players = team_away, players_away

                # Generate possession
                possession_events, score_home, score_away = self.generate_possession(
                    team, players, quarter, time, score_home, score_away
                )

                all_events.extend(possession_events)

                # Advance time (possession typically 10-24 seconds)
                time -= random.uniform(10, 24)
                time = max(0, time)

        return all_events, score_home, score_away


def generate_dataset(num_games: int, output_dir: str):
    """Generate a dataset of synthetic games"""
    print(f"Generating {num_games} synthetic games...")

    generator = SyntheticGameGenerator()
    tokenizer = SportsEventTokenizer()

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    all_sequences = []
    all_teams = set()
    all_players = set()

    for game_id in range(num_games):
        events, score_home, score_away = generator.generate_game(game_id)

        # Collect unique teams and players
        for event in events:
            if event.team_id:
                all_teams.add(event.team_id)
            if event.player_id:
                all_players.add(event.player_id)

        if (game_id + 1) % 10 == 0:
            print(f"  Generated {game_id + 1}/{num_games} games")

    # Add all players and teams to tokenizer
    print(f"\nAdding {len(all_teams)} teams and {len(all_players)} players to vocabulary...")
    for team in all_teams:
        tokenizer.add_team(team)
    for player in all_players:
        tokenizer.add_player(player)

    print(f"Vocabulary size: {tokenizer.vocab_size}")

    # Tokenize all games
    print(f"\nTokenizing {num_games} games...")
    for game_id in range(num_games):
        events, _, _ = generator.generate_game(game_id)
        tokens = tokenizer.tokenize_sequence(events)
        all_sequences.append(tokens)

        if (game_id + 1) % 10 == 0:
            print(f"  Tokenized {game_id + 1}/{num_games} games")

    # Save tokenizer
    tokenizer_path = output_path / "tokenizer.json"
    tokenizer.save(str(tokenizer_path))
    print(f"\n✓ Tokenizer saved to {tokenizer_path}")

    # Save sequences
    sequences_path = output_path / "sequences.pkl"
    with open(sequences_path, 'wb') as f:
        pickle.dump(all_sequences, f)
    print(f"✓ Token sequences saved to {sequences_path}")

    # Statistics
    total_tokens = sum(len(seq) for seq in all_sequences)
    avg_tokens = total_tokens / len(all_sequences)

    print("\n" + "="*60)
    print("Dataset Statistics:")
    print("="*60)
    print(f"  Games: {num_games}")
    print(f"  Total tokens: {total_tokens:,}")
    print(f"  Avg tokens per game: {avg_tokens:.1f}")
    print(f"  Vocabulary size: {tokenizer.vocab_size}")
    print(f"  Unique teams: {len(all_teams)}")
    print(f"  Unique players: {len(all_players)}")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic sports data for testing"
    )
    parser.add_argument(
        "--num-games",
        type=int,
        default=100,
        help="Number of games to generate (default: 100)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/synthetic",
        help="Output directory (default: data/synthetic)"
    )

    args = parser.parse_args()

    print("🏀" * 30)
    print("Synthetic Data Generator")
    print("🏀" * 30 + "\n")

    generate_dataset(args.num_games, args.output_dir)

    print("\n✅ Synthetic dataset generated successfully!")
    print("\nYou can now use this data to test the training pipeline:")
    print("  python scripts/test_training.py")


if __name__ == "__main__":
    main()
