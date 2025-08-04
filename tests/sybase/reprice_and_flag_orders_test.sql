-- Sybase Test Script for reprice_and_flag_orders

-- Test 1: Valid input test
DECLARE @updated_count_1 TEXT;
DECLARE @result_1 INT;
EXEC @result_1 = reprice_and_flag_orders @campaign_code = 'SUMMER2022', @updated_count = @updated_count_1 OUTPUT;
SELECT 'Test 1' as test_name, @result_1 as return_code, @updated_count_1 as updated_count;
SELECT 'Verify orders were updated with correct campaign code' as verification, COUNT(*) as count FROM orders WHERE campaign_code = 'SUMMER2022';
SELECT 'Verify products were repriced successfully' as verification, COUNT(*) as count FROM products WHERE price > 0;
-- Test 2: Boundary value test
DECLARE @updated_count_1 TEXT;
DECLARE @result_2 INT;
EXEC @result_2 = reprice_and_flag_orders @campaign_code = NULL, @updated_count = @updated_count_1 OUTPUT;
SELECT 'Test 2' as test_name, @result_2 as return_code, @updated_count_1 as updated_count;
SELECT 'Verify null handling in campaign code' as verification, COUNT(*) as count FROM orders WHERE campaign_code IS NULL OR campaign_code = 'pending';
SELECT 'Verify products were repriced successfully' as verification, COUNT(*) as count FROM products WHERE price > 0;
-- Test 3: Error condition test
DECLARE @updated_count_1 TEXT;
DECLARE @result_3 INT;
EXEC @result_3 = reprice_and_flag_orders @campaign_code = '-1', @updated_count = @updated_count_1 OUTPUT;
SELECT 'Test 3' as test_name, @result_3 as return_code, @updated_count_1 as updated_count;
SELECT 'Verify error handling for invalid campaign code' as verification, COUNT(*) as count FROM orders WHERE error_flag = true;
SELECT 'Verify products were not affected' as verification, COUNT(*) as count FROM products WHERE price > 0;

DELETE FROM products;
DELETE FROM orders;
