-- Constraint and cascade tests for the original seed dataset.
-- Expected failures are caught inside subtransactions. All changes are rolled back.
BEGIN;
DO $tests$
BEGIN
    BEGIN
        UPDATE app_user SET email='arman.armanov@example.com' WHERE user_id=2;
        RAISE EXCEPTION 'FAIL: database allowed duplicate email';
    EXCEPTION WHEN unique_violation THEN
        RAISE NOTICE 'PASS: rejected duplicate email';
    END;
    BEGIN
        UPDATE paper_author SET author_position=1 WHERE paper_id=1 AND author_id=3;
        RAISE EXCEPTION 'FAIL: database allowed duplicate author position';
    EXCEPTION WHEN unique_violation THEN
        RAISE NOTICE 'PASS: rejected duplicate author position';
    END;
    BEGIN
        UPDATE review SET reviewer_id=6 WHERE review_id=2;
        RAISE EXCEPTION 'FAIL: database allowed duplicate reviewer-paper pair';
    EXCEPTION WHEN unique_violation THEN
        RAISE NOTICE 'PASS: rejected duplicate reviewer-paper pair';
    END;
    BEGIN
        INSERT INTO paper_version SELECT * FROM paper_version WHERE paper_id=1 AND version_no=1;
        RAISE EXCEPTION 'FAIL: database allowed duplicate version';
    EXCEPTION WHEN unique_violation THEN
        RAISE NOTICE 'PASS: rejected duplicate version';
    END;
    BEGIN
        UPDATE paper SET status='pending' WHERE paper_id=1;
        RAISE EXCEPTION 'FAIL: database allowed invalid paper status';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'PASS: rejected invalid paper status';
    END;
    BEGIN
        UPDATE review SET overall_score=0 WHERE review_id=1;
        RAISE EXCEPTION 'FAIL: database allowed score below 1';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'PASS: rejected score below 1';
    END;
    BEGIN
        UPDATE review SET overall_score=6 WHERE review_id=1;
        RAISE EXCEPTION 'FAIL: database allowed score above 5';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'PASS: rejected score above 5';
    END;
    BEGIN
        UPDATE review SET recommendation='maybe' WHERE review_id=1;
        RAISE EXCEPTION 'FAIL: database allowed invalid recommendation';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'PASS: rejected invalid recommendation';
    END;
    BEGIN
        UPDATE paper_author SET author_position=0 WHERE paper_id=1 AND author_id=1;
        RAISE EXCEPTION 'FAIL: database allowed zero author position';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'PASS: rejected zero author position';
    END;
    BEGIN
        UPDATE paper_version SET version_no=0 WHERE paper_id=1 AND version_no=1;
        RAISE EXCEPTION 'FAIL: database allowed zero version number';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'PASS: rejected zero version number';
    END;
    BEGIN
        UPDATE reviewer SET years_experience=-1 WHERE reviewer_id=6;
        RAISE EXCEPTION 'FAIL: database allowed negative experience';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'PASS: rejected negative experience';
    END;
    BEGIN
        UPDATE conference SET end_date=start_date-1 WHERE conference_id=1;
        RAISE EXCEPTION 'FAIL: database allowed reversed conference dates';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'PASS: rejected reversed conference dates';
    END;
    BEGIN
        UPDATE conference_session SET end_time=start_time WHERE session_id=1;
        RAISE EXCEPTION 'FAIL: database allowed equal session times';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'PASS: rejected equal session times';
    END;
    BEGIN
        UPDATE conference_session SET end_time='08:00' WHERE session_id=1;
        RAISE EXCEPTION 'FAIL: database allowed reversed session times';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'PASS: rejected reversed session times';
    END;
    BEGIN
        UPDATE paper SET title=NULL WHERE paper_id=1;
        RAISE EXCEPTION 'FAIL: database allowed missing required title';
    EXCEPTION WHEN not_null_violation THEN
        RAISE NOTICE 'PASS: rejected missing required title';
    END;
    BEGIN
        UPDATE review SET overall_score=NULL WHERE review_id=1;
        RAISE EXCEPTION 'FAIL: database allowed incomplete review score';
    EXCEPTION WHEN not_null_violation THEN
        RAISE NOTICE 'PASS: rejected incomplete review score';
    END;
    BEGIN
        UPDATE review SET review_submission_date=NULL WHERE review_id=1;
        RAISE EXCEPTION 'FAIL: database allowed incomplete review date';
    EXCEPTION WHEN not_null_violation THEN
        RAISE NOTICE 'PASS: rejected incomplete review date';
    END;
    BEGIN
        UPDATE review SET comments_for_authors='   ' WHERE review_id=1;
        RAISE EXCEPTION 'FAIL: database allowed blank review comments';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'PASS: rejected blank review comments';
    END;
    BEGIN
        UPDATE paper SET track_id=99999 WHERE paper_id=1;
        RAISE EXCEPTION 'FAIL: database allowed missing parent track';
    EXCEPTION WHEN foreign_key_violation THEN
        RAISE NOTICE 'PASS: rejected missing parent track';
    END;
    BEGIN
        UPDATE paper_author SET is_corresponding=TRUE WHERE paper_id=1 AND author_id=3;
        RAISE EXCEPTION 'FAIL: database allowed second corresponding author';
    EXCEPTION WHEN unique_violation THEN
        RAISE NOTICE 'PASS: rejected second corresponding author';
    END;
    BEGIN
        UPDATE track SET coordinator_id=12 WHERE track_id=1;
        RAISE EXCEPTION 'FAIL: database allowed coordinator outside conference pool';
    EXCEPTION WHEN foreign_key_violation THEN
        RAISE NOTICE 'PASS: rejected coordinator outside conference pool';
    END;
    BEGIN
        UPDATE conference_session SET chair_id=12 WHERE session_id=1;
        RAISE EXCEPTION 'FAIL: database allowed chair outside conference pool';
    EXCEPTION WHEN foreign_key_violation THEN
        RAISE NOTICE 'PASS: rejected chair outside conference pool';
    END;
    BEGIN
        DELETE FROM author WHERE author_id=1;
        RAISE EXCEPTION 'FAIL: database allowed delete referenced author';
    EXCEPTION WHEN foreign_key_violation OR restrict_violation THEN
        RAISE NOTICE 'PASS: rejected delete referenced author';
    END;
    BEGIN
        DELETE FROM conference WHERE conference_id=1;
        RAISE EXCEPTION 'FAIL: database allowed delete populated conference';
    EXCEPTION WHEN foreign_key_violation OR restrict_violation THEN
        RAISE NOTICE 'PASS: rejected delete populated conference';
    END;
