// minio.js — MinIO (S3-compatible) client
const Minio = require('minio');

const minioClient = new Minio.Client({
  endPoint:  process.env.MINIO_ENDPOINT || 'minio',
  port:      parseInt(process.env.MINIO_PORT || '9000'),
  useSSL:    false,                                     // HTTP — intentional for demo
  accessKey: process.env.MINIO_ACCESS_KEY || 'minioadmin',
  secretKey: process.env.MINIO_SECRET_KEY || 'minioadmin',
});

const BUCKET_NAME = 'vaultnote-files';

async function ensureBucket() {
  const exists = await minioClient.bucketExists(BUCKET_NAME);
  if (!exists) {
    await minioClient.makeBucket(BUCKET_NAME, 'us-east-1');
    console.log(`MinIO bucket "${BUCKET_NAME}" created`);
  }
}

module.exports = { minioClient, BUCKET_NAME, ensureBucket };
