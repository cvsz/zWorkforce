const { compilePrompt } = require("./promptCompiler");
const { createDraftAssetPack } = require("./assetPackFactory");
const { evaluateArtifact } = require("./qaScorer");
const { evaluateAutopilot } = require("./autopilotPolicy");
const { localSlotToUtc } = require("./calendar");
const { analyzeMention, evaluateAlerts } = require("./monitoring");

const FACTORY_STEPS = Object.freeze([
  { key: "M01_STRATEGY", owner: "strategy", maxAttempts: 3 },
  { key: "M02_IMAGE", owner: "creative", maxAttempts: 3 },
  { key: "M03_VIDEO", owner: "creative", maxAttempts: 3 },
  { key: "M04_AUDIO", owner: "creative", maxAttempts: 3 },
  { key: "M05_CAPTION", owner: "editorial", maxAttempts: 3 },
  { key: "M10_QA", owner: "brand-safety", maxAttempts: 2 },
  { key: "APPROVAL", owner: "human-or-policy", maxAttempts: 1 },
  { key: "M06_PUBLISH", owner: "publishing", maxAttempts: 5 },
  { key: "M07_MONITOR", owner: "community", maxAttempts: 3 },
  { key: "M08_REPORT", owner: "analytics", maxAttempts: 3 },
]);

function carry(input, patch) {
  return { ...input, ...patch };
}

function defaultFactoryHandlers() {
  return {
    M01_STRATEGY: async (input) => {
      const idea = input.idea;
      if (!idea?.title || !Number.isFinite(idea.score))
        throw new Error("M01 requires a scored idea with a title");
      const compiledPrompt = compilePrompt({
        module: "M01",
        mode: "PRODUCTION",
        brand: input.brand,
        role: "Content strategy lead",
        inputs: idea,
        template: "Create a production content pack for {brand} about {title}.",
        constraints: ["Use only substantiated claims"],
        output: { type: "scored_idea" },
        selfCheck: ["brand_fit", "audience_value"],
      });
      return carry(input, {
        idea: { ...idea, status: "selected" },
        compiledPrompt,
      });
    },
    M02_IMAGE: async (input) => {
      if (!input.image?.prompt) throw new Error("M02 requires an image prompt");
      return carry(input, {
        completedModules: [...(input.completedModules || []), "M02"],
      });
    },
    M03_VIDEO: async (input) => {
      if (!input.video?.shots?.length)
        throw new Error("M03 requires a video shot list");
      return carry(input, {
        completedModules: [...input.completedModules, "M03"],
      });
    },
    M04_AUDIO: async (input) => {
      if (input.audio?.license !== "generated")
        throw new Error("M04 requires generated audio provenance");
      return carry(input, {
        completedModules: [...input.completedModules, "M04"],
      });
    },
    M05_CAPTION: async (input) => {
      const assetPack = createDraftAssetPack(input);
      return carry(input, {
        completedModules: [...input.completedModules, "M05"],
        assetPack,
      });
    },
    M10_QA: async (input) => {
      const qa = evaluateArtifact(input.qaChecks, {
        autoPilot: input.autoPilot === true,
      });
      const autopilot = evaluateAutopilot({
        autoPilot: input.autoPilot === true,
        killSwitch: input.killSwitch === true,
        qaScore: qa.score,
        platformPermitted: input.platformPermitted === true,
        estimatedCost: Number(input.estimatedCost),
        remainingBudget: Number(input.remainingBudget),
        postsInWindow: input.postsInWindow,
        postingFrequencyCap: input.postingFrequencyCap,
        claimsSubstantiated: input.claimsSubstantiated === true,
        copyrightCleared: input.copyrightCleared === true,
      });
      return carry(input, {
        qa,
        autopilot,
        completedModules: [...input.completedModules, "M10"],
      });
    },
    APPROVAL: async (input) => {
      const approved =
        input.approvalDecision === "approved" ||
        input.approvalDecision === "overridden" ||
        input.autopilot?.allowed === true;
      if (!approved)
        return {
          blocked: true,
          reason: { code: "HUMAN_APPROVAL_REQUIRED", qa: input.qa },
          output: input,
        };
      return carry(input, {
        approval: {
          decision: input.approvalDecision || "approved_by_policy",
          approvedAt: new Date().toISOString(),
        },
      });
    },
    M06_PUBLISH: async (input, context) => {
      if (context.killSwitch())
        throw Object.assign(
          new Error("Emergency publishing kill switch is active"),
          { code: "KILL_SWITCH_ACTIVE", retryable: false },
        );
      const slot = input.slot
        ? localSlotToUtc(input.slot, input.brand.timezone)
        : null;
      const publication = await context.publish(input, { slot });
      return carry(input, {
        publication,
        completedModules: [...input.completedModules, "M06"],
      });
    },
    M07_MONITOR: async (input) => {
      const mentions = (input.mentions || []).map(analyzeMention);
      const alerts = input.alertSnapshot
        ? evaluateAlerts(input.alertSnapshot)
        : [];
      return carry(input, {
        monitoring: { mentions, alerts },
        completedModules: [...input.completedModules, "M07"],
      });
    },
    M08_REPORT: async (input) =>
      carry(input, {
        report: {
          brand: input.brand.brand,
          publication: input.publication,
          qaScore: input.qa.score,
          alertCount: input.monitoring.alerts.length,
          generatedAt: new Date().toISOString(),
        },
        completedModules: [...input.completedModules, "M08"],
      }),
  };
}

