-- =========================================================
-- FILE 3: failure_lineage_advanced.sql
-- Run after DDL and DML, on a fresh sample dataset.
-- Run this file only once unless you reset the database.
-- =========================================================

USE failure_lineage;

-- =========================================================
-- 1. STORED FUNCTION: Assign a failure category
--
-- Rules:
--   Poor-quality input containing control characters -> 4
--   Fewer than 4 words                            -> 2
--   3 or more earlier failures with same actual class -> 3
--   Otherwise                                     -> 1
--
-- Note: These are example investigation rules, not an AI model.
-- =========================================================

DROP FUNCTION IF EXISTS fn_assign_failure_type;

DELIMITER $$

CREATE FUNCTION fn_assign_failure_type(
    p_text TEXT,
    p_actual_class VARCHAR(50),
    p_prediction_id INT
)
RETURNS INT
READS SQL DATA
BEGIN
    DECLARE v_word_count INT DEFAULT 0;
    DECLARE v_prior_failures INT DEFAULT 0;

    SET p_text = TRIM(COALESCE(p_text, ''));

    IF p_text = '' THEN
        SET v_word_count = 0;
    ELSE
        SET v_word_count =
            1 + CHAR_LENGTH(p_text)
              - CHAR_LENGTH(REPLACE(p_text, ' ', ''));
    END IF;

    -- Count earlier failed cases with the same actual class.
    -- Exclude the current prediction.
    SELECT COUNT(*)
    INTO v_prior_failures
    FROM failures f
    JOIN actual_results ar
        ON f.prediction_id = ar.prediction_id
    WHERE ar.actual_class = p_actual_class
      AND f.prediction_id <> p_prediction_id;

    IF COALESCE(p_text, '') REGEXP '[[:cntrl:]]' THEN
        RETURN 4;

    ELSEIF v_word_count < 4 THEN
        RETURN 2;

    ELSEIF v_prior_failures >= 3 THEN
        RETURN 3;

    ELSE
        RETURN 1;
    END IF;
END$$

DELIMITER ;

-- =========================================================
-- 2. STORED PROCEDURE: Record a verified actual result
--
-- The procedure:
--   a. Validates the prediction, user, and actual class.
--   b. Inserts the actual result.
--   c. Lets triggers calculate correctness/create a failure.
--   d. Inserts feedback.
--   e. Assigns a failure category when needed.
--   f. Records data lineage.
--   g. Commits the transaction.
-- =========================================================

DROP PROCEDURE IF EXISTS sp_record_actual_result;

DELIMITER $$

