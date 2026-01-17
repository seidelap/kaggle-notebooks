#!/usr/bin/env python3
"""
Tokenize collected NBA play-by-play data.

Converts raw game events into token sequences ready for model training.

Usage:
    python scripts/tokenize_nba_data.py --input data/raw/nba --output data/processed
"""

import sys
sys.path.insert(0, 'src')

import argparse
import pickle
from pathlib import Path
from tqdm import tqdm
import pandas as pd
import numpy as np

from models.event_tokenizer import SportsEventTokenizer, Event


def load_game_events(game_file):
    """
    Load and parse game events from parquet file.

    Args:
        game_file: Path to parquet file

    Returns:
        List of Event objects
    """
    try:
        df = pd.read_parquet(game_file)

        # Get team abbreviations
        team_abbrevs = {}
        for _, row in df.head(20).iterrows():
            if row.get('teamId') and row.get('teamTricode'):
                team_abbrevs[row['teamId']] = row['teamTricode']

        events = []
        for _, row in df.iterrows():
            event = parse_nba_event(row, team_abbrevs)
            if event:
                events.append(event)

        return events

    except Exception as e:
        print(f"Error loading {game_file}: {e}")
        return []


def parse_nba_event(row, team_abbrevs):
    """Parse NBA API row into Event object"""
    try:
        event_type = row.get('actionType', '')
        period = row.get('period', 1)
        clock = row.get('clock', 'PT00M00.00S')

        # Parse clock
        try:
            clock_str = clock.replace('PT', '').replace('S', '')
            if 'M' in clock_str:
                parts = clock_str.split('M')
                minutes = int(parts[0])
                seconds = float(parts[1]) if len(parts) > 1 else 0.0
                timestamp = minutes * 60 + seconds
            else:
                timestamp = float(clock_str)
        except:
            timestamp = 0.0

        team_id = row.get('teamId')
        team_abbrev = team_abbrevs.get(team_id, f"TEAM_{team_id}") if team_id else None

        player_id = row.get('personId')
        player_name = row.get('playerNameI', '')

        score_home = row.get('scoreHome', 0)
        score_away = row.get('scoreAway', 0)

        description = row.get('description', '')

        # Map event types
        if 'shot' in event_type.lower() or event_type == '1' or event_type == '2':
            if '3PT' in description or 'three' in description.lower():
                shot_type = '3PT'
            elif 'free throw' in description.lower():
                shot_type = 'FT'
            else:
                shot_type = '2PT'

            outcome = 'miss' if 'MISS' in description else 'make'

            return Event(
                event_type='shot',
                timestamp=timestamp,
                quarter=period,
                player_id=player_name if player_name else str(player_id),
                team_id=team_abbrev,
                outcome=outcome,
                shot_type=shot_type,
                score_home=score_home,
                score_away=score_away
            )

        elif 'rebound' in event_type.lower() or event_type == '4':
            rebound_type = 'OFF' if 'offensive' in description.lower() else 'DEF'
            return Event(
                event_type='rebound',
                timestamp=timestamp,
                quarter=period,
                player_id=player_name if player_name else str(player_id),
                team_id=team_abbrev,
                score_home=score_home,
                score_away=score_away,
                metadata={'rebound_type': rebound_type}
            )

        elif 'turnover' in event_type.lower() or event_type == '5':
            return Event(
                event_type='turnover',
                timestamp=timestamp,
                quarter=period,
                player_id=player_name if player_name else str(player_id),
                team_id=team_abbrev,
                score_home=score_home,
                score_away=score_away
            )

        elif 'foul' in event_type.lower() or event_type == '6':
            return Event(
                event_type='foul_personal',
                timestamp=timestamp,
                quarter=period,
                player_id=player_name if player_name else str(player_id),
                team_id=team_abbrev,
                score_home=score_home,
                score_away=score_away
            )

        return None

    except Exception as e:
        return None


