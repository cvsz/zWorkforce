const {
  FACTORY_STEPS,
  FactoryWorkflowRunner,
  defaultFactoryHandlers,
} = require("../domain/factoryWorkflow");
const { WorkflowRepository } = require("../repositories/workflowRepository");
const { FactoryRepository } = require("../repositories/factoryRepository");
const {
  PublicationRepository,
} = require("../repositories/publicationRepository");

class FactoryWorkflowService {
  constructor({
    pool,
    providerRegistry,
    killSwitch = () => process.env.EMERGENCY_PUBLISHING_KILL_SWITCH === "true",
  }) {
    this.pool = pool;
    this.workflows = new WorkflowRepository(pool);
    this.factory = new FactoryRepository(pool);
    this.publications = new PublicationRepository(pool, { providerRegistry });
    this.killSwitch = killSwitch;
  }

  async definitionFor(brandId) {
    const existing = await this.pool.query(
      "SELECT * FROM workflows WHERE brand_id = $1 AND name = 'canonical-content-factory' AND active = true ORDER BY version DESC LIMIT 1",
      [brandId],
    );
    return (
      existing.rows[0] ||
      this.workflows.createDefinition({
        brandId,
        name: "canonical-content-factory",
        steps: FACTORY_STEPS,
      })
    );
  }

  handlers() {
    const handlers = defaultFactoryHandlers();
    return {
      ...handlers,
      M01_STRATEGY: async (input, context) => {
        const output = await handlers.M01_STRATEGY(input, context);
        const idea = await this.factory.persistIdea(
          context.run.id,
          input.brandId,
          output.idea,
        );
        return { ...output, idea: { ...output.idea, id: idea.id } };
      },
      M05_CAPTION: async (input, context) => {
        const output = await handlers.M05_CAPTION(input, context);
        await this.factory.persistAssetPack(
          input.brandId,
          input.idea.id,
          output.assetPack,
        );
        return output;
      },
      M10_QA: async (input, context) => {
        const output = await handlers.M10_QA(input, context);
        await this.factory.persistQa(
          output.assetPack.assets.map((asset) => asset.id),
          output.qa,
        );
        return output;
      },
      APPROVAL: async (input, context) => {
        const output = await handlers.APPROVAL(input, context);
        if (!output.blocked) {
          await this.factory.approve(
            input.assetPack.assets.map((asset) => asset.id),
            input.approvalActorId || null,
            input.qa,
            input.approvalDecision === "overridden" ? "overridden" : "approved",
          );
        }
        return output;
      },
    };
  }

  runner() {
    return new FactoryWorkflowRunner({
      workflows: this.workflows,
      handlers: this.handlers(),
      killSwitch: this.killSwitch,
      publish: async (input, { slot }) => {
        const visual = input.assetPack.assets.find(
          (asset) => asset.type === (input.publicationKind || "image"),
        );
        if (!visual)
          throw new Error(
            `No ${input.publicationKind || "image"} asset is available for publishing`,
          );
        return this.publications.createApproved(
          {
            brandId: input.brandId,
            assetIds: [visual.id],
            platform: input.platform,
            kind: visual.type,
            caption: input.caption.hook,
            hashtags: input.caption.hashtags,
            slot,
          },
          {
            idempotencyKey: `${input.factoryCommandKey}:publish`,
            requestId: input.requestId,
            actorId: input.approvalActorId || null,
          },
        );
      },
    });
  }

  async start(input, context) {
    const definition = await this.definitionFor(input.brandId);
    const commandKey = context.idempotencyKey;
    const run = await this.workflows.start(
      definition.id,
      { ...input, factoryCommandKey: commandKey, requestId: context.requestId },
      commandKey,
    );
    return this.runner().run(run.id);
  }

  async approve(runId, { decision, actorId }) {
    await this.workflows.resumeBlocked(runId, "APPROVAL", {
      approvalDecision: decision,
      approvalActorId: actorId,
    });
    return this.runner().run(runId);
  }
}

module.exports = { FactoryWorkflowService };
