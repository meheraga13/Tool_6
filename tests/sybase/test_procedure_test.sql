-- Sybase Test Script for test_procedure

-- Test 1: Valid input test
DECLARE @result_msg_1 TEXT;
DECLARE @result_1 INT;
EXEC @result_1 = test_procedure @input_id = '123', @result_msg = @result_msg_1 OUTPUT;
SELECT 'Test 1' as test_name, @result_1 as return_code, @result_msg_1 as result_msg;
SELECT 'Verify record was processed correctly' as verification, COUNT(*) as count FROM users WHERE id = 123 AND status = 'active';
-- Test 2: Boundary value test
DECLARE @result_msg_1 TEXT;
DECLARE @result_2 INT;
EXEC @result_2 = test_procedure @input_id = NULL, @result_msg = @result_msg_1 OUTPUT;
SELECT 'Test 2' as test_name, @result_2 as return_code, @result_msg_1 as result_msg;
SELECT 'Verify null handling' as verification, COUNT(*) as count FROM users WHERE status IS NULL OR status = 'pending';
-- Test 3: Error condition test
DECLARE @result_msg_1 TEXT;
DECLARE @result_3 INT;
EXEC @result_3 = test_procedure @input_id = '-1', @result_msg = @result_msg_1 OUTPUT;
SELECT 'Test 3' as test_name, @result_3 as return_code, @result_msg_1 as result_msg;
SELECT 'Verify error handling' as verification, COUNT(*) as count FROM users WHERE error_flag = true;

DELETE FROM users;