class FactoryWorkflowRunner {
  constructor({
    workflows,
    handlers = defaultFactoryHandlers(),
    publish,
    killSwitch = () => false,
    workerId = `factory-${process.pid}`,
  }) {
    if (!workflows || typeof publish !== "function")
      throw new Error("workflows and publish are required");
    this.workflows = workflows;
    this.handlers = handlers;
    this.publish = publish;
    this.killSwitch = killSwitch;
    this.workerId = workerId;
  }

  async run(runId) {
    while (true) {
      const run = await this.workflows.getRun(runId);
      if (!run) throw new Error("Workflow run not found");
      if (["succeeded", "failed", "cancelled"].includes(run.status)) return run;
      const step = await this.workflows.claimNext(runId, this.workerId);
      if (!step) return this.workflows.getRun(runId);
      const handler = this.handlers[step.step_key];
      const span = await this.workflows.startSpan(run, step, {
        attempt: step.attempt,
      });
      try {
        if (!handler) throw new Error(`No handler for ${step.step_key}`);
        const output = await handler(step.input, {
          run,
          step,
          publish: this.publish,
          killSwitch: this.killSwitch,
        });
        if (output?.blocked) {
          await this.workflows.block(
            step.id,
            this.workerId,
            output.output,
            output.reason,
          );
          await this.workflows.finishSpan(span.id, "blocked", {
            attributes: { code: output.reason?.code },
          });
          return this.workflows.getRun(runId);
        }
        await this.workflows.succeed(
          step.id,
          this.workerId,
          output,
          Number(output?.stepCost || 0),
        );
        await this.workflows.finishSpan(span.id, "succeeded");
      } catch (error) {
        const detail = {
          code: error.code || "STEP_FAILED",
          message: error.message,
          retryable: error.retryable !== false,
        };
        await this.workflows.fail(
          step.id,
          this.workerId,
          detail,
          error.retryable === false ? 0 : 1000,
          error.retryable === false,
        );
        await this.workflows.finishSpan(span.id, "failed", { error: detail });
        if (error.retryable === false) return this.workflows.getRun(runId);
      }
    }
  }
}

module.exports = {
  FACTORY_STEPS,
  FactoryWorkflowRunner,
  defaultFactoryHandlers,
};
