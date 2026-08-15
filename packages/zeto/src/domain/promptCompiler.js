const MODES = ["PRODUCTION", "OPS", "OPTIMIZE"];
const REQUIRED_BRAND_FIELDS = [
  "brand",
  "niche",
  "voice",
  "colors",
  "fonts",
  "platforms",
  "goals",
  "timezone",
  "budget_per_asset",
  "stack",
  "image_model",
  "video_model",
  "audio_model",
];

function compilePrompt(specification) {
  if (!MODES.includes(specification.mode))
    throw new Error(`Invalid lifecycle mode: ${specification.mode}`);
  const missingBrandFields = REQUIRED_BRAND_FIELDS.filter(
    (field) =>
      specification.brand?.[field] === undefined ||
      specification.brand?.[field] === null,
  );
  if (missingBrandFields.length)
    throw new Error(`Missing brand fields: ${missingBrandFields.join(", ")}`);
  const values = { ...specification.brand, ...specification.inputs };
  const prompt = specification.template.replace(
    /\{([A-Za-z0-9_]+)\}/g,
    (placeholder, key) => {
      if (values[key] === undefined || values[key] === null) return placeholder;
      return Array.isArray(values[key])
        ? values[key].join(", ")
        : String(values[key]);
    },
  );
  const unresolved = prompt.match(/\{[^}]+\}/g);
  if (unresolved)
    throw new Error(`Unresolved placeholder: ${unresolved.join(", ")}`);
  const brandPolicy = {
    brand: specification.brand.brand,
    niche: specification.brand.niche,
    voice: specification.brand.voice,
    colors: specification.brand.colors,
    palette: specification.brand.palette || [],
    fonts: specification.brand.fonts,
    goals: specification.brand.goals,
    budget_per_asset: specification.brand.budget_per_asset,
  };
  const pmaster = {
    role: specification.role,
    inputs: specification.inputs,
    modes: { active: specification.mode, supported: MODES },
    constraints: [...specification.constraints, { brand_policy: brandPolicy }],
    output: specification.output,
    self_check: specification.selfCheck,
  };
  return {
    module: specification.module,
    mode: specification.mode,
    prompt,
    pmaster,
    brand_policy: brandPolicy,
    approval: {
      required:
        specification.approvalRequired === undefined
          ? specification.brand.approval_required !== false
          : specification.approvalRequired === true,
    },
  };
}

module.exports = { MODES, compilePrompt };
