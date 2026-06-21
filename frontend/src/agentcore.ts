const apiGatewayUrl = (import.meta as any).env.VITE_API_GATEWAY_URL as string | undefined;

export interface InvokeAgentRequest {
  prompt: string;
  threadId?: string;
  onChunk?: (chunk: string) => void;
}

export interface InvokeAgentResponse {
  response: string;
}

export const invokeAgent = async (request: InvokeAgentRequest): Promise<InvokeAgentResponse> => {
  try {
    // Call API Gateway, receive NDJSON stream
    if (!apiGatewayUrl) {
      throw new Error('API Gateway URL not configured. Please check VITE_API_GATEWAY_URL.');
    }

    const { getIdToken } = await import('./auth');
    const token = await getIdToken();
    if (!token) {
      throw new Error('Not authenticated - no access token available');
    }

    const url = `${apiGatewayUrl}/api/chat/streaming`;
    console.log('Invoking API Gateway:', { url });

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({
        message: request.prompt,
        threadId: request.threadId,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API Gateway invocation failed: ${response.status} ${response.statusText} - ${errorText}`);
    }

    if (request.onChunk && response.body) {
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullResponse = '';
      let buffer = '';

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (!line.trim()) continue;
            try {
              const parsed = JSON.parse(line);
              if (parsed.type === 'chunk') {
                fullResponse += parsed.text;
                request.onChunk(parsed.text);
              } else if (parsed.type === 'done') {
                return { response: fullResponse };
              } else if (parsed.type === 'error') {
                throw new Error(parsed.error || 'Unknown agent error');
              }
            } catch (parseError) {
              console.warn('Failed to parse NDJSON line:', line, parseError);
            }
          }
        }
        return { response: fullResponse };
      } finally {
        reader.releaseLock();
      }
    }

    // Non-streaming fallback
    const text = await response.text();
    const lines = text.split('\n').filter(l => l.trim());
    let fullResponse = '';
    for (const line of lines) {
      try {
        const parsed = JSON.parse(line);
        if (parsed.type === 'chunk') fullResponse += parsed.text;
      } catch { /* skip */ }
    }
    return { response: fullResponse };

  } catch (error: any) {
    console.error('Agent invocation error:', error);
    throw new Error(`Failed to invoke agent: ${error.message}`);
  }
};
