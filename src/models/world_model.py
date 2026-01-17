"""
Autoregressive World Model for Sports Simulation

This module implements a GPT-style transformer that learns to predict the next
event in a sports game. By minimizing perplexity on real play-by-play sequences,
the model learns the "physics" of the sport and can be used as a simulation engine.

Key Features:
- Causal (autoregressive) attention mask
- Multi-head self-attention
- Positional + temporal encodings
- Outputs probability distribution over next events
- Can be sampled from to generate realistic game simulations
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math
from typing import Optional, Tuple


class SportsWorldModel(nn.Module):
    """
    Autoregressive transformer for sports event prediction.

    Architecture:
        Input: Sequence of tokenized events [e_1, e_2, ..., e_t]
        Output: P(e_{t+1} | e_1, ..., e_t)

    Training:
        - Loss: Cross-entropy on next event prediction
        - Metric: Perplexity = exp(cross_entropy)
        - Goal: Minimize perplexity → Model understands sport dynamics

    Inference (Simulation):
        - Sample e_{t+1} ~ P(e_{t+1} | context)
        - Autoregressively generate full game/season trajectories
    """

    def __init__(
        self,
        vocab_size: int,
        d_model: int = 512,
        n_heads: int = 8,
        n_layers: int = 6,
        d_ff: int = 2048,
        max_seq_len: int = 2048,
        dropout: float = 0.1,
        context_dim: int = 256,  # For news/context embeddings
    ):
        """
        Args:
            vocab_size: Number of unique event types (e.g., SHOT_3PT, REBOUND, etc.)
            d_model: Embedding dimension
            n_heads: Number of attention heads
            n_layers: Number of transformer blocks
            d_ff: Feedforward dimension
            max_seq_len: Maximum sequence length
            dropout: Dropout probability
            context_dim: Dimension of context embeddings (news, game state, etc.)
        """
        super().__init__()

        self.d_model = d_model
        self.vocab_size = vocab_size

        # Token embedding
        self.token_embedding = nn.Embedding(vocab_size, d_model)

        # Positional encoding (learned)
        self.pos_embedding = nn.Embedding(max_seq_len, d_model)

        # Context projection (for news/external context)
        self.context_proj = nn.Linear(context_dim, d_model)

        # Transformer layers
        self.layers = nn.ModuleList([
            TransformerBlock(d_model, n_heads, d_ff, dropout)
            for _ in range(n_layers)
        ])

        # Output projection to vocabulary
        self.output_proj = nn.Linear(d_model, vocab_size)

        self.dropout = nn.Dropout(dropout)

        # Initialize weights
        self.apply(self._init_weights)

    def _init_weights(self, module):
        """Initialize weights with small random values"""
        if isinstance(module, (nn.Linear, nn.Embedding)):
            module.weight.data.normal_(mean=0.0, std=0.02)
            if isinstance(module, nn.Linear) and module.bias is not None:
                module.bias.data.zero_()

    def forward(
        self,
        event_tokens: torch.Tensor,
        context: Optional[torch.Tensor] = None,
        return_hidden: bool = False
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        """
        Forward pass for next event prediction.

        Args:
            event_tokens: [batch_size, seq_len] - Tokenized event sequence
            context: [batch_size, context_dim] - Optional context (news, game state)
            return_hidden: Whether to return hidden states (for analysis)

        Returns:
            logits: [batch_size, seq_len, vocab_size] - Logits for next event
            hidden: [batch_size, seq_len, d_model] - Hidden states (if requested)
        """
        batch_size, seq_len = event_tokens.shape

        # Token embeddings
        token_emb = self.token_embedding(event_tokens)  # [B, T, D]

        # Positional embeddings
        positions = torch.arange(seq_len, device=event_tokens.device)
        pos_emb = self.pos_embedding(positions)  # [T, D]

        # Combine embeddings
        x = self.dropout(token_emb + pos_emb)  # [B, T, D]

        # Add context if provided (broadcast across sequence)
        if context is not None:
            context_emb = self.context_proj(context).unsqueeze(1)  # [B, 1, D]
            x = x + context_emb

        # Apply transformer layers
        for layer in self.layers:
            x = layer(x)  # [B, T, D]

        # Project to vocabulary
        logits = self.output_proj(x)  # [B, T, V]

        if return_hidden:
            return logits, x
        return logits, None

    def compute_perplexity(
        self,
        event_tokens: torch.Tensor,
        context: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Compute perplexity on a sequence.

        Lower perplexity = Better model of the sport's dynamics

        Args:
            event_tokens: [batch_size, seq_len]
            context: [batch_size, context_dim]

        Returns:
            perplexity: Scalar tensor
        """
        logits, _ = self.forward(event_tokens[:, :-1], context)
        targets = event_tokens[:, 1:]

        # Cross-entropy loss
        loss = F.cross_entropy(
            logits.reshape(-1, self.vocab_size),
            targets.reshape(-1),
            reduction='mean'
        )

        # Perplexity = exp(loss)
        perplexity = torch.exp(loss)
        return perplexity

    @torch.no_grad()
    def generate(
        self,
        start_tokens: torch.Tensor,
        max_new_tokens: int,
        context: Optional[torch.Tensor] = None,
        temperature: float = 1.0,
        top_k: Optional[int] = None,
        top_p: Optional[float] = None,
    ) -> torch.Tensor:
        """
        Generate a sequence by sampling from the model (simulation mode).

        This is the core simulation function: starting from an initial state,
        autoregressively sample next events to simulate a game/season forward.

        Args:
            start_tokens: [batch_size, prefix_len] - Initial sequence
            max_new_tokens: How many events to generate
            context: [batch_size, context_dim] - Context (news, etc.)
            temperature: Sampling temperature (higher = more random)
            top_k: Only sample from top k tokens
            top_p: Nucleus sampling threshold

        Returns:
            generated: [batch_size, prefix_len + max_new_tokens]
        """
        self.eval()

        generated = start_tokens

        for _ in range(max_new_tokens):
            # Get logits for next token
            logits, _ = self.forward(generated, context)
            logits = logits[:, -1, :] / temperature  # [B, V]

            # Apply top-k filtering
            if top_k is not None:
                indices_to_remove = logits < torch.topk(logits, top_k)[0][..., -1, None]
                logits[indices_to_remove] = float('-inf')

            # Apply top-p (nucleus) filtering
            if top_p is not None:
                sorted_logits, sorted_indices = torch.sort(logits, descending=True)
                cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)

                # Remove tokens with cumulative probability above threshold
                sorted_indices_to_remove = cumulative_probs > top_p
                sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
                sorted_indices_to_remove[..., 0] = 0

                indices_to_remove = sorted_indices_to_remove.scatter(
                    1, sorted_indices, sorted_indices_to_remove
                )
                logits[indices_to_remove] = float('-inf')

            # Sample from distribution
            probs = F.softmax(logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)  # [B, 1]

            # Append to sequence
            generated = torch.cat([generated, next_token], dim=1)

        return generated


