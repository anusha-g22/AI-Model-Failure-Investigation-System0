USE failure_lineage;

-- =========================================================
-- 1. Database objects
-- =========================================================
SHOW TABLES;
SHOW FULL TABLES WHERE TABLE_TYPE = 'VIEW';
SHOW TRIGGERS;

-- =========================================================
-- 2. Sample relational records
-- =========================================================
SELECT * FROM users ORDER BY user_id;
SELECT * FROM models ORDER BY model_id;
SELECT * FROM datasets ORDER BY dataset_id;
SELECT * FROM model_dataset ORDER BY model_id, dataset_id;

-- =========================================================
-- 3. Prediction vs. ground-truth verification
-- =========================================================
SELECT
    p.prediction_id,
    e.subject,
    p.predicted_class,
    p.confidence_score,
    ar.actual_class,
    ar.is_correct,
    ar.verified_at
FROM predictions p
JOIN emails e ON e.email_id = p.email_id
LEFT JOIN actual_results ar ON ar.prediction_id = p.prediction_id
ORDER BY p.prediction_id DESC;

-- =========================================================
-- 4. Accuracy based on verified results only
-- =========================================================
SELECT
    COUNT(*) AS verified_predictions,
    SUM(is_correct = 1) AS correct_predictions,
    SUM(is_correct = 0) AS failed_predictions,
    ROUND(100 * AVG(is_correct), 2) AS accuracy_percent
FROM actual_results;

SELECT * FROM v_model_accuracy;

-- =========================================================
-- 5. Failure investigation and failure hotspots
-- =========================================================
SELECT * FROM v_failure_investigation ORDER BY failure_id DESC;
SELECT * FROM v_failure_hotspots ORDER BY occurrences DESC;

SELECT
    f.failure_id,
    f.prediction_id,
    ft.failure_type_name,
    f.description,
    f.created_at
FROM failures f
JOIN failure_types ft ON ft.failure_type_id = f.failure_type_id
ORDER BY f.failure_id DESC;

-- =========================================================
-- 6. Data lineage
-- =========================================================
SELECT
    lineage_id,
    prediction_id,
    email_id,
    dataset_id,
    model_id,
    actual_id,
    failure_id,
    feedback_id,
    model_version
FROM data_lineage
ORDER BY prediction_id DESC;

-- =========================================================
-- 7. Investigator feedback and audit history
-- =========================================================
SELECT * FROM feedback ORDER BY feedback_id DESC;
SELECT * FROM failure_audit_log ORDER BY audit_id DESC;

-- =========================================================
-- 8. Stored routine metadata
-- =========================================================
SHOW PROCEDURE STATUS WHERE Db = 'failure_lineage';
SHOW FUNCTION STATUS WHERE Db = 'failure_lineage';

-- To inspect routine definitions, run:
-- SHOW CREATE PROCEDURE failure_lineage.sp_record_actual_result;
-- SHOW CREATE FUNCTION failure_lineage.fn_assign_failure_type;

-- =========================================================
-- 9. Transaction example (rolled back; no lasting data change)
-- =========================================================
START TRANSACTION;
UPDATE datasets
SET record_count = record_count + 100
WHERE dataset_id = 1;
SELECT dataset_id, dataset_name, record_count
FROM datasets
WHERE dataset_id = 1;
ROLLBACK;

-- Confirm the original value was restored.
SELECT dataset_id, dataset_name, record_count
FROM datasets
WHERE dataset_id = 1;
