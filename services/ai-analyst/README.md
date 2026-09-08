# ai-analyst

AI investigation/explanation service (product spec section 15).

- **Provider abstraction** (`ai_analyst/provider.py`, `factory.py`): the
  rest of the codebase only ever talks to the `AIProvider` interface;
  which vendor is used is chosen entirely from `AI_PROVIDER`/`AI_API_KEY`/
  `AI_MODEL` in `.env`. Only `anthropic` is implemented so far.
- **Prompt construction** (`prompt.py`): every evidence field the
  pipeline couldn't determine is rendered as an explicit "not available"
  marker — the model is instructed never to guess. On-chain-derived
  strings (contract names, token symbols) are wrapped in
  `<untrusted_onchain_data>` tags with an explicit system-prompt
  instruction never to treat their contents as commands, since a
  malicious contract could embed adversarial text there.
- **Output validation** (`output.py`): the model's raw text is never
  trusted directly — every field is type- and range-checked before
  becoming an `AIAssessment`. Invalid output triggers one retry with a
  correction reminder, then a safe `REVIEW`/confidence-0 fallback
  (`service.py`) — never a fabricated-looking result and never a
  silently-passed transaction.

## What's real vs. not, in this delivery

The prompt builder, output validator, and service orchestration
(retry-then-fallback) are all **real, tested logic** — see `tests/`,
which uses a hand-written `FakeAIProvider` and was actually run (no
network needed). The `AnthropicProvider` itself has **not** been
exercised against the real API in the environment that generated this
repo (no network access, package not installed) — syntax-checked only.
Validate it for real once `AI_API_KEY` is set:

```bash
pip install -r requirements.txt
python -c "
import asyncio
from ai_analyst.providers.anthropic_provider import AnthropicProvider
p = AnthropicProvider(api_key='...', model='claude-sonnet-4-6')
print(asyncio.run(p.complete(system='Reply with OK.', user='ping')))
"
```