class TransformerBlock(nn.Module):
    """Single transformer block with causal attention"""

    def __init__(self, d_model: int, n_heads: int, d_ff: int, dropout: float):
        super().__init__()

        self.attention = CausalMultiHeadAttention(d_model, n_heads, dropout)
        self.feed_forward = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Linear(d_ff, d_model),
            nn.Dropout(dropout)
        )

        self.ln1 = nn.LayerNorm(d_model)
        self.ln2 = nn.LayerNorm(d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Attention with residual
        x = x + self.attention(self.ln1(x))
        # Feed-forward with residual
        x = x + self.feed_forward(self.ln2(x))
        return x


class CausalMultiHeadAttention(nn.Module):
    """Multi-head attention with causal masking (can't attend to future)"""

    def __init__(self, d_model: int, n_heads: int, dropout: float):
        super().__init__()

        assert d_model % n_heads == 0

        self.d_model = d_model
        self.n_heads = n_heads
        self.d_k = d_model // n_heads

        self.q_proj = nn.Linear(d_model, d_model)
        self.k_proj = nn.Linear(d_model, d_model)
        self.v_proj = nn.Linear(d_model, d_model)
        self.out_proj = nn.Linear(d_model, d_model)

        self.dropout = nn.Dropout(dropout)

        # Register causal mask buffer
        self.register_buffer('causal_mask', None)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch_size, seq_len, d_model = x.shape

        # Project to Q, K, V
        Q = self.q_proj(x).view(batch_size, seq_len, self.n_heads, self.d_k).transpose(1, 2)
        K = self.k_proj(x).view(batch_size, seq_len, self.n_heads, self.d_k).transpose(1, 2)
        V = self.v_proj(x).view(batch_size, seq_len, self.n_heads, self.d_k).transpose(1, 2)

        # Compute attention scores
        scores = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(self.d_k)  # [B, H, T, T]

        # Apply causal mask
        if self.causal_mask is None or self.causal_mask.size(-1) < seq_len:
            self.causal_mask = torch.triu(
                torch.ones(seq_len, seq_len, device=x.device) * float('-inf'),
                diagonal=1
            )
        scores = scores + self.causal_mask[:seq_len, :seq_len]

        # Attention weights
        attn_weights = F.softmax(scores, dim=-1)
        attn_weights = self.dropout(attn_weights)

        # Apply attention to values
        out = torch.matmul(attn_weights, V)  # [B, H, T, D_k]

        # Concatenate heads
        out = out.transpose(1, 2).contiguous().view(batch_size, seq_len, d_model)

        # Output projection
        out = self.out_proj(out)
        out = self.dropout(out)

        return out


if __name__ == "__main__":
    # Example usage
    print("Testing Sports World Model...")

    # Create model
    vocab_size = 1000  # e.g., 1000 unique event types
    model = SportsWorldModel(
        vocab_size=vocab_size,
        d_model=256,
        n_heads=8,
        n_layers=4,
        max_seq_len=1024
    )

    print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")

    # Example: Compute perplexity on a sequence
    batch_size = 4
    seq_len = 128
    event_tokens = torch.randint(0, vocab_size, (batch_size, seq_len))

    perplexity = model.compute_perplexity(event_tokens)
    print(f"Perplexity: {perplexity.item():.2f}")

    # Example: Generate (simulate) a sequence
    start_tokens = torch.randint(0, vocab_size, (1, 10))  # Start with 10 events
    generated = model.generate(start_tokens, max_new_tokens=50, temperature=1.0)
    print(f"Generated sequence shape: {generated.shape}")
    print("Model ready for training and simulation!")
