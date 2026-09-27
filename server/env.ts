import dotenv from 'dotenv';
import * as tls from 'node:tls';

// Runs before auth/database/AI imports. Shell values take precedence.
dotenv.config({ path: ['.env.local', '.env'], quiet: true });

// Honor locally trusted enterprise CAs on Windows without disabling certificate verification.
if (process.platform === 'win32' && typeof tls.setDefaultCACertificates === 'function') {
  tls.setDefaultCACertificates([...tls.getCACertificates('default'), ...tls.getCACertificates('system')]);
}
