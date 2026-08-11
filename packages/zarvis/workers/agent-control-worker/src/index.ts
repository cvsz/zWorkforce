export interface Env {
  API_GATEWAY_URL: string;
  AUTH_TOKEN: string;
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const authHeader = request.headers.get('Authorization');
    if (!authHeader || authHeader !== `Bearer ${env.AUTH_TOKEN}`) {
      return new Response('Unauthorized', { status: 401 });
    }

    const url = new URL(request.url);
    const targetUrl = `${env.API_GATEWAY_URL}${url.pathname}${url.search}`;

    const newRequest = new Request(targetUrl, {
      method: request.method,
      headers: request.headers,
      body: request.body,
    });

    try {
      const response = await fetch(newRequest);
      return response;
    } catch (e) {
      return new Response('Gateway Error', { status: 502 });
    }
  },
};
