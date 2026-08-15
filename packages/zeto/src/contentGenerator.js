/**
 * AI Content Generator for Zeto
 * ──────────────────────────────────────────────────────────────────────────────
 * Generates Facebook post content (text + image URL) using multiple AI
 * providers in order of availability:
 *   1. Cloudflare AI Gateway (Workers AI)
 *   2. OpenAI (gpt-4o-mini text, dall-e-3 image)
 *   3. Gemini (Google AI Studio)
 *   4. Built-in local template engine (no API needed, always works)
 *
 * For images: uses Cloudflare AI image generation OR Unsplash photo API (free)
 * as a reliable fallback.
 *
 * Content topics: rotates through "learning" topics in Thai/English.
 */

const axios = require("axios");
const https = require("https");
const { readSecret } = require("./security/secrets");

// ── Config ─────────────────────────────────────────────────────────────────────
const AI_CONFIG = {
  cloudflare: {
    accountId: process.env.CLOUDFLARE_ACCOUNT_ID,
    token:
      readSecret("CLOUDFLARE_WORKERS_TOKEN") ||
      readSecret("CLOUDFLARE_API_TOKEN"),
    aiGateway: process.env.CLOUDFLARE_AI_GATEWAY_SLUG,
    textModel: "@cf/meta/llama-3.1-8b-instruct",
    imgModel: "@cf/stabilityai/stable-diffusion-xl-base-1.0",
  },
  openai: {
    apiKey: readSecret("OPENAI_API_KEY"),
    textModel: "gpt-4o-mini",
    imgModel: "dall-e-3",
  },
  gemini: {
    apiKey: readSecret("GEMINI_API_KEY") || readSecret("GOOGLE_AI_API_KEY"),
    model: "gemini-1.5-flash-latest",
  },
  unsplash: {
    accessKey: readSecret("UNSPLASH_ACCESS_KEY"),
  },
};

// ── "Know-how to learn" topic library ─────────────────────────────────────────
const TOPIC_LIBRARY = [
  // Tech & Dev
  {
    tag: "coding",
    th: "การเขียนโปรแกรม",
    en: "programming & coding",
    emoji: "💻",
  },
  {
    tag: "ai",
    th: "ปัญญาประดิษฐ์",
    en: "Artificial Intelligence & Machine Learning",
    emoji: "🤖",
  },
  { tag: "webdev", th: "Web Development", en: "web development", emoji: "🌐" },
  { tag: "python", th: "Python", en: "Python programming", emoji: "🐍" },
  { tag: "database", th: "ฐานข้อมูล", en: "databases & SQL", emoji: "🗄️" },
  { tag: "cloud", th: "Cloud Computing", en: "cloud computing", emoji: "☁️" },
  { tag: "security", th: "Cybersecurity", en: "cybersecurity", emoji: "🔐" },
  // Business & Life
  {
    tag: "productivity",
    th: "Productivity",
    en: "productivity & time management",
    emoji: "⏱️",
  },
  {
    tag: "finance",
    th: "การเงิน",
    en: "personal finance & investing",
    emoji: "💰",
  },
  {
    tag: "marketing",
    th: "Digital Marketing",
    en: "digital marketing",
    emoji: "📈",
  },
  {
    tag: "leadership",
    th: "ภาวะผู้นำ",
    en: "leadership & management",
    emoji: "🚀",
  },
  {
    tag: "startup",
    th: "Startup & Entrepreneurship",
    en: "startups and entrepreneurship",
    emoji: "🏆",
  },
  // Learning & Growth
  {
    tag: "learning",
    th: "การเรียนรู้",
    en: "how to learn effectively",
    emoji: "📚",
  },
  { tag: "mindset", th: "Growth Mindset", en: "growth mindset", emoji: "🧠" },
  {
    tag: "creativity",
    th: "ความคิดสร้างสรรค์",
    en: "creativity & design thinking",
    emoji: "🎨",
  },
  {
    tag: "english",
    th: "ภาษาอังกฤษ",
    en: "English language learning",
    emoji: "🗣️",
  },
  // Trending
  {
    tag: "blockchain",
    th: "Blockchain & Web3",
    en: "blockchain and Web3",
    emoji: "⛓️",
  },
  { tag: "ux", th: "UI/UX Design", en: "UI/UX design", emoji: "✨" },
  {
    tag: "data",
    th: "Data Science",
    en: "data science & analytics",
    emoji: "📊",
  },
  {
    tag: "automation",
    th: "Automation",
    en: "automation and no-code tools",
    emoji: "⚙️",
  },
];

