import readline from 'node:readline';
import { handleMcp } from './src/lib/mcp.mjs';

const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
for await (const line of rl) {
  if (!line.trim()) continue;
  try {
    const message = JSON.parse(line);
    const response = await handleMcp(message, { baseUrl: process.env.BASE_URL || 'https://agentcom.org' });
    if (response) process.stdout.write(JSON.stringify(response) + '\n');
  } catch (error) {
    process.stdout.write(JSON.stringify({jsonrpc:'2.0',id:null,error:{code:-32700,message:'Parse error',data:String(error?.message||error)}})+'\n');
  }
}
