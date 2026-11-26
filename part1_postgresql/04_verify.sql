-- Verification for the ORIGINAL seed dataset. Raises an exception on failure.
-- Does not modify application data. Run after 00_restore.sql or 02_seed.sql.
BEGIN;
DO $verify$
BEGIN
    IF ((SELECT count(*) = 12 FROM app_user)) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: app_user: exactly 12 seed rows';
    END IF;
    IF ((SELECT count(*) = 8 FROM author)) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: author: exactly 8 seed rows';
    END IF;
    IF ((SELECT count(*) = 9 FROM author_research_area)) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: author_research_area: exactly 9 seed rows';
    END IF;
    IF ((SELECT count(*) = 8 FROM reviewer)) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: reviewer: exactly 8 seed rows';
    END IF;
    IF ((SELECT count(*) = 11 FROM reviewer_expertise)) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: reviewer_expertise: exactly 11 seed rows';
    END IF;
    IF ((SELECT count(*) = 3 FROM conference)) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: conference: exactly 3 seed rows';
    END IF;
    IF ((SELECT count(*) = 4 FROM conference_host)) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: conference_host: exactly 4 seed rows';
    END IF;
    IF ((SELECT count(*) = 16 FROM conference_reviewer)) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: conference_reviewer: exactly 16 seed rows';
    END IF;
    IF ((SELECT count(*) = 6 FROM track)) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: track: exactly 6 seed rows';
    END IF;
    IF ((SELECT count(*) = 5 FROM conference_session)) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: conference_session: exactly 5 seed rows';
    END IF;
    IF ((SELECT count(*) = 12 FROM paper)) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: paper: exactly 12 seed rows';
    END IF;
    IF ((SELECT count(*) = 24 FROM paper_keyword)) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: paper_keyword: exactly 24 seed rows';
    END IF;
    IF ((SELECT count(*) = 21 FROM paper_author)) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: paper_author: exactly 21 seed rows';
    END IF;
    IF ((SELECT count(*) = 16 FROM paper_version)) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: paper_version: exactly 16 seed rows';
    END IF;
    IF ((SELECT count(*) = 16 FROM review)) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: review: exactly 16 seed rows';
    END IF;
    IF (NOT EXISTS (SELECT 1 FROM app_user u WHERE NOT EXISTS (SELECT 1 FROM author a WHERE a.author_id=u.user_id) AND NOT EXISTS (SELECT 1 FROM reviewer r WHERE r.reviewer_id=u.user_id))) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: every user has an author or reviewer role';
    END IF;
    IF (EXISTS (SELECT 1 FROM author a WHERE NOT EXISTS (SELECT 1 FROM reviewer r WHERE r.reviewer_id=a.author_id)) AND EXISTS (SELECT 1 FROM reviewer r WHERE NOT EXISTS (SELECT 1 FROM author a WHERE a.author_id=r.reviewer_id)) AND EXISTS (SELECT 1 FROM author a JOIN reviewer r ON a.author_id=r.reviewer_id)) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: author-only, reviewer-only, and both roles exist';
    END IF;
    IF (NOT EXISTS (SELECT 1 FROM author p WHERE NOT EXISTS (SELECT 1 FROM author_research_area c WHERE c.author_id=p.author_id))) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: every author has required author_research_area rows';
    END IF;
    IF (NOT EXISTS (SELECT 1 FROM reviewer p WHERE NOT EXISTS (SELECT 1 FROM reviewer_expertise c WHERE c.reviewer_id=p.reviewer_id))) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: every reviewer has required reviewer_expertise rows';
    END IF;
    IF (NOT EXISTS (SELECT 1 FROM conference p WHERE NOT EXISTS (SELECT 1 FROM conference_host c WHERE c.conference_id=p.conference_id))) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: every conference has required conference_host rows';
    END IF;
    IF (NOT EXISTS (SELECT 1 FROM conference p WHERE NOT EXISTS (SELECT 1 FROM conference_reviewer c WHERE c.conference_id=p.conference_id))) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: every conference has required conference_reviewer rows';
    END IF;
    IF (NOT EXISTS (SELECT 1 FROM conference p WHERE NOT EXISTS (SELECT 1 FROM track c WHERE c.conference_id=p.conference_id))) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: every conference has required track rows';
    END IF;
    IF (NOT EXISTS (SELECT 1 FROM paper p WHERE NOT EXISTS (SELECT 1 FROM paper_keyword c WHERE c.paper_id=p.paper_id))) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: every paper has required paper_keyword rows';
    END IF;
    IF (NOT EXISTS (SELECT 1 FROM paper p WHERE NOT EXISTS (SELECT 1 FROM paper_author c WHERE c.paper_id=p.paper_id))) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: every paper has required paper_author rows';
    END IF;
    IF (NOT EXISTS (SELECT 1 FROM paper p WHERE NOT EXISTS (SELECT 1 FROM paper_version c WHERE c.paper_id=p.paper_id))) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: every paper has required paper_version rows';
    END IF;
    IF (NOT EXISTS (SELECT p.paper_id FROM paper p LEFT JOIN paper_author pa ON pa.paper_id=p.paper_id GROUP BY p.paper_id HAVING count(*) FILTER (WHERE pa.is_corresponding) <> 1)) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: exactly one corresponding author per paper';
    END IF;
    IF (NOT EXISTS (SELECT 1 FROM review r JOIN paper_author pa ON pa.paper_id=r.paper_id AND pa.author_id=r.reviewer_id)) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: no self-reviews';
    END IF;
    IF (NOT EXISTS (SELECT 1 FROM paper p JOIN track t ON t.track_id=p.track_id JOIN conference_session s ON s.session_id=p.session_id WHERE p.status <> 'accepted' OR t.conference_id<>s.conference_id)) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: all session assignments valid';
    END IF;
    IF (NOT EXISTS (SELECT 1 FROM track t WHERE NOT EXISTS (SELECT 1 FROM conference_reviewer cr WHERE cr.conference_id=t.conference_id AND cr.reviewer_id=t.coordinator_id)) AND NOT EXISTS (SELECT 1 FROM conference_session s WHERE NOT EXISTS (SELECT 1 FROM conference_reviewer cr WHERE cr.conference_id=s.conference_id AND cr.reviewer_id=s.chair_id))) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: chairs and coordinators in conference pools';
    END IF;
    IF ((SELECT count(DISTINCT status)=5 FROM paper)) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: all five paper statuses represented';
    END IF;
    IF ((SELECT array_agg(version_no ORDER BY version_no)=ARRAY[1,2,4] FROM paper_version WHERE paper_id=1)) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: paper 1 has multiple versions with a gap and current version 4';
    END IF;
    IF ((SELECT count(*)>1 FROM paper_author WHERE paper_id=1)) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: paper 1 has multiple authors';
    END IF;
    IF ((SELECT count(*)=0 FROM paper WHERE track_id IN (3,6))) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: empty tracks 3 and 6';
    END IF;
    IF ((SELECT count(*)=0 FROM paper p JOIN track t USING(track_id) WHERE t.conference_id=3)) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: conference 3 has no papers';
    END IF;
    IF ((SELECT count(*)=0 FROM review WHERE reviewer_id IN (11,12))) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: reviewers 11 and 12 have no reviews';
    END IF;
    IF (EXISTS (SELECT 1 FROM paper WHERE status='accepted' AND session_id IS NOT NULL) AND EXISTS (SELECT 1 FROM paper WHERE status='accepted' AND session_id IS NULL)) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: accepted papers with and without sessions';
    END IF;
    IF ((SELECT count(*)=1 FROM app_user WHERE email='arman.armanov@example.com' AND phone_number='+77010000001')) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: Arman identified uniquely with old phone';
    END IF;
    IF ((SELECT array_agg(p.paper_id ORDER BY p.paper_id)=ARRAY[6,11] FROM paper p JOIN paper_author pa USING(paper_id) JOIN app_user u ON u.user_id=pa.author_id WHERE p.status='withdrawn' AND pa.is_corresponding AND u.email='amina.aminova@example.com')) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: Amina corresponding author on withdrawn papers 6 and 11';
    END IF;
    IF ((SELECT array_agg(s.session_id ORDER BY s.session_id)=ARRAY[2,5] FROM conference_session s JOIN conference c USING(conference_id) WHERE c.city='Astana' AND NOT EXISTS (SELECT 1 FROM paper p WHERE p.session_id=s.session_id))) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: empty Astana sessions are 2 and 5';
    END IF;
    IF (EXISTS (SELECT 1 FROM conference WHERE city='Astana') AND EXISTS (SELECT 1 FROM conference WHERE city<>'Astana')) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: both conditional deadline update branches available';
    END IF;
    IF ((SELECT array_agg(paper_id ORDER BY paper_id)=ARRAY[1,4,7] FROM paper WHERE abstract ILIKE '%machine learning%')) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: case-insensitive phrase matches papers 1, 4, 7';
    END IF;
    IF ((SELECT array_agg(r.reviewer_id ORDER BY r.reviewer_id)=ARRAY[1,6,7,8] FROM reviewer r JOIN conference_reviewer cr USING(reviewer_id) WHERE cr.conference_id=1 AND r.years_experience>=3 AND EXISTS (SELECT 1 FROM reviewer_expertise e WHERE e.reviewer_id=r.reviewer_id AND e.area_label='Databases'))) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: Databases and 3 years in conference 1 matches 1,6,7,8';
    END IF;
    IF ((WITH counts AS (SELECT r.reviewer_id,count(v.review_id) AS n FROM reviewer r LEFT JOIN review v USING(reviewer_id) GROUP BY r.reviewer_id) SELECT array_agg(reviewer_id ORDER BY reviewer_id)=ARRAY[6,7,8] AND (SELECT avg(n)=2 FROM counts) FROM counts WHERE n>(SELECT avg(n) FROM counts))) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: varied review counts, average 2.0, reviewers 6,7,8 above average';
    END IF;
    IF ((SELECT array_agg(paper_id ORDER BY paper_id)=ARRAY[1,7] FROM accepted_paper_schedule)) IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'FAIL: schedule view contains exactly papers 1 and 7';
    END IF;
    RAISE NOTICE 'PASS: all 44 seed and business-rule assertions.';