// Post format templates
const POST_FORMATS = ["tips", "howto", "fact", "quote", "checklist", "story"];

// Unsplash keyword map
const UNSPLASH_KEYWORDS = {
  coding: "coding laptop",
  ai: "artificial intelligence technology",
  webdev: "web design computer",
  python: "python programming code",
  database: "server data technology",
  cloud: "cloud technology sky",
  security: "cybersecurity technology",
  productivity: "productivity workspace desk",
  finance: "finance money investment",
  marketing: "digital marketing analytics",
  leadership: "leadership team success",
  startup: "startup office team",
  learning: "learning books study",
  mindset: "mindset motivation success",
  creativity: "creativity design art",
  english: "language learning books",
  blockchain: "blockchain cryptocurrency",
  ux: "ux design interface",
  data: "data analytics charts",
  automation: "automation robot technology",
};

// ── Helpers ────────────────────────────────────────────────────────────────────
const axiosInst = axios.create({
  timeout: 30000,
  httpsAgent:
    process.env.NODE_ENV !== "production"
      ? new https.Agent({ rejectUnauthorized: false })
      : undefined,
});

/** Pick a random item from array */
const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];

/** Pick a random topic, weighted to avoid repeats within last N */
let _recentTopics = [];
const pickTopic = () => {
  const available = TOPIC_LIBRARY.filter((t) => !_recentTopics.includes(t.tag));
  const pool = available.length > 0 ? available : TOPIC_LIBRARY;
  const topic = pick(pool);
  _recentTopics = [..._recentTopics.slice(-4), topic.tag];
  return topic;
};

// ── Text generation ────────────────────────────────────────────────────────────

/** Build a rich prompt for the given topic and format */
const buildPrompt = (topic, format) => {
  const instructions = {
    tips: `Write 3-5 actionable tips about ${topic.en} for beginners. Format as a numbered list. Keep each tip under 2 sentences.`,
    howto: `Write a short "How to get started with ${topic.en}" guide in 3 steps. Make it engaging and beginner-friendly.`,
    fact: `Share 2-3 surprising and interesting facts about ${topic.en} that most people don't know.`,
    quote: `Write an original motivational quote about ${topic.en} and explain it briefly (2-3 sentences).`,
    checklist: `Create a beginner's checklist for learning ${topic.en}. Use checkboxes or bullet points.`,
    story: `Write a short (3-4 sentence) relatable story about someone learning ${topic.en} and their breakthrough moment.`,
  };

  return `You are an engaging social media content creator for a tech and learning community in Thailand.
Write a Facebook post about: ${topic.th} (${topic.en})

Format: ${instructions[format] || instructions.tips}

Rules:
- Mix Thai and English naturally (Thai-first, English terms keep as-is)
- Use ${topic.emoji} emoji and 2-3 relevant emojis
- End with a call-to-action or question for engagement
- Maximum 300 words
- Sound authentic and conversational, NOT like an ad
- Include relevant hashtags at the end (mix Thai and English)

Write only the post content, nothing else.`;
};

/** Generate text via Cloudflare Workers AI */
async function generateTextCloudflare(prompt) {
  const { accountId, token, textModel } = AI_CONFIG.cloudflare;
  if (!accountId || !token) throw new Error("Cloudflare creds missing");

  const url = `https://api.cloudflare.com/client/v4/accounts/${accountId}/ai/run/${textModel}`;
  const res = await axiosInst.post(
    url,
    {
      messages: [
        { role: "system", content: "You are a social media content creator." },
        { role: "user", content: prompt },
      ],
      max_tokens: 500,
    },
    {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    },
  );

  const text =
    res.data?.result?.response || res.data?.result?.[0]?.generated_text;
  if (!text) throw new Error("No text from Cloudflare AI");
  return text.trim();
}

