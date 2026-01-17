#!/usr/bin/env python3
"""
Test the simulation engine with the trained model.

This script demonstrates:
1. Loading the trained model
2. Setting up a hypothetical season state
3. Running Monte Carlo simulations
4. Evaluating futures bets
5. Calculating betting recommendations
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import pickle
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List
import numpy as np

from models.world_model import SportsWorldModel
from models.event_tokenizer import SportsEventTokenizer
from simulation.engine import FuturesSimulator, SeasonState, TeamState
import pandas as pd


@dataclass
class FuturesBet:
    """Represents a futures betting opportunity"""
    description: str
    team_id: str
    bet_type: str
    market_odds: float  # American odds (e.g., +150, -200)
    model_probability: float
    edge: float
    kelly_fraction: float
    recommendation: str


def american_to_probability(odds: float) -> float:
    """Convert American odds to implied probability"""
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)


def calculate_kelly(edge: float, odds: float) -> float:
    """Calculate Kelly criterion bet sizing"""
    if edge <= 0:
        return 0.0

    if odds > 0:
        decimal_odds = (odds / 100) + 1
    else:
        decimal_odds = (100 / abs(odds)) + 1

    b = decimal_odds - 1  # Net fractional odds
    p = edge + american_to_probability(odds)  # Win probability
    q = 1 - p  # Loss probability

    kelly = (b * p - q) / b
    return max(0, min(kelly, 0.25))  # Cap at 25% (quarter Kelly)


def load_trained_model(checkpoint_path: Path, tokenizer_path: Path):
    """Load the trained model and tokenizer"""
    print("Loading tokenizer...")
    tokenizer = SportsEventTokenizer.load(str(tokenizer_path))

    print(f"Vocabulary size: {tokenizer.vocab_size}")

    print("\nLoading trained model...")
    checkpoint = torch.load(checkpoint_path, map_location='cpu', weights_only=False)

    # Model config from training (must match training hyperparameters)
    d_model = 128
    model = SportsWorldModel(
        vocab_size=tokenizer.vocab_size,
        d_model=d_model,
        n_heads=4,
        n_layers=3,
        d_ff=d_model * 4,  # Same as training: 512
        max_seq_len=512,
        dropout=0.1
    )

    model.load_state_dict(checkpoint['model_state_dict'], strict=False)
    model.eval()

    print(f"Model loaded from epoch {checkpoint['epoch']}")
    print(f"Validation perplexity: {checkpoint['val_perplexity']:.2f}")

    return model, tokenizer


def create_test_season_state(tokenizer: SportsEventTokenizer) -> SeasonState:
    """Create a hypothetical mid-season state"""

    # Create 8 teams with realistic records (halfway through 82-game season)
    teams = {}

    # Get actual team IDs from tokenizer
    team_ids = [token for token in tokenizer.token_to_id.keys()
                if token.startswith('TEAM_') and not token.endswith('_away')
                and not token.endswith('_home')][:8]

    if not team_ids:
        # Fallback if no teams in tokenizer
        team_ids = [f'TEAM_{i}' for i in range(8)]

    # Assign realistic records
    records = [
        (30, 11, 0.732, 1.15),  # Top team (higher strength)
        (28, 13, 0.683, 1.08),  # Contender
        (25, 16, 0.610, 1.02),  # Playoff team
        (23, 18, 0.561, 0.98),  # Bubble team
        (21, 20, 0.512, 0.95),  # .500 team
        (18, 23, 0.439, 0.90),  # Below .500
        (15, 26, 0.366, 0.85),  # Lottery team
        (12, 29, 0.293, 0.80),  # Rebuilding
    ]

    for team_id, (wins, losses, win_pct, strength) in zip(team_ids, records):
        # Strip TEAM_ prefix if present for cleaner display
        clean_team_id = team_id.replace('TEAM_', '')

        teams[clean_team_id] = TeamState(
            team_id=clean_team_id,
            wins=wins,
            losses=losses,
            games_remaining=5,  # Minimal for quick test
            strength_rating=strength,
            injuries=[],  # No injuries for simplicity
            recent_form=[1] * (wins % 10)  # Simplified recent form
        )

    # Create standings DataFrame
    standings_data = []
    for team_id, team_state in teams.items():
        standings_data.append({
            'team': team_id,
            'wins': team_state.wins,
            'losses': team_state.losses,
            'win_pct': team_state.wins / (team_state.wins + team_state.losses)
        })

    standings = pd.DataFrame(standings_data).sort_values('win_pct', ascending=False)

    return SeasonState(
        teams=teams,
        games_played=77,  # Most of season complete
        games_remaining=5,  # Minimal for quick test
        standings=standings
    )


def simulate_playoff_race(
    simulator: FuturesSimulator,
    season_state: SeasonState,
    n_simulations: int = 1000
) -> Dict[str, float]:
    """Run Monte Carlo simulations to estimate playoff probabilities"""

    print(f"\n{'='*60}")
    print(f"Running {n_simulations} Monte Carlo simulations...")
    print(f"{'='*60}\n")

    playoff_counts = {team_id: 0 for team_id in season_state.teams.keys()}
    championship_counts = {team_id: 0 for team_id in season_state.teams.keys()}
    final_records = {team_id: [] for team_id in season_state.teams.keys()}

    for sim_idx in range(n_simulations):
        if (sim_idx + 1) % 100 == 0:
            print(f"Simulation {sim_idx + 1}/{n_simulations}...", end='\r')

        # Simulate remaining season
        sim_results = simulate_remaining_games(simulator, season_state)

        # Determine playoff teams (top 6 make playoffs)
        sorted_teams = sorted(
            sim_results.items(),
            key=lambda x: x[1]['final_wins'],
            reverse=True
        )

        playoff_teams = sorted_teams[:6]
        champion = sorted_teams[0][0]  # Simplification: best record wins

        for team_id, _ in playoff_teams:
            playoff_counts[team_id] += 1

        championship_counts[champion] += 1

        for team_id, results in sim_results.items():
            final_records[team_id].append(results['final_wins'])

    print(f"\nSimulations complete!")

    # Calculate probabilities
    playoff_probs = {
        team_id: count / n_simulations
        for team_id, count in playoff_counts.items()
    }

    championship_probs = {
        team_id: count / n_simulations
        for team_id, count in championship_counts.items()
    }

    return {
        'playoff_probs': playoff_probs,
        'championship_probs': championship_probs,
        'final_records': final_records
    }


def simulate_remaining_games(
    simulator: FuturesSimulator,
    season_state: SeasonState
) -> Dict[str, Dict]:
    """Simulate all remaining games for the season"""

    team_ids = list(season_state.teams.keys())
    results = {
        team_id: {
            'wins': season_state.teams[team_id].wins,
            'losses': season_state.teams[team_id].losses
        }
        for team_id in team_ids
    }

    # Simulate round-robin remaining games
    games_per_team = season_state.teams[team_ids[0]].games_remaining

    for _ in range(games_per_team):
        # Pair up teams randomly
        np.random.shuffle(team_ids)
        for i in range(0, len(team_ids), 2):
            if i + 1 < len(team_ids):
                team1 = team_ids[i]
                team2 = team_ids[i + 1]

                # Simulate game with temperature for variety
                team1_score, team2_score, _ = simulator.simulate_game(
                    team1, team2, temperature=1.2
                )

                if team1_score > team2_score:
                    results[team1]['wins'] += 1
                    results[team2]['losses'] += 1
                else:
                    results[team2]['wins'] += 1
                    results[team1]['losses'] += 1

    # Add final wins
    for team_id in team_ids:
        results[team_id]['final_wins'] = results[team_id]['wins']

    return results


def evaluate_futures_bets(
    season_state: SeasonState,
    simulation_results: Dict,
    market_odds: Dict[str, Dict[str, float]]
) -> List[FuturesBet]:
    """Evaluate futures betting opportunities"""

    bets = []

    # Evaluate playoff bets
    for team_id, prob in simulation_results['playoff_probs'].items():
        if team_id in market_odds['playoffs']:
            odds = market_odds['playoffs'][team_id]
            market_prob = american_to_probability(odds)
            edge = prob - market_prob
            kelly = calculate_kelly(edge, odds)

            if abs(edge) > 0.02:  # Only show if edge > 2%
                recommendation = "BET" if edge > 0.05 else "SMALL BET" if edge > 0.02 else "PASS"

                bets.append(FuturesBet(
                    description=f"{team_id} makes playoffs",
                    team_id=team_id,
                    bet_type="playoffs",
                    market_odds=odds,
                    model_probability=prob,
                    edge=edge,
                    kelly_fraction=kelly,
                    recommendation=recommendation
                ))

    # Evaluate championship bets
    for team_id, prob in simulation_results['championship_probs'].items():
        if team_id in market_odds['championship']:
            odds = market_odds['championship'][team_id]
            market_prob = american_to_probability(odds)
            edge = prob - market_prob
            kelly = calculate_kelly(edge, odds)

            if abs(edge) > 0.01:  # Lower threshold for championship
                recommendation = "BET" if edge > 0.03 else "SMALL BET" if edge > 0.01 else "PASS"

                bets.append(FuturesBet(
                    description=f"{team_id} wins championship",
                    team_id=team_id,
                    bet_type="championship",
                    market_odds=odds,
                    model_probability=prob,
                    edge=edge,
                    kelly_fraction=kelly,
                    recommendation=recommendation
                ))

    return sorted(bets, key=lambda x: abs(x.edge), reverse=True)


def print_season_standings(season_state: SeasonState):
    """Print current season standings"""
    print("\n" + "="*60)
    print("CURRENT SEASON STANDINGS")
    print("="*60)

    sorted_teams = sorted(
        season_state.teams.items(),
        key=lambda x: x[1].wins / (x[1].wins + x[1].losses),
        reverse=True
    )

    print(f"\n{'Rank':<6} {'Team':<20} {'Record':<12} {'Win%':<8} {'Games Rem.'}")
    print("-" * 60)

    for rank, (team_id, record) in enumerate(sorted_teams, 1):
        win_pct = record.wins / (record.wins + record.losses)
        record_str = f"{record.wins}-{record.losses}"
        print(f"{rank:<6} {team_id:<20} {record_str:<12} {win_pct:.3f}    {record.games_remaining}")


def print_simulation_results(season_state: SeasonState, results: Dict):
    """Print simulation results"""
    print("\n" + "="*60)
    print("SIMULATION RESULTS")
    print("="*60)

    # Playoff probabilities
    print("\nPLAYOFF PROBABILITIES (Top 6 make playoffs):")
    print("-" * 60)

    sorted_playoff = sorted(
        results['playoff_probs'].items(),
        key=lambda x: x[1],
        reverse=True
    )

    for team_id, prob in sorted_playoff:
        current_record = season_state.teams[team_id]
        bar_length = int(prob * 30)
        bar = "█" * bar_length + "░" * (30 - bar_length)
        print(f"{team_id:<20} {bar} {prob*100:5.1f}%  ({current_record.wins}-{current_record.losses})")

    # Championship probabilities
    print("\nCHAMPIONSHIP PROBABILITIES:")
    print("-" * 60)

    sorted_champ = sorted(
        results['championship_probs'].items(),
        key=lambda x: x[1],
        reverse=True
    )

    for team_id, prob in sorted_champ[:5]:  # Top 5
        bar_length = int(prob * 40)
        bar = "█" * bar_length + "░" * (40 - bar_length)
        print(f"{team_id:<20} {bar} {prob*100:5.1f}%")


def print_betting_opportunities(bets: List[FuturesBet]):
    """Print betting recommendations"""
    print("\n" + "="*60)
    print("BETTING OPPORTUNITIES")
    print("="*60)

    if not bets:
        print("\nNo significant edges found.")
        return

    print(f"\n{'Bet':<35} {'Odds':<10} {'Model':<10} {'Market':<10} {'Edge':<10} {'Kelly':<10} {'Rec.'}")
    print("-" * 110)

    for bet in bets:
        market_prob = american_to_probability(bet.market_odds)
        odds_str = f"{bet.market_odds:+.0f}"

        edge_indicator = "↑" if bet.edge > 0 else "↓"
        rec_color = "✓" if bet.recommendation == "BET" else "~" if bet.recommendation == "SMALL BET" else "✗"

        print(f"{bet.description:<35} {odds_str:<10} {bet.model_probability*100:5.1f}%    "
              f"{market_prob*100:5.1f}%    {edge_indicator}{abs(bet.edge)*100:5.1f}%    "
              f"{bet.kelly_fraction*100:5.1f}%    {rec_color} {bet.recommendation}")


def main():
    """Main test function"""
    print("="*60)
    print("SPORTS SIMULATION ENGINE TEST")
    print("="*60)

    # Paths
    project_root = Path(__file__).parent.parent
    checkpoint_path = project_root / 'models' / 'checkpoints' / 'best_model.pt'
    tokenizer_path = project_root / 'data' / 'processed' / 'tokenizer.json'

    # Check if files exist
    if not checkpoint_path.exists():
        print(f"\nError: Model checkpoint not found at {checkpoint_path}")
        print("Please train the model first using scripts/train_model.py")
        return

    if not tokenizer_path.exists():
        print(f"\nError: Tokenizer not found at {tokenizer_path}")
        print("Please generate data first using scripts/generate_synthetic_data.py")
        return

    # Load model
    model, tokenizer = load_trained_model(checkpoint_path, tokenizer_path)

    # Create simulator
    print("\nInitializing simulation engine...")
    simulator = FuturesSimulator(model, tokenizer)

    # Create test season state
    print("\nCreating test season state...")
    season_state = create_test_season_state(tokenizer)
    print_season_standings(season_state)

    # Run simulations (10 for quick test, increase to 1000+ for production)
    n_sims = 10
    print(f"\nNote: Running only {n_sims} simulations for quick testing.")
    print("For production use, increase to 1000-10000 simulations for accurate probabilities.\n")
    simulation_results = simulate_playoff_race(simulator, season_state, n_simulations=n_sims)

    # Print results
    print_simulation_results(season_state, simulation_results)

    # Create hypothetical market odds
    team_ids = list(season_state.teams.keys())
    market_odds = {
        'playoffs': {
            team_ids[0]: -400,  # Heavy favorite
            team_ids[1]: -250,  # Strong favorite
            team_ids[2]: -150,  # Moderate favorite
            team_ids[3]: +120,  # Slight underdog
            team_ids[4]: +180,  # Underdog
            team_ids[5]: +300,  # Long shot
            team_ids[6]: +600,  # Very long shot
            team_ids[7]: +1200, # Extreme long shot
        },
        'championship': {
            team_ids[0]: +200,
            team_ids[1]: +350,
            team_ids[2]: +600,
            team_ids[3]: +1200,
            team_ids[4]: +2000,
            team_ids[5]: +5000,
            team_ids[6]: +10000,
            team_ids[7]: +25000,
        }
    }

    # Evaluate bets
    bets = evaluate_futures_bets(season_state, simulation_results, market_odds)
    print_betting_opportunities(bets)

    # Summary statistics
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"\nSimulations run: {n_sims}")
    print(f"Teams analyzed: {len(season_state.teams)}")
    print(f"Betting opportunities with edge > 2%: {len([b for b in bets if abs(b.edge) > 0.02])}")
    print(f"Strong recommendations (BET): {len([b for b in bets if b.recommendation == 'BET'])}")

    # Show expected value for best bet
    if bets:
        best_bet = bets[0]
        print(f"\nBest opportunity: {best_bet.description}")
        print(f"  Edge: {best_bet.edge*100:+.2f}%")
        print(f"  Kelly sizing: {best_bet.kelly_fraction*100:.2f}% of bankroll")

        # Calculate expected value on $100 bet
        if best_bet.market_odds > 0:
            win_amount = 100 * (best_bet.market_odds / 100)
        else:
            win_amount = 100 * (100 / abs(best_bet.market_odds))

        ev = best_bet.model_probability * win_amount - (1 - best_bet.model_probability) * 100
        print(f"  Expected value on $100 bet: ${ev:+.2f}")

    print("\n" + "="*60)
    print("Test complete!")
    print("="*60)


if __name__ == '__main__':
    main()
