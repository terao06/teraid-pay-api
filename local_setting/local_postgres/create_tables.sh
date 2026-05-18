#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" <<-'EOSQL'

    -- ==========================================
    -- pgvector 拡張有効化
    -- ==========================================
    CREATE EXTENSION IF NOT EXISTS vector;

    -- ==========================================
    -- 顔特徴量テーブル
    -- ==========================================
    CREATE TABLE IF NOT EXISTS face_embeddings (
        face_embedding_id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,

        -- 512次元 embedding
        embedding VECTOR(512) NOT NULL,

        -- 画像の拡張子
        extension_type VARCHAR(10) NOT NULL
            CHECK (extension_type IN ('jpeg', 'png', 'jpg')),

        is_active BOOLEAN NOT NULL DEFAULT TRUE,

        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    -- ==========================================
    -- HNSWインデックス（高速検索）
    -- cosine類似度用
    -- ==========================================
    CREATE INDEX IF NOT EXISTS idx_face_embedding_hnsw
    ON face_embeddings
    USING hnsw (
        embedding vector_cosine_ops
    );

EOSQL