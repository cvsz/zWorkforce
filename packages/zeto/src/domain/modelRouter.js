class ModelRouter {
  constructor({ providers, recordCostEvent, enqueueFailure }) {
    this.providers = providers;
    this.recordCostEvent = recordCostEvent;
    this.enqueueFailure = enqueueFailure;
  }

  async execute({ task, input, budget, routes }) {
    if (!Array.isArray(routes) || routes.length === 0)
      throw new Error("At least one model route is required");
    const affordable = routes.filter(
      (route) => Number(route.estimatedCost) <= Number(budget),
    );
    if (affordable.length === 0)
      throw new Error("Cost cap exceeded before generation");
    const attempts = [];
    for (let retryCount = 0; retryCount < affordable.length; retryCount += 1) {
      const route = affordable[retryCount];
      const provider = this.providers[route.provider];
      if (!provider)
        throw new Error(`Unknown model provider: ${route.provider}`);
      const started = performance.now();
      try {
        const response = await provider({ model: route.model, task, input });
        const event = {
          task,
          provider: route.provider,
          model: route.model,
          latencyMs: Math.round(performance.now() - started),
          usage: response.usage || { input: 0, output: 0 },
          estimatedCost: route.estimatedCost,
          retryCount,
          qualityScore: response.qualityScore ?? null,
          fallbackReason: null,
        };
        await this.recordCostEvent(event);
        return {
          ...response,
          provider: route.provider,
          model: route.model,
          retryCount,
        };
      } catch (error) {
        const event = {
          task,
          provider: route.provider,
          model: route.model,
          latencyMs: Math.round(performance.now() - started),
          usage: { input: 0, output: 0 },
          estimatedCost: route.estimatedCost,
          retryCount,
          qualityScore: null,
          fallbackReason: error.message,
        };
        attempts.push(event);
        await this.recordCostEvent(event);
      }
    }
    await this.enqueueFailure({ task, input, attempts });
    throw new Error("All model routes failed; work sent to failure queue");
  }
}

module.exports = { ModelRouter };
