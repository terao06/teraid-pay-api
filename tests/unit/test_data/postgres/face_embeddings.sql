INSERT INTO face_embeddings (user_id, embedding, extension_type, is_active)
VALUES
  -- test_get_nearest_face_embedding_excludes_specified_user_id で除外対象外の最短有効レコードとして使用
  -- Face Register API の test_with_db で顔特徴量を登録・更新するユーザーとして使用
  (101, ('[' || array_to_string(ARRAY[0.8] || array_fill(0.0, ARRAY[511]), ',') || ']')::vector, 'png', TRUE),
  -- test_get_nearest_face_embedding_returns_first_matched_embedding で最短有効レコードとして使用
  -- test_get_nearest_face_embedding_excludes_specified_user_id で除外対象 user_id として使用
  (102, ('[' || array_to_string(ARRAY[1.0] || array_fill(0.0, ARRAY[511]), ',') || ']')::vector, 'jpeg', TRUE),
  -- nearest face 検索 fixture で返却されない非アクティブ候補として使用
  (103, ('[' || array_to_string(ARRAY[1.0] || array_fill(0.0, ARRAY[511]), ',') || ']')::vector, 'jpeg', FALSE),
  -- nearest face 検索 fixture で閾値内検索に一致しない遠い有効候補として使用
  (105, ('[' || array_to_string(ARRAY[0.0, 1.0] || array_fill(0.0, ARRAY[510]), ',') || ']')::vector, 'jpg', TRUE),
  -- test_delete_face_embedding_sets_deleted_at_and_updated_at で削除対象として使用
  (108, ('[' || array_to_string(ARRAY[0.0, 0.5] || array_fill(0.0, ARRAY[510]), ',') || ']')::vector, 'png', TRUE),
  -- build_local_db.py で test_face.png から生成した embedding に更新するユーザー
  (107, ('[' || array_to_string(ARRAY[0.0] || array_fill(0.0, ARRAY[511]), ',') || ']')::vector, 'png', TRUE),
  
  (109, ('[' || array_to_string(ARRAY[0.0, 0.5] || array_fill(0.0, ARRAY[510]), ',') || ']')::vector, 'png', TRUE);