END;
$verify$;
COMMIT;

-- Required row counts for every table:
SELECT 'app_user' AS table_name, count(*) AS row_count FROM app_user
UNION ALL
SELECT 'author' AS table_name, count(*) AS row_count FROM author
UNION ALL
SELECT 'author_research_area' AS table_name, count(*) AS row_count FROM author_research_area
UNION ALL
SELECT 'reviewer' AS table_name, count(*) AS row_count FROM reviewer
UNION ALL
SELECT 'reviewer_expertise' AS table_name, count(*) AS row_count FROM reviewer_expertise
UNION ALL
SELECT 'conference' AS table_name, count(*) AS row_count FROM conference
UNION ALL
SELECT 'conference_host' AS table_name, count(*) AS row_count FROM conference_host
UNION ALL
SELECT 'conference_reviewer' AS table_name, count(*) AS row_count FROM conference_reviewer
UNION ALL
SELECT 'track' AS table_name, count(*) AS row_count FROM track
UNION ALL
SELECT 'conference_session' AS table_name, count(*) AS row_count FROM conference_session
UNION ALL
SELECT 'paper' AS table_name, count(*) AS row_count FROM paper
UNION ALL
SELECT 'paper_keyword' AS table_name, count(*) AS row_count FROM paper_keyword
UNION ALL
SELECT 'paper_author' AS table_name, count(*) AS row_count FROM paper_author
UNION ALL
SELECT 'paper_version' AS table_name, count(*) AS row_count FROM paper_version
UNION ALL
SELECT 'review' AS table_name, count(*) AS row_count FROM review
ORDER BY table_name;

-- A view has no intrinsic output order; always order the demonstration query.
SELECT * FROM accepted_paper_schedule
ORDER BY conference_id, session_date, start_time, session_id, paper_id;
