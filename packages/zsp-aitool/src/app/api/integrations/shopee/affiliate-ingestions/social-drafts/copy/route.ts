import { NextResponse } from "next/server";
import { withAuth } from "@/middleware/auth-middleware";
import { shopeeAffiliateSocialDraftService } from "@/services/ShopeeAffiliateSocialDraftService";

export const POST = withAuth(async (request) => {
  const body = await request.json().catch(() => ({}));
  const draft = await shopeeAffiliateSocialDraftService.markCopied(request.auth.userId, String(body?.draftId ?? ""));
  return NextResponse.json({ ok: true, data: draft });
});
