const assert = require("node:assert/strict");
const test = require("node:test");

const zato = require("../config/brands/zato.json");

test("ProMaster compiler preserves P-MASTER and appends zato brand policy", () => {
  const { compilePrompt } = require("../src/domain/promptCompiler");
  const result = compilePrompt({
    module: "M02",
    mode: "PRODUCTION",
    brand: zato,
    role: "AI image art director",
    inputs: { brief: "Launch a practical niche-content series" },
    constraints: ["No unsupported claims"],
    output: { format: "json", schema: "asset-v1" },
    selfCheck: ["Validate palette", "Return provenance"],
    template: "Create for {brand} in {niche} using {colors}. Brief: {brief}",
  });

  assert.equal(result.mode, "PRODUCTION");
  assert.deepEqual(Object.keys(result.pmaster), [
    "role",
    "inputs",
    "modes",
    "constraints",
    "output",
    "self_check",
  ]);
  assert.match(result.prompt, /zato/);
  assert.match(result.prompt, /Niche Content/);
  assert.doesNotMatch(result.prompt, /\{[^}]+\}/);
  assert.equal(result.brand_policy.palette[0].hex, "#ffffff");
  assert.equal(result.approval.required, true);
});

test("ProMaster compiler rejects unresolved placeholders and invalid modes", () => {
  const { compilePrompt } = require("../src/domain/promptCompiler");
  const base = {
    module: "M05",
    brand: zato,
    role: "caption writer",
    inputs: {},
    constraints: [],
    output: { format: "json" },
    selfCheck: [],
  };
  assert.throws(
    () =>
      compilePrompt({
        ...base,
        mode: "PRODUCTION",
        template: "Write about {missing}",
      }),
    /unresolved placeholder/i,
  );
  assert.throws(
    () =>
      compilePrompt({ ...base, mode: "DRAFT", template: "Write for {brand}" }),
    /mode/i,
  );
});
