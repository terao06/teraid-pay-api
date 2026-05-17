INSERT INTO face_embeddings (user_id, embedding, is_active, deleted_at)
VALUES
  (101, ('[' || array_to_string(ARRAY[0.8] || array_fill(0.0, ARRAY[511]), ',') || ']')::vector, TRUE, NULL),
  (102, ('[' || array_to_string(ARRAY[1.0] || array_fill(0.0, ARRAY[511]), ',') || ']')::vector, TRUE, NULL),
  (103, ('[' || array_to_string(ARRAY[1.0] || array_fill(0.0, ARRAY[511]), ',') || ']')::vector, FALSE, NULL),
  (104, ('[' || array_to_string(ARRAY[1.0] || array_fill(0.0, ARRAY[511]), ',') || ']')::vector, TRUE, '2026-01-01 00:00:00'),
  (105, ('[' || array_to_string(ARRAY[0.0, 1.0] || array_fill(0.0, ARRAY[510]), ',') || ']')::vector, TRUE, NULL);
