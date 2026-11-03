SOURCE C:/Users/Anusha/OneDrive/Desktop/5th sem/dbms/AI Model Failure Investigation and Data Lineage System/failure_lineage_ddl.sql;
SOURCE C:/Users/Anusha/OneDrive/Desktop/5th sem/dbms/AI Model Failure Investigation and Data Lineage System/failure_lineage_dml.sql;
SOURCE C:/Users/Anusha/OneDrive/Desktop/5th sem/dbms/AI Model Failure Investigation and Data Lineage System/failure_lineage_advanced.sql;
1.Database and table verification

USE failure_lineage;

SHOW TABLES;

DESCRIBE emails;
DESCRIBE predictions;
DESCRIBE actual_results;
DESCRIBE failures;
DESCRIBE failure_types;
DESCRIBE feedback;
DESCRIBE data_lineage;


SELECT * FROM users;
SELECT * FROM models;
SELECT * FROM datasets;
SELECT * FROM emails;
SELECT * FROM predictions;
SELECT * FROM actual_results;
SELECT * FROM failures;
SELECT * FROM failure_types;
SELECT * FROM feedback;
SELECT * FROM data_lineage;


Feature 1 — Triggers

triggers automate correctness checking, failure creation, and failure-category auditing.
Query 1: Verify prediction correctness
SELECT
    p.prediction_id,
    p.predicted_class,
    ar.actual_class,
    ar.is_correct
FROM predictions p
JOIN actual_results ar
    ON p.prediction_id = ar.prediction_id;

Query 2: Verify recorded failures
SELECT
    f.failure_id,
    f.prediction_id,
    ft.type_name,
    f.failure_description
FROM failures f
JOIN failure_types ft
    ON f.failure_type_id = ft.failure_type_id;

Query 3: Verify the failure audit log
First check the actual audit table name:
SHOW TABLES;
SELECT * FROM failure_audit_log;

3. Feature 2 — Stored function and stored procedure

SELECT fn_assign_failure_type(
    'Your bank account statement is ready',
    'FINANCE'
) AS suggested_failure_type_id;

SELECT
    failure_type_id,
    type_name,
    description
FROM failure_types;



SHOW PROCEDURE STATUS
WHERE Db = 'failure_lineage';
SHOW CREATE PROCEDURE sp_record_actual_result;



SHOW FUNCTION STATUS
WHERE Db = 'failure_lineage';

SHOW CREATE FUNCTION fn_assign_failure_type;


D. Verify results recorded by the procedure
SELECT
    prediction_id,
    actual_class,
    is_correct,
    verified_by
FROM actual_results;

Check the feedback:
SELECT * FROM feedback;

Check the lineage records:
SELECT * FROM data_lineage;



4. Feature 3 — Transactions

START TRANSACTION;
INSERT INTO emails
    (subject, body)
VALUES
    ('Rollback Test', 'Temporary email for transaction testing');
SELECT *
FROM emails
WHERE subject = 'Rollback Test';
ROLLBACK;
SELECT COUNT(*) AS remaining_test_emails
FROM emails
WHERE subject = 'Rollback Test';


Query 2: Demonstrate SAVEPOINT

START TRANSACTION;
SAVEPOINT before_test;
UPDATE datasets
SET record_count = record_count + 100
WHERE dataset_id = 1;
SELECT dataset_id, record_count
FROM datasets
WHERE dataset_id = 1;
ROLLBACK TO SAVEPOINT before_test;
SELECT dataset_id, record_count
FROM datasets
WHERE dataset_id = 1;
ROLLBACK;



START TRANSACTION;
INSERT INTO emails
    (subject, body)
VALUES
    ('Commit Test', 'Temporary email for commit testing');
COMMIT;
SELECT *
FROM emails
WHERE subject = 'Commit Test';

5. Feature 4 — Views

Query 1: Failure investigation
SELECT * FROM v_failure_investigation;


Query 2: Model accuracy
SELECT * FROM v_model_accuracy;


Query 3: Failure hotspots
SELECT * FROM v_failure_hotspots;

Query 4: Check all views
SHOW FULL TABLES
WHERE Table_type = 'VIEW';

6. Data lineage and investigation queries
These are useful additional queries for your demonstration.
Query 1: Trace each verified prediction
SELECT
    lineage_id,
    prediction_id,
    dataset_id,
    actual_result_id,
    failure_id,
    feedback_id
FROM data_lineage;


Expected: three lineage records, including one correct prediction with a NULL failure ID.
Query 2: Show prediction versus actual result
SELECT
    p.prediction_id,
    e.subject,
    p.predicted_class,
    ar.actual_class,
    ar.is_correct
FROM predictions p
JOIN emails e
    ON p.email_id = e.email_id
JOIN actual_results ar
    ON p.prediction_id = ar.prediction_id;


This assumes the schema uses predictions.email_id and emails.email_id. If your schema uses different column names, check DESCRIBE predictions; and DESCRIBE emails; first.
Query 3: Count correct and incorrect predictions
SELECT
    is_correct,
    COUNT(*) AS prediction_count
FROM actual_results
GROUP BY is_correct;


Query 4: Calculate verified accuracy directly
SELECT
    COUNT(*) AS verified_predictions,
    SUM(is_correct = 1) AS correct_predictions,
    SUM(is_correct = 0) AS failed_predictions,
    ROUND(100 * AVG(is_correct), 2) AS accuracy_percent
FROM actual_results;