CREATE PROCEDURE sp_record_actual_result(
    IN p_prediction_id INT,
    IN p_actual_class VARCHAR(50),
    IN p_user_id INT,
    IN p_comment TEXT
)
BEGIN
    DECLARE v_prediction_count INT DEFAULT 0;
    DECLARE v_user_count INT DEFAULT 0;
    DECLARE v_model_id INT;
    DECLARE v_email_id INT;
    DECLARE v_dataset_id INT;
    DECLARE v_actual_id INT;
    DECLARE v_failure_id INT DEFAULT NULL;
    DECLARE v_feedback_id INT;
    DECLARE v_predicted_class VARCHAR(50);
    DECLARE v_email_text TEXT;
    DECLARE v_model_version VARCHAR(50);
    DECLARE v_is_correct TINYINT DEFAULT 0;
    DECLARE v_failure_type_id INT;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    -- Check prediction exists.
    SELECT COUNT(*)
    INTO v_prediction_count
    FROM predictions
    WHERE prediction_id = p_prediction_id;

    IF v_prediction_count = 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Prediction ID does not exist';
    END IF;

    -- Prevent duplicate actual results.
    SELECT COUNT(*)
    INTO v_prediction_count
    FROM actual_results
    WHERE prediction_id = p_prediction_id;

    IF v_prediction_count > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT =
                'This prediction already has an actual result';
    END IF;

    -- Validate user.
    SELECT COUNT(*)
    INTO v_user_count
    FROM users
    WHERE user_id = p_user_id;

    IF v_user_count = 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'User ID does not exist';
    END IF;

    -- Validate actual class.
    IF p_actual_class IS NULL
       OR TRIM(p_actual_class) = '' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Actual class cannot be empty';
    END IF;

    -- Retrieve the prediction, input, and model details.
    SELECT
        p.model_id,
        p.email_id,
        p.predicted_class,
        e.email_text,
        m.model_version
    INTO
        v_model_id,
        v_email_id,
        v_predicted_class,
        v_email_text,
        v_model_version
    FROM predictions p
    JOIN emails e
        ON p.email_id = e.email_id
    JOIN models m
        ON p.model_id = m.model_id
    WHERE p.prediction_id = p_prediction_id;

    -- Select a linked dataset for lineage.
    SELECT MIN(dataset_id)
    INTO v_dataset_id
    FROM model_dataset
    WHERE model_id = v_model_id;

    IF v_dataset_id IS NULL THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT =
                'No dataset is linked to this model';
    END IF;

    -- Insert the actual result.
    -- trg_set_is_correct sets is_correct automatically.
    -- trg_auto_create_failure creates a failure if incorrect.
    INSERT INTO actual_results (
        prediction_id,
        actual_class,
        verified_by
    )
    VALUES (
        p_prediction_id,
        UPPER(TRIM(p_actual_class)),
        p_user_id
    );

    SET v_actual_id = LAST_INSERT_ID();

    SELECT is_correct
    INTO v_is_correct
    FROM actual_results
    WHERE actual_id = v_actual_id;

    -- Record feedback for the investigation.
    INSERT INTO feedback (
        prediction_id,
        user_id,
        feedback_text
    )
    VALUES (
        p_prediction_id,
        p_user_id,
        p_comment
    );

    SET v_feedback_id = LAST_INSERT_ID();

    -- If the trigger created a failure, classify it.
    IF v_is_correct = 0 THEN

        SET v_failure_type_id = fn_assign_failure_type(
            v_email_text,
            UPPER(TRIM(p_actual_class)),
            p_prediction_id
        );

        SELECT failure_id
        INTO v_failure_id
        FROM failures
        WHERE prediction_id = p_prediction_id;

        UPDATE failures
        SET
            failure_type_id = v_failure_type_id,
            feedback_id = v_feedback_id,
            description = CONCAT(
                'Predicted ',
                v_predicted_class,
                '; verified actual class is ',
                UPPER(TRIM(p_actual_class)),
                '. Investigation: ',
                COALESCE(p_comment, 'No comment provided')
            )
        WHERE failure_id = v_failure_id;

    END IF;

    -- Record the complete lineage for this prediction.
    INSERT INTO data_lineage (
        prediction_id,
        email_id,
        dataset_id,
        model_id,
        actual_id,
        failure_id,
        feedback_id,
        model_version,
        preprocessing_steps,
        feature_extraction
    )
    VALUES (
        p_prediction_id,
        v_email_id,
        v_dataset_id,
        v_model_id,
        v_actual_id,
        v_failure_id,
        v_feedback_id,
        v_model_version,
        'Sample input stored as email text; no live preprocessing pipeline',
        'Email text used as the input feature for the sample record'
    );

    COMMIT;

    -- Return a summary of the operation.
    SELECT
        p_prediction_id AS prediction_id,
        v_predicted_class AS predicted_class,
        UPPER(TRIM(p_actual_class)) AS actual_class,
        v_is_correct AS is_correct,
        v_failure_id AS failure_id,
        v_feedback_id AS feedback_id,
        v_actual_id AS actual_id;
END$$

DELIMITER ;

-- =========================================================
-- 3. RECORD SAMPLE ACTUAL RESULTS
-- These are demonstration labels used to test the database.
-- Run these CALL statements only once on this sample dataset.
-- =========================================================

CALL sp_record_actual_result(
    1,
    'FINANCE',
    3,
    'Bank statement should be classified as FINANCE'
);

CALL sp_record_actual_result(
    2,
    'WORK',
    3,
    'Team meeting correctly classified as WORK'
);