def tokenize_dataset(input_dir, output_dir, vocab_size_limit=5000):
    """
    Tokenize all games in the input directory.

    Args:
        input_dir: Directory with raw parquet files
        output_dir: Directory to save tokenized data
        vocab_size_limit: Maximum vocabulary size

    Returns:
        Statistics dictionary
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Find all game files
    game_files = sorted(input_path.glob('*.parquet'))
    print(f"Found {len(game_files)} game files")

    if len(game_files) == 0:
        print(f"No data found in {input_dir}")
        print("Run: python scripts/collect_nba_data.py first")
        return None

    # Initialize tokenizer
    tokenizer = SportsEventTokenizer()

    # First pass: collect all unique players and teams
    print("\nPhase 1: Building vocabulary...")
    all_players = set()
    all_teams = set()
    all_events = []

    for game_file in tqdm(game_files, desc="Loading games"):
        events = load_game_events(game_file)
        all_events.append(events)

        for event in events:
            if event.player_id:
                all_players.add(event.player_id)
            if event.team_id:
                all_teams.add(event.team_id)

    print(f"  Found {len(all_teams)} unique teams")
    print(f"  Found {len(all_players)} unique players")

    # Add to tokenizer
    for team in sorted(all_teams):
        tokenizer.add_team(team)

    # Limit players if too many
    if len(all_players) > vocab_size_limit:
        print(f"  Limiting to most common {vocab_size_limit} players")
        # Count player appearances
        player_counts = {}
        for events in all_events:
            for event in events:
                if event.player_id:
                    player_counts[event.player_id] = player_counts.get(event.player_id, 0) + 1

        # Keep top players
        top_players = sorted(player_counts.items(), key=lambda x: -x[1])[:vocab_size_limit]
        all_players = set(p for p, _ in top_players)

    for player in sorted(all_players):
        tokenizer.add_player(player)

    print(f"\nVocabulary size: {tokenizer.vocab_size}")

    # Second pass: tokenize all games
    print("\nPhase 2: Tokenizing games...")
    tokenized_sequences = []
    sequence_lengths = []

    for events in tqdm(all_events, desc="Tokenizing"):
        if not events:
            continue

        tokens = tokenizer.tokenize_sequence(events)
        tokenized_sequences.append(tokens)
        sequence_lengths.append(len(tokens))

    # Save tokenizer
    tokenizer_path = output_path / 'tokenizer.json'
    tokenizer.save(str(tokenizer_path))
    print(f"\n✓ Tokenizer saved to {tokenizer_path}")

    # Save token sequences
    sequences_path = output_path / 'sequences.pkl'
    with open(sequences_path, 'wb') as f:
        pickle.dump(tokenized_sequences, f)
    print(f"✓ Token sequences saved to {sequences_path}")

    # Save metadata
    metadata = {
        'num_games': len(tokenized_sequences),
        'vocab_size': tokenizer.vocab_size,
        'num_teams': len(all_teams),
        'num_players': len(all_players),
        'total_tokens': sum(sequence_lengths),
        'avg_tokens_per_game': np.mean(sequence_lengths),
        'min_tokens': np.min(sequence_lengths),
        'max_tokens': np.max(sequence_lengths),
        'sequence_lengths': sequence_lengths
    }

    metadata_path = output_path / 'metadata.pkl'
    with open(metadata_path, 'wb') as f:
        pickle.dump(metadata, f)
    print(f"✓ Metadata saved to {metadata_path}")

    return metadata


def main():
    parser = argparse.ArgumentParser(
        description="Tokenize NBA play-by-play data"
    )
    parser.add_argument(
        '--input',
        type=str,
        default='data/raw/nba',
        help='Input directory with raw parquet files'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='data/processed',
        help='Output directory for tokenized data'
    )
    parser.add_argument(
        '--vocab-size-limit',
        type=int,
        default=5000,
        help='Maximum number of players in vocabulary'
    )

    args = parser.parse_args()

    print("🏀" * 35)
    print("NBA Data Tokenization")
    print("🏀" * 35)

    # Tokenize
    stats = tokenize_dataset(
        input_dir=args.input,
        output_dir=args.output,
        vocab_size_limit=args.vocab_size_limit
    )

    if stats:
        # Print statistics
        print("\n" + "="*70)
        print("TOKENIZATION COMPLETE")
        print("="*70)
        print(f"Games processed: {stats['num_games']}")
        print(f"Vocabulary size: {stats['vocab_size']}")
        print(f"  Teams: {stats['num_teams']}")
        print(f"  Players: {stats['num_players']}")
        print(f"Total tokens: {stats['total_tokens']:,}")
        print(f"Avg tokens/game: {stats['avg_tokens_per_game']:.1f}")
        print(f"Token range: {stats['min_tokens']} - {stats['max_tokens']}")
        print("="*70)

        print(f"\nTokenized data saved to: {args.output}")
        print("\nNext step: python scripts/validate_tokenized_data.py")


if __name__ == "__main__":
    main()