/** Generate text via OpenAI */
async function generateTextOpenAI(prompt) {
  const { apiKey, textModel } = AI_CONFIG.openai;
  if (!apiKey) throw new Error("OpenAI API key missing");

  const res = await axiosInst.post(
    "https://api.openai.com/v1/chat/completions",
    {
      model: textModel,
      messages: [{ role: "user", content: prompt }],
      max_tokens: 500,
      temperature: 0.8,
    },
    {
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
    },
  );

  const text = res.data?.choices?.[0]?.message?.content;
  if (!text) throw new Error("No text from OpenAI");
  return text.trim();
}

/** Generate text via Gemini */
async function generateTextGemini(prompt) {
  const { apiKey, model } = AI_CONFIG.gemini;
  if (!apiKey) throw new Error("Gemini API key missing");

  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`;
  const res = await axiosInst.post(url, {
    contents: [{ parts: [{ text: prompt }] }],
    generationConfig: { maxOutputTokens: 500, temperature: 0.8 },
  });

  const text = res.data?.candidates?.[0]?.content?.parts?.[0]?.text;
  if (!text) throw new Error("No text from Gemini");
  return text.trim();
}

/** Local fallback text generator — no API needed */
function generateTextLocal(topic, format) {
  const templates = {
    tips: () => `${topic.emoji} 3 เทคนิคสำคัญสำหรับ ${topic.th}

1️⃣ เริ่มจากพื้นฐาน — อย่าข้ามขั้นตอน เข้าใจ concept ก่อน แล้วค่อยลงมือทำ
2️⃣ Practice makes perfect — ฝึกทุกวัน แม้แค่ 20-30 นาที ก็สร้างความแตกต่างได้
3️⃣ Join community — หาเพื่อนที่เรียนเหมือนกัน แชร์ประสบการณ์ เติบโตไปด้วยกัน

${topic.th} ไม่ยากเลย ถ้าเริ่มถูกทาง! ${topic.emoji}

คุณกำลังเรียน ${topic.th} อยู่ไหม? แชร์ประสบการณ์ได้เลย! 👇

#${topic.tag} #${topic.th.replace(/\s/g, "")} #LearnWithZeaZ #TechThailand`,

    howto: () => `🚀 เริ่มต้น ${topic.th} ยังไงดี? มาดูกัน!

📌 Step 1: ศึกษา Basics
หา resource ที่ดี เช่น YouTube, Coursera, หรือ Official Docs แล้วทำความเข้าใจ concept หลักให้ชัดเจน

📌 Step 2: ลงมือทำ Project จริง
อย่าแค่ดู tutorial ลองสร้าง project เล็กๆ ด้วยตัวเอง ผิดพลาดได้ — นั่นคือการเรียนรู้จริงๆ

📌 Step 3: Share & Get Feedback
โพสต์ผลงานใน community รับ feedback แล้วปรับปรุง วนซ้ำไปเรื่อยๆ ${topic.emoji}

Ready to start ${topic.en}? 💪

#${topic.tag} #HowTo #${topic.th.replace(/\s/g, "")} #ZeaZLearning`,

    fact: () => `${topic.emoji} Did you know? น่าสนใจเกี่ยวกับ ${topic.th}!

💡 มีผู้เชี่ยวชาญด้าน ${topic.en} เพิ่มขึ้นกว่า 40% ต่อปีทั่วโลก
💡 คนที่เรียน ${topic.en} มักมีรายได้สูงกว่าค่าเฉลี่ย เพราะ demand สูงมาก
💡 คุณสามารถเริ่มเรียน ${topic.en} ได้จาก 0 ถึงระดับมืออาชีพภายใน 6-12 เดือน ถ้าตั้งใจจริง

${topic.th} เป็นทักษะที่ตลาดต้องการมากที่สุดในยุคนี้! ${topic.emoji}

คุณสนใจ ${topic.th} บ้างไหม? Comment มาเลย! 🔥

#${topic.tag} #FunFact #${topic.th.replace(/\s/g, "")} #LearnEveryday`,

    quote: () => `✨ Quote of the Day — ${topic.th}

"การเรียนรู้ ${topic.th} ไม่ใช่ sprint แต่เป็น marathon — ทุกวันที่ฝึกคือก้าวที่นำคุณไปข้างหน้า"

${topic.emoji} ความสำเร็จด้าน ${topic.en} เกิดจากความสม่ำเสมอ ไม่ใช่ความสามารถที่ติดตัวมา ทุกคนเริ่มจากศูนย์ได้ทั้งนั้น

วันนี้คุณได้เรียนรู้อะไรใหม่บ้าง? แชร์กันได้เลย 👇 ${topic.emoji}

#${topic.tag} #DailyQuote #Motivation #${topic.th.replace(/\s/g, "")}`,

    checklist: () => `📋 Checklist: เริ่มต้น ${topic.th} ให้ได้ผล!

☐ ตั้งเป้าหมายชัดเจนว่าอยากได้อะไรจาก ${topic.en}
☐ หา learning resource ที่ดีและเหมาะกับระดับตัวเอง
☐ กำหนดเวลาเรียนสม่ำเสมอ อย่างน้อย 30 นาที/วัน
☐ สร้าง project จริงเพื่อ apply สิ่งที่เรียน
☐ เข้าร่วม community และแชร์ความก้าวหน้า
☐ Review และทบทวนสิ่งที่เรียนสัปดาห์ละครั้ง

${topic.emoji} Checklist เสร็จแล้ว เริ่มได้เลย!

คุณผ่าน checklist นี้ไปกี่ข้อแล้ว? แจ้งด้านล่าง! 👇

#${topic.tag} #Checklist #${topic.th.replace(/\s/g, "")} #LearningJourney`,

    story:
      () => `${topic.emoji} เรื่องราวจริง: จากมือใหม่สู่มืออาชีพด้าน ${topic.th}

"ตอนแรกฉันไม่รู้อะไรเลยเกี่ยวกับ ${topic.en} กลัวมากว่ามันจะยากเกินไป แต่พอเริ่มทีละเล็กทีละน้อย ฝึกทุกวัน ผ่านไป 3 เดือนก็เริ่มทำได้จริงๆ"

💡 Lesson: ทุกผู้เชี่ยวชาญเคยเป็นมือใหม่มาก่อน ความสำเร็จอยู่ที่การไม่ยอมแพ้ ${topic.emoji}

คุณมีเรื่องราวการเรียนรู้ ${topic.th} บ้างไหม? เล่าให้ฟังได้เลย! 🙌

#${topic.tag} #SuccessStory #${topic.th.replace(/\s/g, "")} #NeverGiveUp`,
  };

  const fn = templates[format] || templates.tips;
  return fn();
}

