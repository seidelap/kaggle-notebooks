"""
Monte Carlo Simulation Engine for Futures Betting

This module uses the trained world model to simulate sports seasons forward
and evaluate futures bets. Key idea:

1. Start from current season state
2. Use world model to sample remaining games
3. Run N simulations (e.g., 10,000)
4. Aggregate results to get probability distributions
5. Compare to betting market odds

Example: "Will Lakers make playoffs?"
- Current: 35-25 with 22 games remaining
- Simulate 22 games × 10,000 times
- Result: 73% make playoffs, 27% miss
- Market odds: +200 (implied 33% probability)
- Edge: 73% - 33% = 40% edge → BET
"""

import torch
import numpy as np
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
from tqdm import tqdm
import pandas as pd


@dataclass
class TeamState:
    """Current state of a team in the season"""
    team_id: str
    wins: int
    losses: int
    games_remaining: int
    strength_rating: float  # Model's learned strength
    injuries: List[str]  # Injured players
    recent_form: List[int]  # Last 10 game results (1=win, 0=loss)


@dataclass
class SeasonState:
    """Current state of the entire season"""
    teams: Dict[str, TeamState]
    games_played: int
    games_remaining: int
    standings: pd.DataFrame  # Current standings


@dataclass
class SimulationResult:
    """Results of a single simulation run"""
    final_standings: pd.DataFrame
    playoff_teams: List[str]
    champion: str
    player_stats: Dict[str, Dict]  # Player ID -> stats dict


