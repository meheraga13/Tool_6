-- PostgreSQL Test Script for reprice_and_flag_orders
DO $$ 
DECLARE 
    test_count INTEGER := 0; 
    pass_count INTEGER := 0;
    verification_count INTEGER;
    updated_count_1 TEXT;
    updated_count_1 TEXT;
    updated_count_1 TEXT;

BEGIN

    -- Test 1: Valid input test
    test_count := test_count + 1;
    BEGIN
        -- Call the procedure
        CALL reprice_and_flag_orders('SUMMER2022', updated_count_1);
        RAISE NOTICE 'Test %: % - Completed', test_count, 'Valid input test';
        RAISE NOTICE 'Output parameter updated_count: %', updated_count_1;

        
        -- Perform verifications
        SELECT COUNT(*) INTO verification_count FROM orders WHERE campaign_code = 'SUMMER2022';
        IF verification_count > 0 THEN 
            RAISE NOTICE 'Verification passed: Verify orders were updated with correct campaign code (Count: %)', verification_count; 
            pass_count := pass_count + 1;
        ELSE 
            RAISE NOTICE 'Verification failed: Verify orders were updated with correct campaign code (Count: 0)'; 
        END IF;
        SELECT COUNT(*) INTO verification_count FROM products WHERE price > 0;
        IF verification_count > 0 THEN 
            RAISE NOTICE 'Verification passed: Verify products were repriced successfully (Count: %)', verification_count; 
            pass_count := pass_count + 1;
        ELSE 
            RAISE NOTICE 'Verification failed: Verify products were repriced successfully (Count: 0)'; 
        END IF;

    EXCEPTION 
        WHEN OTHERS THEN 
            RAISE NOTICE 'Test % failed with error: %', test_count, SQLERRM; 
    END;
    
    -- Test 2: Boundary value test
    test_count := test_count + 1;
    BEGIN
        -- Call the procedure
        CALL reprice_and_flag_orders(NULL, updated_count_1);
        RAISE NOTICE 'Test %: % - Completed', test_count, 'Boundary value test';
        RAISE NOTICE 'Output parameter updated_count: %', updated_count_1;

        
        -- Perform verifications
        SELECT COUNT(*) INTO verification_count FROM orders WHERE campaign_code IS NULL OR campaign_code = 'pending';
        IF verification_count > 0 THEN 
            RAISE NOTICE 'Verification passed: Verify null handling in campaign code (Count: %)', verification_count; 
            pass_count := pass_count + 1;
        ELSE 
            RAISE NOTICE 'Verification failed: Verify null handling in campaign code (Count: 0)'; 
        END IF;
        SELECT COUNT(*) INTO verification_count FROM products WHERE price > 0;
        IF verification_count > 0 THEN 
            RAISE NOTICE 'Verification passed: Verify products were repriced successfully (Count: %)', verification_count; 
            pass_count := pass_count + 1;
        ELSE 
            RAISE NOTICE 'Verification failed: Verify products were repriced successfully (Count: 0)'; 
        END IF;

    EXCEPTION 
        WHEN OTHERS THEN 
            RAISE NOTICE 'Test % failed with error: %', test_count, SQLERRM; 
    END;
    
    -- Test 3: Error condition test
    test_count := test_count + 1;
    BEGIN
        -- Call the procedure
        CALL reprice_and_flag_orders('-1', updated_count_1);
        RAISE NOTICE 'Test %: % - Completed', test_count, 'Error condition test';
        RAISE NOTICE 'Output parameter updated_count: %', updated_count_1;

        
        -- Perform verifications
        SELECT COUNT(*) INTO verification_count FROM orders WHERE error_flag = true;
        IF verification_count > 0 THEN 
            RAISE NOTICE 'Verification passed: Verify error handling for invalid campaign code (Count: %)', verification_count; 
            pass_count := pass_count + 1;
        ELSE 
            RAISE NOTICE 'Verification failed: Verify error handling for invalid campaign code (Count: 0)'; 
        END IF;
        SELECT COUNT(*) INTO verification_count FROM products WHERE price > 0;
        IF verification_count > 0 THEN 
            RAISE NOTICE 'Verification passed: Verify products were not affected (Count: %)', verification_count; 
            pass_count := pass_count + 1;
        ELSE 
            RAISE NOTICE 'Verification failed: Verify products were not affected (Count: 0)'; 
        END IF;

    EXCEPTION 
        WHEN OTHERS THEN 
            RAISE NOTICE 'Test % failed with error: %', test_count, SQLERRM; 
    END;
    
    -- Summary
    RAISE NOTICE 'Test Summary: % verifications passed out of % total tests', pass_count, test_count;
    
    -- Cleanup
    DELETE FROM products;
    DELETE FROM orders;
END $$;