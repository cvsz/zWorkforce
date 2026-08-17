---
name: social-content-publisher
description: Workflow for drafting, validating, and publishing multi-platform social media campaigns across Facebook, Instagram, TikTok, YouTube, X, and LinkedIn.
---

# Social Content Publisher Skill

## Purpose
Enables autonomous and operator-supervised drafting, 12-point QA compliance, asset rendering, and approval-gated publishing across major social platforms.

## Workflow Steps:
1. **Content Strategy & Copywriting**:
   - Generate per-platform hooks, captions, hashtags, and CTA according to brand tone.
2. **Media Asset Verification**:
   - Check aspect ratios (9:16 vertical for TikTok/Reels/Shorts, 1:1 or 16:9 for Feed/YouTube).
3. **12-Point QA & Brand Safety**:
   - Verify logo clearance, palette compliance, and claim substantiation.
4. **Human Approval Gate**:
   - Submit mutating publication request through the control plane before triggering live API upload.
5. **Durable Multi-Platform Distribution**:
   - Dispatch via `social_connector` tool to Facebook Pages, Instagram Graph, TikTok Content, YouTube Data API, X v2, or LinkedIn UGC.