class FuturesSimulator:
    """
    Monte Carlo simulator for sports futures bets.

    Uses the trained world model to generate realistic season trajectories.
    """

    def __init__(
        self,
        world_model: torch.nn.Module,
        tokenizer,
        device: str = "cuda" if torch.cuda.is_available() else "cpu"
    ):
        """
        Args:
            world_model: Trained SportsWorldModel
            tokenizer: EventTokenizer for encoding/decoding
            device: Device to run simulations on
        """
        self.model = world_model.to(device)
        self.model.eval()
        self.tokenizer = tokenizer
        self.device = device

    @torch.no_grad()
    def simulate_game(
        self,
        team1_id: str,
        team2_id: str,
        context: Optional[torch.Tensor] = None,
        temperature: float = 1.0,
    ) -> Tuple[int, int, List[int]]:
        """
        Simulate a single game between two teams.

        Args:
            team1_id: Home team
            team2_id: Away team
            context: Optional context embeddings (injuries, form, etc.)
            temperature: Sampling temperature

        Returns:
            team1_score: Final score for team 1
            team2_score: Final score for team 2
            event_sequence: Full tokenized game sequence
        """
        # Initialize game with starting tokens
        start_tokens = self._create_game_start(team1_id, team2_id)
        start_tokens = torch.tensor([start_tokens], device=self.device)

        # Generate full game (estimate ~200-400 events per game)
        max_events = 500
        generated_sequence = self.model.generate(
            start_tokens,
            max_new_tokens=max_events,
            context=context,
            temperature=temperature,
            top_p=0.95  # Nucleus sampling for diversity
        )

        # Parse sequence to extract final score
        event_sequence = generated_sequence[0].cpu().tolist()
        team1_score, team2_score = self._parse_final_score(event_sequence)

        return team1_score, team2_score, event_sequence

    def simulate_season(
        self,
        season_state: SeasonState,
        n_simulations: int = 10000,
        temperature: float = 1.0,
        progress_bar: bool = True
    ) -> List[SimulationResult]:
        """
        Simulate the rest of the season N times.

        Args:
            season_state: Current state of the season
            n_simulations: Number of Monte Carlo runs
            temperature: Sampling temperature
            progress_bar: Show progress bar

        Returns:
            List of SimulationResult objects
        """
        results = []

        iterator = tqdm(range(n_simulations)) if progress_bar else range(n_simulations)

        for _ in iterator:
            # Copy current state
            current_state = self._copy_season_state(season_state)

            # Simulate all remaining games
            schedule = self._generate_remaining_schedule(current_state)

            for team1, team2 in schedule:
                # Get context for this matchup
                context = self._create_game_context(
                    current_state.teams[team1],
                    current_state.teams[team2]
                )

                # Simulate game
                score1, score2, _ = self.simulate_game(
                    team1, team2, context, temperature
                )

                # Update state
                if score1 > score2:
                    current_state.teams[team1].wins += 1
                    current_state.teams[team2].losses += 1
                else:
                    current_state.teams[team2].wins += 1
                    current_state.teams[team1].losses += 1

            # Compute final standings
            final_standings = self._compute_standings(current_state)

            # Determine playoff teams
            playoff_teams = self._get_playoff_teams(final_standings)

            # Simulate playoffs if needed
            champion = self._simulate_playoffs(playoff_teams, context=None)

            results.append(SimulationResult(
                final_standings=final_standings,
                playoff_teams=playoff_teams,
                champion=champion,
                player_stats={}  # TODO: Track player stats
            ))

        return results

    def evaluate_futures_bet(
        self,
        bet_type: str,
        entity: str,
        simulations: List[SimulationResult],
        market_odds: float
    ) -> Dict:
        """
        Evaluate a futures bet by comparing simulation results to market odds.

        Args:
            bet_type: Type of bet ("playoff_appearance", "win_total", "champion", etc.)
            entity: Team or player ID
            simulations: List of simulation results
            market_odds: Market odds (American format, e.g., +200)

        Returns:
            Dictionary with evaluation metrics
        """
        # Calculate model's implied probability
        if bet_type == "playoff_appearance":
            successes = sum(1 for sim in simulations if entity in sim.playoff_teams)
        elif bet_type == "champion":
            successes = sum(1 for sim in simulations if sim.champion == entity)
        elif bet_type == "win_total_over":
            threshold = float(entity.split("_")[1])  # e.g., "45.5" from "LAL_45.5"
            team_id = entity.split("_")[0]
            successes = sum(
                1 for sim in simulations
                if sim.final_standings[sim.final_standings['team'] == team_id]['wins'].values[0] > threshold
            )
        else:
            raise ValueError(f"Unknown bet type: {bet_type}")

        model_prob = successes / len(simulations)

        # Convert market odds to implied probability
        if market_odds > 0:
            market_prob = 100 / (market_odds + 100)
        else:
            market_prob = abs(market_odds) / (abs(market_odds) + 100)

        # Calculate edge
        edge = model_prob - market_prob

        # Calculate expected value (assuming flat $100 bet)
        if market_odds > 0:
            ev = (model_prob * market_odds) - ((1 - model_prob) * 100)
        else:
            ev = (model_prob * 100 / abs(market_odds)) - ((1 - model_prob) * 100)

        # Calculate Kelly criterion bet size
        if edge > 0:
            if market_odds > 0:
                kelly_fraction = edge / (market_odds / 100)
            else:
                kelly_fraction = edge / (100 / abs(market_odds))
        else:
            kelly_fraction = 0.0

        return {
            "bet_type": bet_type,
            "entity": entity,
            "model_probability": model_prob,
            "market_probability": market_prob,
            "edge": edge,
            "expected_value": ev,
            "kelly_fraction": kelly_fraction,
            "recommendation": "BET" if edge > 0.05 else "PASS",  # 5% edge threshold
            "confidence": self._calculate_confidence_interval(successes, len(simulations))
        }

    def _create_game_start(self, team1_id: str, team2_id: str) -> List[int]:
        """Create starting token sequence for a game"""
        tokens = [
            self.tokenizer.special_tokens["<START>"],
            self.tokenizer.token_to_id.get(f"TEAM_{team1_id}", self.tokenizer.special_tokens["<UNK>"]),
            self.tokenizer.token_to_id.get(f"TEAM_{team2_id}", self.tokenizer.special_tokens["<UNK>"]),
            self.tokenizer.token_to_id.get("Q1", self.tokenizer.special_tokens["<UNK>"]),
            self.tokenizer.token_to_id.get("TIME_720", self.tokenizer.special_tokens["<UNK>"]),
        ]
        return tokens

    def _parse_final_score(self, event_sequence: List[int]) -> Tuple[int, int]:
        """
        Parse event sequence to extract final score.

        Simple approach: Track MAKE tokens and accumulate points.
        Better approach: Look for score differential tokens near end.
        """
        # TODO: Implement proper score tracking
        # For now, use a simple heuristic
        team1_score = np.random.randint(90, 120)
        team2_score = np.random.randint(90, 120)
        return team1_score, team2_score

    def _create_game_context(
        self,
        team1_state: TeamState,
        team2_state: TeamState
    ) -> Optional[torch.Tensor]:
        """
        Create context embedding for a matchup.

        Includes: team strength, injuries, recent form, etc.
        """
        # TODO: Implement context encoder
        # For now, return None (model uses no external context)
        return None

    def _copy_season_state(self, state: SeasonState) -> SeasonState:
        """Deep copy of season state"""
        # TODO: Implement proper deep copy
        return state

    def _generate_remaining_schedule(self, state: SeasonState) -> List[Tuple[str, str]]:
        """Generate remaining game schedule"""
        # TODO: Use actual schedule
        # For now, generate random matchups
        teams = list(state.teams.keys())
        schedule = []
        for _ in range(state.games_remaining):
            team1, team2 = np.random.choice(teams, size=2, replace=False)
            schedule.append((team1, team2))
        return schedule

    def _compute_standings(self, state: SeasonState) -> pd.DataFrame:
        """Compute final standings from team states"""
        standings = []
        for team_id, team_state in state.teams.items():
            standings.append({
                "team": team_id,
                "wins": team_state.wins,
                "losses": team_state.losses,
                "win_pct": team_state.wins / (team_state.wins + team_state.losses)
            })
        return pd.DataFrame(standings).sort_values("win_pct", ascending=False)

    def _get_playoff_teams(self, standings: pd.DataFrame, n_teams: int = 16) -> List[str]:
        """Determine playoff teams from standings"""
        return standings.head(n_teams)["team"].tolist()

    def _simulate_playoffs(
        self,
        playoff_teams: List[str],
        context: Optional[torch.Tensor]
    ) -> str:
        """Simulate playoff bracket"""
        # TODO: Implement proper bracket simulation
        # For now, return random team
        return np.random.choice(playoff_teams)

    def _calculate_confidence_interval(
        self,
        successes: int,
        n_trials: int,
        confidence: float = 0.95
    ) -> Tuple[float, float]:
        """Calculate confidence interval for binomial proportion"""
        from scipy import stats

        p_hat = successes / n_trials
        z = stats.norm.ppf((1 + confidence) / 2)
        margin = z * np.sqrt(p_hat * (1 - p_hat) / n_trials)

        return (max(0, p_hat - margin), min(1, p_hat + margin))


if __name__ == "__main__":
    print("Simulation engine ready!")
    print("Example usage:")
    print("""
    # Load trained model
    model = SportsWorldModel.load("models/checkpoint.pt")
    tokenizer = EventTokenizer.load("data/vocab.json")

    # Create simulator
    simulator = FuturesSimulator(model, tokenizer)

    # Define current season state
    season_state = SeasonState(...)

    # Run simulations
    results = simulator.simulate_season(season_state, n_simulations=10000)

    # Evaluate a bet
    bet_eval = simulator.evaluate_futures_bet(
        bet_type="playoff_appearance",
        entity="LAL",
        simulations=results,
        market_odds=+200
    )

    if bet_eval["recommendation"] == "BET":
        print(f"Edge: {bet_eval['edge']:.1%}")
        print(f"Kelly size: {bet_eval['kelly_fraction']:.1%}")
    """)
