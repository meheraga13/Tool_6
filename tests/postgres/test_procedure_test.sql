-- PostgreSQL Test Script for test_procedure
DO $$ 
DECLARE 
    test_count INTEGER := 0; 
    pass_count INTEGER := 0;
    verification_count INTEGER;
    result_msg_1 TEXT;
    result_msg_1 TEXT;
    result_msg_1 TEXT;

BEGIN

    -- Test 1: Valid input test
    test_count := test_count + 1;
    BEGIN
        -- Call the procedure
        CALL test_procedure('123', result_msg_1);
        RAISE NOTICE 'Test %: % - Completed', test_count, 'Valid input test';
        RAISE NOTICE 'Output parameter result_msg: %', result_msg_1;

        
        -- Perform verifications
        SELECT COUNT(*) INTO verification_count FROM users WHERE id = 123 AND status = 'active';
        IF verification_count > 0 THEN 
            RAISE NOTICE 'Verification passed: Verify record was processed correctly (Count: %)', verification_count; 
            pass_count := pass_count + 1;
        ELSE 
            RAISE NOTICE 'Verification failed: Verify record was processed correctly (Count: 0)'; 
        END IF;

    EXCEPTION 
        WHEN OTHERS THEN 
            RAISE NOTICE 'Test % failed with error: %', test_count, SQLERRM; 
    END;
    
    -- Test 2: Boundary value test
    test_count := test_count + 1;
    BEGIN
        -- Call the procedure
        CALL test_procedure(NULL, result_msg_1);
        RAISE NOTICE 'Test %: % - Completed', test_count, 'Boundary value test';
        RAISE NOTICE 'Output parameter result_msg: %', result_msg_1;

        
        -- Perform verifications
        SELECT COUNT(*) INTO verification_count FROM users WHERE status IS NULL OR status = 'pending';
        IF verification_count > 0 THEN 
            RAISE NOTICE 'Verification passed: Verify null handling (Count: %)', verification_count; 
            pass_count := pass_count + 1;
        ELSE 
            RAISE NOTICE 'Verification failed: Verify null handling (Count: 0)'; 
        END IF;

    EXCEPTION 
        WHEN OTHERS THEN 
            RAISE NOTICE 'Test % failed with error: %', test_count, SQLERRM; 
    END;
    
    -- Test 3: Error condition test
    test_count := test_count + 1;
    BEGIN
        -- Call the procedure
        CALL test_procedure('-1', result_msg_1);
        RAISE NOTICE 'Test %: % - Completed', test_count, 'Error condition test';
        RAISE NOTICE 'Output parameter result_msg: %', result_msg_1;

        
        -- Perform verifications
        SELECT COUNT(*) INTO verification_count FROM users WHERE error_flag = true;
        IF verification_count > 0 THEN 
            RAISE NOTICE 'Verification passed: Verify error handling (Count: %)', verification_count; 
            pass_count := pass_count + 1;
        ELSE 
            RAISE NOTICE 'Verification failed: Verify error handling (Count: 0)'; 
        END IF;

    EXCEPTION 
        WHEN OTHERS THEN 
            RAISE NOTICE 'Test % failed with error: %', test_count, SQLERRM; 
    END;
    
    -- Summary
    RAISE NOTICE 'Test Summary: % verifications passed out of % total tests', pass_count, test_count;
    
    -- Cleanup
    DELETE FROM users;
END $$;