CALL sp_record_actual_result(
    3,
    'SPAM',
    3,
    'Prize message should be classified as SPAM'
);

CALL sp_record_actual_result(
    4,
    'FINANCE',
    4,
    'Credit card statement should be classified as FINANCE'
);

CALL sp_record_actual_result(
    5,
    'FINANCE',
    4,
    'Loan EMI reminder should be classified as FINANCE'
);

-- =========================================================
-- 4. VIEW: MODEL ACCURACY
-- Includes models even if they have no verified predictions.
-- Accuracy is calculated only from verified actual results.
-- =========================================================

CREATE OR REPLACE VIEW v_model_accuracy AS
SELECT
    m.model_id,
    m.model_name,
    m.model_version,
    COUNT(ar.actual_id) AS verified_predictions,

    COALESCE(
        SUM(
            CASE
                WHEN ar.actual_id IS NOT NULL
                     AND ar.is_correct = 1
                THEN 1
                ELSE 0
            END
        ),
        0
    ) AS correct_predictions,

    COALESCE(
        SUM(
            CASE
                WHEN ar.actual_id IS NOT NULL
                     AND ar.is_correct = 0
                THEN 1
                ELSE 0
            END
        ),
        0
    ) AS failed_predictions,

    ROUND(
        100.0 *
        SUM(
            CASE
                WHEN ar.actual_id IS NOT NULL
                     AND ar.is_correct = 1
                THEN 1
                ELSE 0
            END
        )
        / NULLIF(COUNT(ar.actual_id), 0),
        2
    ) AS accuracy_percent

FROM models m
LEFT JOIN predictions p
    ON m.model_id = p.model_id
LEFT JOIN actual_results ar
    ON p.prediction_id = ar.prediction_id
GROUP BY
    m.model_id,
    m.model_name,
    m.model_version;

-- =========================================================
-- 5. VIEW: FAILURE HOTSPOTS
-- Groups repeated failure patterns.
-- =========================================================

CREATE OR REPLACE VIEW v_failure_hotspots AS
SELECT
    p.predicted_class,
    ar.actual_class,
    ft.failure_type_name,
    COUNT(*) AS occurrences
FROM failures f
JOIN predictions p
    ON f.prediction_id = p.prediction_id
JOIN actual_results ar
    ON f.prediction_id = ar.prediction_id
JOIN failure_types ft
    ON f.failure_type_id = ft.failure_type_id
GROUP BY
    p.predicted_class,
    ar.actual_class,
    ft.failure_type_name;

-- =========================================================
-- 6. VERIFY THE RESULTS
-- =========================================================

-- Prediction versus actual result
SELECT
    p.prediction_id,
    p.predicted_class,
    ar.actual_class,
    ar.is_correct
FROM predictions p
JOIN actual_results ar
    ON p.prediction_id = ar.prediction_id
ORDER BY p.prediction_id;

-- Failures and their assigned categories
SELECT
    f.failure_id,
    f.prediction_id,
    ft.failure_type_name,
    f.description
FROM failures f
JOIN failure_types ft
    ON f.failure_type_id = ft.failure_type_id
ORDER BY f.failure_id;

-- Model accuracy
SELECT * FROM v_model_accuracy;

-- Failure hotspots
SELECT * FROM v_failure_hotspots;

-- Data lineage
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
ORDER BY prediction_id;

-- Trigger audit history
SELECT *
FROM failure_audit_log
ORDER BY audit_id;

-- Detailed investigation view
SELECT *
FROM v_failure_investigation;

-- =========================================================
-- 7. TRANSACTION DEMONSTRATION
-- This example rolls back its update, preserving the count.
-- =========================================================

START TRANSACTION;

UPDATE datasets
SET record_count = record_count + 100
WHERE dataset_id = 1;

SELECT
    dataset_id,
    dataset_name,
    record_count
FROM datasets
WHERE dataset_id = 1;

ROLLBACK;

SELECT
    dataset_id,
    dataset_name,
    record_count
FROM datasets
WHERE dataset_id = 1;