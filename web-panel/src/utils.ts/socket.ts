import type { Socket } from 'socket.io-client';
import { sleep } from './sleep';

export function waitForStateChange(socket: Socket, timeout = 3000) {
  const events = ['connect', 'disconnect'] as const;
  // TODO: cancel promises to avoid leaking
  return Promise.race([
    ...events.map((name) => new Promise((resolve) => socket.on(name, resolve))),
    sleep(timeout).then(() =>
      Promise.reject(
        new Error('Waiting for socket connect or disconnect timedout'),
      ),
    ),
  ]).then(() => events.forEach((name) => socket.off(name)));
}