// ── Image generation ───────────────────────────────────────────────────────────

/** Get image from Unsplash (free, no auth for random) */
async function getUnsplashImage(topic) {
  const keyword = UNSPLASH_KEYWORDS[topic.tag] || `${topic.en} learning`;
  const accessKey = AI_CONFIG.unsplash.accessKey;

  if (accessKey) {
    // Use authenticated Unsplash API for consistent results
    try {
      const res = await axiosInst.get(
        "https://api.unsplash.com/photos/random",
        {
          params: {
            query: keyword,
            orientation: "landscape",
            content_filter: "high",
          },
          headers: { Authorization: `Client-ID ${accessKey}` },
        },
      );
      return res.data?.urls?.regular || res.data?.urls?.full;
    } catch {
      // Continue with the stable fallback image when Unsplash is unavailable.
    }
  }

  // Fallback: use Unsplash URL format (no API key, direct keyword-based search redirection)
  return `https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1200&q=80&auto=format&fit=crop`; // Safe tech/default fallback image
}

/** Generate image via Cloudflare AI (returns binary → need to save or convert) */
async function generateImageCloudflare(prompt) {
  const { accountId, token, imgModel } = AI_CONFIG.cloudflare;
  if (!accountId || !token) throw new Error("Cloudflare creds missing");

  const url = `https://api.cloudflare.com/client/v4/accounts/${accountId}/ai/run/${imgModel}`;
  const res = await axiosInst.post(
    url,
    { prompt },
    {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      responseType: "arraybuffer",
    },
  );

  // Convert arraybuffer to base64 data URL
  const b64 = Buffer.from(res.data).toString("base64");
  return `data:image/png;base64,${b64}`;
}

// ── Main API ───────────────────────────────────────────────────────────────────

