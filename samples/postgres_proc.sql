CREATE OR REPLACE FUNCTION main2(
    batch_id INTEGER,
    result_msg TEXT
)
RETURNS VOID AS $$
DECLARE
    job_id INTEGER;
    status_flag TEXT;
    dynamic_sql TEXT;
    temp_value TEXT;
BEGIN
    CREATE TEMP TABLE my_temp_table (
        job_id INTEGER,
        status TEXT
    );

    DECLARE job_cursor CURSOR FOR
        SELECT id FROM jobs WHERE batch_id = batch_id;

    FETCH job_cursor INTO job_id;

    WHILE FOUND LOOP
        BEGIN
            IF job_id = 1 THEN
                status_flag := 'First Job';
            ELSE
                IF job_id > 10 THEN
                    status_flag := 'Big Job';
                ELSE
                    temp_value := 'Regular Job';
                END IF;
            END IF;

            IF status_flag = 'Big Job' THEN
                INSERT INTO big_jobs (job_id) VALUES (job_id);
            ELSE
                INSERT INTO regular_jobs (job_id) VALUES (job_id);
            END IF;

            dynamic_sql := 'UPDATE jobs SET processed = TRUE WHERE id = ' || CAST(job_id AS TEXT);
            EXECUTE IMMEDIATE dynamic_sql;
        EXCEPTION
            WHEN OTHERS THEN
                RAISE NOTICE 'Default exception handler executed.';
        END;

        FETCH job_cursor INTO job_id;
    END LOOP;

    result_msg := 'Batch Processing Complete';

    COMMIT;

    RETURN 0;
END;
$$ LANGUAGE plpgsql;