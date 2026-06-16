import { BedrockAgentCoreClient, InvokeAgentRuntimeCommand } from '@aws-sdk/client-bedrock-agentcore';

const agentClient = new BedrockAgentCoreClient({ region: process.env.AWS_REGION });

const AGENT_RUNTIME_ARN = process.env.AGENT_RUNTIME_ARN;

export const handler = awslambda.streamifyResponse(async (event, responseStream, _context) => {
  responseStream = awslambda.HttpResponseStream.from(responseStream, {
    statusCode: 200,
    headers: {
      'Content-Type': 'application/x-ndjson',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    }
  });

  try {
    const body = JSON.parse(event.body || '{}');
    const { message, threadId } = body;

    // Get user from Cognito authorizer claims (already validated by API Gateway)
    const claims = event.requestContext?.authorizer?.claims || {};
    const userId = claims.sub;

    const payloadObj = {
      prompt: message,
      user_id: userId,
      thread_id: threadId || `fallback_${Date.now()}`,
    };

    console.log('Invoking agent with payload:', payloadObj);

    const response = await agentClient.send(new InvokeAgentRuntimeCommand({
      agentRuntimeArn: AGENT_RUNTIME_ARN,
      runtimeSessionId: `session_${threadId || Date.now()}`,
      payload: JSON.stringify(payloadObj),
      qualifier: 'DEFAULT'
    }));

    console.log('Response contentType:', response.contentType);

    if (response.contentType?.includes('text/event-stream')) {
      for await (const chunk of response.response) {
        const text = new TextDecoder().decode(chunk);
        const lines = text.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim();
            if (data) {
              try {
                const parsedText = JSON.parse(data);
                responseStream.write(JSON.stringify({ type: 'chunk', text: parsedText }) + '\n');
              } catch {
                responseStream.write(JSON.stringify({ type: 'chunk', text: data }) + '\n');
              }
            }
          }
        }
      }
    } else {
      const bodyStr = await response.response.transformToString();
      responseStream.write(JSON.stringify({ type: 'chunk', text: bodyStr }) + '\n');
    }

    responseStream.write(JSON.stringify({ type: 'done' }) + '\n');
  } catch (error) {
    console.error('Streaming error:', error);
    responseStream.write(JSON.stringify({ type: 'error', error: error.message }) + '\n');
  }

  responseStream.end();
});
