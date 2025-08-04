CREATE PROCEDURE main2
    @batch_id INTEGER,
    @result_msg TEXT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @job_id INTEGER;
    DECLARE @status_flag VARCHAR(50);
    DECLARE @dynamic_sql VARCHAR(1000);
    DECLARE @temp_value VARCHAR(50);
    
    CREATE TABLE #my_temp_table (
        job_id INTEGER,
        status VARCHAR(50)
    );
    
    DECLARE job_cursor CURSOR FOR
        SELECT id FROM jobs WHERE batch_id = @batch_id;
    
    OPEN job_cursor;
    FETCH NEXT FROM job_cursor INTO @job_id;
    
    WHILE @@FETCH_STATUS = 0
    BEGIN
        BEGIN TRY
            IF @job_id = 1
                SET @status_flag = 'First Job';
            ELSE
                IF @job_id > 10
                    SET @status_flag = 'Big Job';
                ELSE
                    SET @temp_value = 'Regular Job';
            
            IF @status_flag = 'Big Job'
                INSERT INTO big_jobs (job_id) VALUES (@job_id);
            ELSE
                INSERT INTO regular_jobs (job_id) VALUES (@job_id);
            
            SET @dynamic_sql = 'UPDATE jobs SET processed = 1 WHERE id = ' + CAST(@job_id AS VARCHAR);
            EXEC (@dynamic_sql);
        
        END TRY
        BEGIN CATCH
            PRINT 'Default exception handler executed.';
        END CATCH;
        
        FETCH NEXT FROM job_cursor INTO @job_id;
    END
    
    CLOSE job_cursor;
    DEALLOCATE job_cursor;
    
    SET @result_msg = 'Batch Processing Complete';
    
    COMMIT TRANSACTION;
    
    RETURN 0;
END
GO
