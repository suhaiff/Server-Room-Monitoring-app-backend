# AI/ML implementation

The AI service implements the five planner blocks:

1. baseline learning from mean and standard deviation;
2. z-score anomaly detection;
3. linear trend/forecasting;
4. weighted risk scoring using environment and hazard factors;
5. deterministic human-readable explanations.

These implementations are deliberately transparent and runnable without a trained proprietary dataset. They are suitable as baselines and service-contract stubs. Production model training must use representative historical data, validation splits, versioning, drift checks and approval thresholds. The optional LLM credential remains unset; safety-critical alert creation never depends on an LLM.

