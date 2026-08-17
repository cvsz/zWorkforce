/**
 * rerank_engine.mjs
 *
 * Zider High-Precision Rerank & Web Grounding Pipeline.
 * Reranks retrieved vector search chunks and formats citation anchors.
 */

export class RerankEngine {
  constructor(options = {}) {
    this.topK = options.topK || 3;
    this.minScore = options.minScore !== undefined ? options.minScore : 0.50;
  }

  rerankChunks(query, chunks = []) {
    if (!query || !Array.isArray(chunks)) return [];

    const queryTerms = query.toLowerCase().split(/\s+/).filter(Boolean);

    const scored = chunks.map((chunk) => {
      const text = (chunk.text || "").toLowerCase();
      let overlapCount = 0;
      for (const term of queryTerms) {
        if (text.includes(term)) overlapCount++;
      }
      const relevance = queryTerms.length > 0 ? overlapCount / queryTerms.length : 0.5;
      const finalScore = Number(((chunk.baseScore || 0.5) * 0.4 + relevance * 0.6).toFixed(2));

      return {
        ...chunk,
        score: finalScore,
      };
    });

    return scored
      .filter((c) => c.score >= this.minScore)
      .sort((a, b) => b.score - a.score)
      .slice(0, this.topK);
  }
}

export class YouTubeSync {
  constructor() {
    this.transcripts = [];
  }

  loadTranscript(cues = []) {
    this.transcripts = Array.isArray(cues) ? cues : [];
  }

  getCurrentCue(currentTimeSeconds) {
    const time = Number(currentTimeSeconds || 0);
    return (
      this.transcripts.find(
        (cue) => time >= cue.start && time <= cue.start + cue.duration
      ) || null
    );
  }
}
