import { afterEach, describe, expect, it } from 'vitest';

import { requestClient } from '../../../shared/api';
import { buildImageProxyUrl } from './imageProxy.utils';

describe('buildImageProxyUrl', () => {
  const originalBaseUrl = requestClient.defaults.baseURL;

  afterEach(() => {
    requestClient.defaults.baseURL = originalBaseUrl;
  });

  it('returns a same-origin relative path when no base URL is configured', () => {
    requestClient.defaults.baseURL = undefined;

    expect(buildImageProxyUrl('https://polymarket.com/img/a.png')).toBe(
      '/api/v1/image-proxy?url=https%3A%2F%2Fpolymarket.com%2Fimg%2Fa.png',
    );
  });

  it('prefixes the shared/api base URL and trims trailing slashes', () => {
    requestClient.defaults.baseURL = 'https://api.polyedge.dev/';

    expect(buildImageProxyUrl('https://polymarket.com/x.png')).toBe(
      'https://api.polyedge.dev/api/v1/image-proxy?url=https%3A%2F%2Fpolymarket.com%2Fx.png',
    );
  });

  it('encodes query parameters in the original URL', () => {
    requestClient.defaults.baseURL = '';

    expect(buildImageProxyUrl('https://cdn.test/i?w=1&h=2')).toBe(
      '/api/v1/image-proxy?url=https%3A%2F%2Fcdn.test%2Fi%3Fw%3D1%26h%3D2',
    );
  });
});
