# Sports Simulation Engine with Perplexity-Based World Modeling

A cutting-edge sports betting research platform that uses autoregressive transformers to learn the "physics" of sports from play-by-play data and news, then simulates futures to identify betting edges.

## Core Concept

**Perplexity-Based Learning:**
- Train an autoregressive model to predict the next event in a game (next play, next score, etc.)
- Perplexity measures how "surprised" the model is by reality
- Lower perplexity → Better understanding of sport dynamics
- Use the trained model as a simulation engine for futures bets

**Why This Works:**
- Traditional models: Point estimates with confidence intervals
- This approach: Generate full probability distributions via Monte Carlo simulation
- Futures bets require long-horizon predictions (50+ games) where simulation shines
- Can incorporate both structured (play-by-play) and unstructured (news) data

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│ Data Layer                                               │
│ - Play-by-play sequences (NBA Stats API, etc.)         │
│ - News articles & social media (SportsDataIO, APIs)     │
│ - Betting odds & line movements (Odds API)              │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ Event Encoding Layer                                     │
│ - Tokenize sports events: [SHOT_3PT, MAKE, PTS:3, ...]│
│ - Embed news context: Vector representations            │
│ - Temporal encoding: Game state, clock, fatigue         │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ Autoregressive World Model                               │
│ - Transformer architecture (GPT-style)                  │
│ - Input: Event sequence + context embeddings            │
│ - Output: Probability distribution over next events     │
│ - Loss: Cross-entropy (minimizes perplexity)           │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ Simulation Engine (Monte Carlo)                         │
│ - Sample from model's distribution to simulate forward  │
│ - Run 10K+ simulations of remaining season              │
│ - Aggregate: P(team makes playoffs), P(player wins MVP)│
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ Betting Strategy Layer                                   │
│ - Compare simulation probabilities to market odds       │
│ - Kelly criterion for bet sizing                        │
│ - Identify +EV opportunities                            │
└─────────────────────────────────────────────────────────┘
```

## Project Structure

```
kaggle-notebooks/
├── notebooks/
│   ├── 01_data_collection.ipynb       # Collect play-by-play & news
│   ├── 02_event_tokenization.ipynb    # Design event vocabulary
│   ├── 03_model_training.ipynb        # Train autoregressive model
│   ├── 04_perplexity_analysis.ipynb   # Evaluate model understanding
│   ├── 05_simulation_engine.ipynb     # Monte Carlo futures simulation
│   └── 06_betting_strategy.ipynb      # Identify +EV bets
├── src/
│   ├── data/
│   │   ├── collectors.py              # API wrappers for data sources
│   │   ├── preprocessors.py           # Clean & structure raw data
│   │   └── loaders.py                 # PyTorch DataLoaders
│   ├── models/
│   │   ├── event_tokenizer.py         # Sports event → Token mapping
│   │   ├── world_model.py             # Autoregressive transformer
│   │   └── embeddings.py              # Positional, temporal encodings
│   ├── simulation/
│   │   ├── engine.py                  # Monte Carlo simulation
│   │   ├── scenarios.py               # Futures bet scenario definitions
│   │   └── metrics.py                 # Evaluation metrics
│   └── betting/
│       ├── strategy.py                # Kelly criterion, bankroll mgmt
│       └── odds_comparison.py         # Market odds vs. model probs
├── data/
│   ├── raw/                           # Raw API responses
│   ├── processed/                     # Tokenized sequences
│   └── embeddings/                    # Pre-computed embeddings
├── models/
│   └── checkpoints/                   # Saved model weights
├── config/
│   ├── data_sources.yaml              # API keys, endpoints
│   └── model_config.yaml              # Hyperparameters
└── tests/
    └── test_simulation.py             # Validate simulation logic
```

## Initial Target: NBA Futures

**Why NBA:**
- Rich play-by-play data (NBA Stats API)
- High-volume news cycle (easy to test news integration)
- 82-game season (medium-horizon for testing)
- Liquid futures markets (easier to find inefficiencies)
- Fast iteration (games daily during season)

**Target Bets:**
- Team to make playoffs (+200 to +800 range)
- Season win totals (over/under)
- Player props (to win MVP, All-NBA teams)

## Getting Started

See `notebooks/01_data_collection.ipynb` to start collecting NBA play-by-play data and training your first world model.