/**
 * Generate complete content (text + image URL) for a Facebook post.
 * @param {Object} options
 * @param {string} [options.tag]       Force specific topic tag
 * @param {string} [options.format]    Force specific format
 * @param {boolean} [options.withImage] Include image (default: true)
 * @param {string} [options.provider]  AI provider: 'auto'|'cloudflare'|'openai'|'gemini'|'local'
 * @returns {Promise<{message, imageUrl, topic, format, provider, generatedAt}>}
 */
async function generateContent(options = {}) {
  const {
    tag,
    format: forcedFormat,
    withImage = true,
    provider = "auto",
  } = options;

  // Pick topic
  const topic = tag
    ? TOPIC_LIBRARY.find((t) => t.tag === tag) || pickTopic()
    : pickTopic();

  const format = forcedFormat || pick(POST_FORMATS);

  const prompt = buildPrompt(topic, format);

  let message = null;
  let usedProvider = "local";
  const errors = [];

  // ── Text generation pipeline ─────────────────────────────────────────────
  const providers =
    provider === "auto"
      ? ["cloudflare", "openai", "gemini", "local"]
      : [provider, "local"];

  for (const p of providers) {
    try {
      if (p === "cloudflare") {
        message = await generateTextCloudflare(prompt);
        usedProvider = "cloudflare";
      } else if (p === "openai") {
        message = await generateTextOpenAI(prompt);
        usedProvider = "openai";
      } else if (p === "gemini") {
        message = await generateTextGemini(prompt);
        usedProvider = "gemini";
      } else {
        message = generateTextLocal(topic, format);
        usedProvider = "local";
      }
      break;
    } catch (e) {
      errors.push(`${p}: ${e.message}`);
    }
  }

  if (!message) {
    message = generateTextLocal(topic, format);
    usedProvider = "local-fallback";
  }

  // ── Prompt Branding Guardrails & Content Filter ────────────────────────
  // Simple safety net to check for unwanted strings, AI artifacts, or marketing slang
  const FORBIDDEN_PATTERNS = [
    /As an AI/i,
    /Here is the post/i,
    /I cannot write/i,
    /gambling|casino|crypto-scam|spam/i,
  ];
  let isClean = true;
  for (const pattern of FORBIDDEN_PATTERNS) {
    if (pattern.test(message)) {
      isClean = false;
      break;
    }
  }
  if (!isClean) {
    console.warn(
      `[content-generator] AI response failed branding guardrails. Falling back to local template.`,
    );
    message = generateTextLocal(topic, format);
    usedProvider = "local-guardrail-fallback";
  }

  // Format message - strip markdown code block wraps (common in AI responses)
  message = message
    .replace(/^```[a-z]*\n/i, "")
    .replace(/\n```$/, "")
    .trim();

  // ── Image pipeline ──────────────────────────────────────────────────────
  let imageUrl = null;
  if (withImage) {
    try {
      if (provider === "cloudflare" && AI_CONFIG.cloudflare.accountId) {
        const imgPrompt = `High quality educational illustration about ${topic.en}, modern flat design, vibrant colors, no text`;
        imageUrl = await generateImageCloudflare(imgPrompt);
      }
    } catch (e) {
      errors.push(`img-cloudflare: ${e.message}`);
    }

    if (!imageUrl || imageUrl.startsWith("data:")) {
      // Use Unsplash for a real URL (FB needs a real URL for photos)
      try {
        imageUrl = await getUnsplashImage(topic);
      } catch (e) {
        errors.push(`img-unsplash: ${e.message}`);
      }
    }
  }

  return {
    message,
    imageUrl,
    topic: { tag: topic.tag, th: topic.th, en: topic.en, emoji: topic.emoji },
    format,
    provider: usedProvider,
    errors: errors.length > 0 ? errors : undefined,
    generatedAt: new Date().toISOString(),
  };
}

/**
 * Return available topics list
 */
function getTopics() {
  return TOPIC_LIBRARY.map((t) => ({
    tag: t.tag,
    th: t.th,
    en: t.en,
    emoji: t.emoji,
  }));
}

/**
 * Return available post formats
 */
function getFormats() {
  return POST_FORMATS;
}

module.exports = {
  generateContent,
  getTopics,
  getFormats,
  TOPIC_LIBRARY,
  POST_FORMATS,
};
