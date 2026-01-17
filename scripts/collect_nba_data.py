#!/usr/bin/env python3
"""
Collect real NBA play-by-play data from 2021-2025 seasons.

Uses the free NBA Stats API to download game data and convert to Event objects.

Usage:
    python scripts/collect_nba_data.py --seasons 2021-22 2022-23 2023-24 2024-25
    python scripts/collect_nba_data.py --seasons 2024-25 --max-games 10  # Test run
"""

import sys
sys.path.insert(0, 'src')

import argparse
import time
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
import json

from models.event_tokenizer import SportsEventTokenizer, Event


class NBADataCollector:
    """Collect NBA play-by-play data from stats.nba.com"""

    BASE_URL = "https://stats.nba.com/stats"

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Host': 'stats.nba.com',
        'Connection': 'keep-alive',
        'Referer': 'https://www.nba.com/',
        'x-nba-stats-origin': 'stats',
        'x-nba-stats-token': 'true'
    }

    def __init__(self, output_dir='data/raw/nba', delay=0.6):
        """
        Args:
            output_dir: Where to save raw game data
            delay: Seconds between API requests (respect rate limits)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.delay = delay

    def get_season_game_ids(self, season='2024-25'):
        """
        Get all game IDs for a season.

        Args:
            season: Season string (e.g., '2024-25')

        Returns:
            List of (game_id, date, home_team, away_team) tuples
        """
        print(f"Fetching game list for {season}...")

        endpoint = f"{self.BASE_URL}/leaguegamefinder"
        params = {
            'Season': season,
            'SeasonType': 'Regular Season',
            'LeagueID': '00'
        }

        try:
            response = requests.get(endpoint, headers=self.HEADERS, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if 'resultSets' not in data or len(data['resultSets']) == 0:
                print(f"No data found for season {season}")
                return []

            # Parse game data
            headers = data['resultSets'][0]['headers']
            rows = data['resultSets'][0]['rowSet']

            # Find column indices
            game_id_idx = headers.index('GAME_ID')
            date_idx = headers.index('GAME_DATE')
            matchup_idx = headers.index('MATCHUP')

            games = {}
            for row in rows:
                game_id = row[game_id_idx]
                if game_id not in games:
                    games[game_id] = {
                        'date': row[date_idx],
                        'matchup': row[matchup_idx]
                    }

            game_list = [(gid, info['date'], info['matchup']) for gid, info in games.items()]
            print(f"  Found {len(game_list)} games for {season}")
            return game_list

        except Exception as e:
            print(f"Error fetching games for {season}: {e}")
            return []

    def get_play_by_play(self, game_id):
        """
        Get play-by-play data for a specific game.

        Args:
            game_id: NBA game ID (e.g., '0022400001')

        Returns:
            DataFrame with play-by-play events, or None if error
        """
        endpoint = f"{self.BASE_URL}/playbyplayv3"
        params = {
            'GameID': game_id,
            'StartPeriod': 0,
            'EndPeriod': 10
        }

        try:
            response = requests.get(endpoint, headers=self.HEADERS, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if 'game' not in data or 'actions' not in data['game']:
                return None

            # Convert to DataFrame
            actions = data['game']['actions']
            df = pd.DataFrame(actions)

            return df

        except Exception as e:
            print(f"  Error fetching game {game_id}: {e}")
            return None

    def parse_event(self, row, team_abbrevs) -> Event:
        """
        Parse a play-by-play row into an Event object.

        Args:
            row: DataFrame row from NBA API
            team_abbrevs: Dict mapping team IDs to abbreviations

        Returns:
            Event object or None if not parseable
        """
        try:
            # Extract basic info
            event_type = row.get('actionType', '')
            period = row.get('period', 1)
            clock = row.get('clock', 'PT00M00.00S')

            # Parse clock (format: PT12M00.00S = 12:00.00)
            try:
                # Extract minutes and seconds
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

            # Get team and player
            team_id = row.get('teamId')
            team_abbrev = team_abbrevs.get(team_id, f"TEAM_{team_id}") if team_id else None

            player_id = row.get('personId')
            player_name = row.get('playerNameI', '')  # Format: "J. Smith"

            # Get score
            score_home = row.get('scoreHome', 0)
            score_away = row.get('scoreAway', 0)

            # Parse event type
            description = row.get('description', '')
            sub_type = row.get('subType', '')

            # Map NBA event types to our event types
            if 'shot' in event_type.lower() or event_type == '1' or event_type == '2':
                # Determine shot type
                if '3PT' in description or 'three' in description.lower():
                    shot_type = '3PT'
                elif 'free throw' in description.lower() or 'FT' in description:
                    shot_type = 'FT'
                else:
                    shot_type = '2PT'

                # Determine outcome
                if 'MISS' in description or row.get('shotResult') == 'Missed':
                    outcome = 'miss'
                else:
                    outcome = 'make'

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

            # Skip other event types (timeouts, violations, etc.)
            return None

        except Exception as e:
            # Silently skip unparseable events
            return None

    def process_game(self, game_id, game_info):
        """
        Download and process a single game.

        Returns:
            List of Event objects, or None if error
        """
        # Check if already downloaded
        save_path = self.output_dir / f"{game_id}.parquet"
        if save_path.exists():
            return "cached"

        # Get play-by-play data
        df = self.get_play_by_play(game_id)
        if df is None or df.empty:
            return None

        # Get team abbreviations from first few rows
        team_abbrevs = {}
        for _, row in df.head(20).iterrows():
            if row.get('teamId') and row.get('teamTricode'):
                team_abbrevs[row['teamId']] = row['teamTricode']

        # Parse all events
        events = []
        for _, row in df.iterrows():
            event = self.parse_event(row, team_abbrevs)
            if event:
                events.append(event)

        if not events:
            return None

        # Save raw dataframe for reference
        df.to_parquet(save_path, index=False)

        return events

    def collect_seasons(self, seasons, max_games_per_season=None):
        """
        Collect data for multiple seasons.

        Args:
            seasons: List of season strings (e.g., ['2021-22', '2022-23'])
            max_games_per_season: Max games to collect per season (None = all)

        Returns:
            Dictionary: {season: {game_id: [Event, Event, ...]}}
        """
        all_data = {}

        for season in seasons:
            print(f"\n{'='*70}")
            print(f"Processing season: {season}")
            print('='*70)

            # Get game IDs
            game_list = self.get_season_game_ids(season)

            if max_games_per_season:
                game_list = game_list[:max_games_per_season]
                print(f"Limiting to first {max_games_per_season} games")

            season_data = {}
            cached = 0
            downloaded = 0
            failed = 0

            for game_id, date, matchup in tqdm(game_list, desc=f"{season} games"):
                result = self.process_game(game_id, {'date': date, 'matchup': matchup})

                if result == "cached":
                    cached += 1
                elif result is not None:
                    season_data[game_id] = result
                    downloaded += 1
                else:
                    failed += 1

                # Rate limiting
                if result != "cached":
                    time.sleep(self.delay)

            all_data[season] = season_data

            print(f"\n{season} Summary:")
            print(f"  Downloaded: {downloaded}")
            print(f"  Cached: {cached}")
            print(f"  Failed: {failed}")
            print(f"  Total events: {sum(len(events) for events in season_data.values()):,}")

        return all_data


def main():
    parser = argparse.ArgumentParser(
        description="Collect and tokenize NBA play-by-play data"
    )
    parser.add_argument(
        '--seasons',
        nargs='+',
        default=['2024-25'],
        help='Seasons to collect (e.g., 2021-22 2022-23 2023-24 2024-25)'
    )
    parser.add_argument(
        '--max-games',
        type=int,
        default=None,
        help='Max games per season (for testing)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='data/raw/nba',
        help='Output directory for raw data'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=0.6,
        help='Delay between API requests (seconds)'
    )

    args = parser.parse_args()

    print("🏀" * 35)
    print("NBA Data Collection")
    print(f"Seasons: {', '.join(args.seasons)}")
    print("🏀" * 35)

    # Create collector
    collector = NBADataCollector(
        output_dir=args.output_dir,
        delay=args.delay
    )

    # Collect data
    all_data = collector.collect_seasons(
        seasons=args.seasons,
        max_games_per_season=args.max_games
    )

    # Summary
    total_games = sum(len(season_data) for season_data in all_data.values())
    total_events = sum(
        sum(len(events) for events in season_data.values())
        for season_data in all_data.values()
    )

    print("\n" + "="*70)
    print("COLLECTION COMPLETE")
    print("="*70)
    print(f"Total seasons: {len(args.seasons)}")
    print(f"Total games: {total_games}")
    print(f"Total events: {total_events:,}")
    print(f"Avg events/game: {total_events/total_games if total_games > 0 else 0:.1f}")
    print("="*70)

    print(f"\nRaw data saved to: {args.output_dir}")
    print("\nNext step: python scripts/tokenize_nba_data.py")


if __name__ == "__main__":
    main()