END;
$tests$;
SAVEPOINT cascade_test;
DELETE FROM paper WHERE paper_id=6;
DO $cascade$
BEGIN
    IF EXISTS (SELECT 1 FROM paper WHERE paper_id=6)
       OR EXISTS (SELECT 1 FROM paper_author WHERE paper_id=6)
       OR EXISTS (SELECT 1 FROM paper_keyword WHERE paper_id=6)
       OR EXISTS (SELECT 1 FROM paper_version WHERE paper_id=6)
       OR EXISTS (SELECT 1 FROM review WHERE paper_id=6)
       OR (SELECT count(*) FROM app_user) <> 12
       OR (SELECT count(*) FROM track) <> 6
       OR (SELECT count(*) FROM conference) <> 3
       OR (SELECT count(*) FROM paper) <> 11 THEN
        RAISE EXCEPTION 'FAIL: paper deletion cascade';
    END IF;
    RAISE NOTICE 'PASS: deleting a paper removes all four dependent record types and preserves parents';
END;
$cascade$;
ROLLBACK TO SAVEPOINT cascade_test;
RELEASE SAVEPOINT cascade_test;
SAVEPOINT session_test;
DELETE FROM conference_session WHERE session_id=1;
DO $session$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM paper WHERE paper_id=1 AND session_id IS NULL) THEN
        RAISE EXCEPTION 'FAIL: deleting session must unschedule and preserve paper';
    END IF;
    RAISE NOTICE 'PASS: deleting a session unschedules its paper';
END;
$session$;
ROLLBACK TO SAVEPOINT session_test;
RELEASE SAVEPOINT session_test;
ROLLBACK;
