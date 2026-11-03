-- =========================================================
-- FILE 2: failure_lineage_dml.sql
-- Run after failure_lineage_ddl.sql
-- =========================================================

USE failure_lineage;

-- 1. USERS
INSERT INTO users (username, role) VALUES
('admin', 'admin'),
('investigator1', 'investigator'),
('alice', 'user'),
('bob', 'user');

-- 2. MODELS
INSERT INTO models (
    model_name,
    model_version,
    description
)
VALUES
(
    'Student Prediction Model',
    'v1.0',
    'Example model for student-related predictions'
),
(
    'Email Classification Model',
    'v2.1',
    'Classifies email messages into categories'
);

-- 3. DATASETS
INSERT INTO datasets (
    dataset_name,
    description,
    record_count
)
VALUES
(
    'EmailDataset',
    'Sample dataset for email classification',
    5
),
(
    'StudentDataset',
    'Sample dataset for student prediction',
    100
);

-- 4. LINK MODELS TO DATASETS
INSERT INTO model_dataset (
    model_id,
    dataset_id,
    usage_purpose
)
VALUES
(1, 2, 'training'),
(2, 1, 'training');

-- 5. SAMPLE EMAIL INPUTS
INSERT INTO emails (
    sender,
    subject,
    email_text,
    metadata
)
VALUES
(
    'bank@example.com',
    'Bank Statement',
    'Bank statement available',
    JSON_OBJECT('source', 'sample', 'type', 'finance')
),
(
    'team@example.com',
    'Team Meeting',
    'Team meeting tomorrow',
    JSON_OBJECT('source', 'sample', 'type', 'work')
),
(
    'offers@example.com',
    'Free Prize',
    'Win a free prize now',
    JSON_OBJECT('source', 'sample', 'type', 'promotion')
),
(
    'cards@example.com',
    'Credit Card Statement',
    'Credit card statement',
    JSON_OBJECT('source', 'sample', 'type', 'finance')
),
(
    'loans@example.com',
    'Loan EMI Reminder',
    'Loan EMI reminder',
    JSON_OBJECT('source', 'sample', 'type', 'finance')
);

-- 6. SAMPLE MODEL PREDICTIONS
-- These are demonstration records, not live AI predictions.
INSERT INTO predictions (
    model_id,
    email_id,
    predicted_class,
    confidence_score
)
VALUES
(2, 1, 'PROMOTION', 0.720),
(2, 2, 'WORK',      0.910),
(2, 3, 'PROMOTION', 0.640),
(2, 4, 'PROMOTION', 0.680),
(2, 5, 'WORK',      0.600);

-- 7. FAILURE CATEGORIES
INSERT INTO failure_types (
    failure_type_name,
    description
)
VALUES
(
    'Incorrect Prediction',
    'The predicted class differs from the verified actual class'
),
(
    'Insufficient Input Data',
    'The input may not contain enough information'
),
(
    'Insufficient Training Data',
    'The model may lack sufficient examples for the case'
),
(
    'Poor Quality Data',
    'The input data may contain quality problems'
);

-- =========================================================
-- VERIFY THE INSERTED SAMPLE DATA
-- =========================================================

SELECT * FROM users;
SELECT * FROM models;
SELECT * FROM datasets;
SELECT * FROM model_dataset;
SELECT * FROM emails;
SELECT * FROM predictions;
SELECT * FROM failure_types;

-- actual_results will be empty until File 3 is executed.
SELECT * FROM actual_results;