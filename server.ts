import * as mqtt from 'mqtt';

async function main() {
  const topic = '#';
  const client = await mqtt.connectAsync('mqtt://192.168.1.144');

  await client.subscribeAsync(topic);
  client.on('message', (topic, message) => {
    // message is Buffer
    console.log('topic:', topic, 'message:', message.toString());
  });

  console.log('client connected');
  await client.publishAsync(topic, 'hey');
}

main().catch(console.error);
