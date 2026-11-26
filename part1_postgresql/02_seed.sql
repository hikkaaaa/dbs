-- Fictional seed data for CSCI 341 Assignment 3. Re-running restores the seed.
BEGIN;
SET LOCAL TIME ZONE 'UTC';

TRUNCATE TABLE review, paper_version, paper_author, paper_keyword, paper,
conference_session, track, conference_reviewer, conference_host, conference,
reviewer_expertise, reviewer, author_research_area, author, app_user RESTART IDENTITY;

INSERT INTO app_user (user_id, given_name, surname, email, affiliation, country, phone_number) VALUES
    (1, 'Arman', 'Armanov', 'arman.armanov@example.com', 'Steppe University', 'Kazakhstan', '+77010000001'),
    (2, 'Amina', 'Aminova', 'amina.aminova@example.com', 'Caspian Institute', 'Kazakhstan', '+77010000002'),
    (3, 'Daniyar', 'Saparov', 'daniyar.saparov@example.com', 'Steppe University', 'Kazakhstan', '+77010000003'),
    (4, 'Aliya', 'Karimova', 'aliya.karimova@example.com', 'Altai University', 'Kazakhstan', '+77010000004'),
    (5, 'Timur', 'Bekov', 'timur.bekov@example.com', 'Caspian Institute', 'Kazakhstan', '+77010000005'),
    (6, 'Dana', 'Suleimenova', 'dana.suleimenova@example.com', 'North Research Institute', 'Kazakhstan', '+77010000006'),
    (7, 'Nurlan', 'Omarov', 'nurlan.omarov@example.com', 'Altai University', 'Kazakhstan', '+77010000007'),
    (8, 'Sara', 'Kim', 'sara.kim@example.com', 'River University', 'South Korea', '+821000000008'),
    (9, 'Madina', 'Iskakova', 'madina.iskakova@example.com', 'Steppe University', 'Kazakhstan', '+77010000009'),
    (10, 'Bek', 'Asanov', 'bek.asanov@example.com', 'Caspian Institute', 'Kazakhstan', '+77010000010'),
    (11, 'Leila', 'Chen', 'leila.chen@example.com', 'River University', 'Singapore', '+6510000011'),
    (12, 'Ruslan', 'Nuriev', 'ruslan.nuriev@example.com', 'North Research Institute', 'Kazakhstan', '+77010000012');

INSERT INTO author (author_id, orcid) VALUES
    (1, NULL),
    (2, NULL),
    (3, NULL),
    (4, NULL),
    (5, NULL),
    (9, NULL),
    (10, NULL),
    (11, NULL);

INSERT INTO author_research_area (author_id, area_label) VALUES
    (1, 'Databases'),
    (1, 'Machine Learning'),
    (2, 'Databases'),
    (3, 'Distributed Systems'),
    (4, 'Machine Learning'),
    (5, 'Databases'),
    (9, 'Machine Learning'),
    (10, 'Distributed Systems'),
    (11, 'Information Retrieval');

INSERT INTO reviewer (reviewer_id, years_experience) VALUES
    (1, 4),
    (4, 5),
    (5, 2),
    (6, 8),
    (7, 6),
    (8, 3),
    (11, 1),
    (12, 0);

INSERT INTO reviewer_expertise (reviewer_id, area_label) VALUES
    (1, 'Databases'),
    (1, 'Machine Learning'),
    (4, 'Machine Learning'),
    (5, 'Databases'),
    (6, 'Databases'),
    (6, 'Distributed Systems'),
    (7, 'Databases'),
    (7, 'Machine Learning'),
    (8, 'Databases'),
    (11, 'Information Retrieval'),
    (12, 'Distributed Systems');

INSERT INTO conference (conference_id, name, acronym, description, city, country, start_date, end_date, submission_deadline, review_deadline) VALUES
    (1, 'Steppe Database Conference 2026', 'DBCON26', 'Database research and applications.', 'Astana', 'Kazakhstan', '2026-12-10', '2026-12-11', '2026-11-01', '2026-11-20'),
    (2, 'Applied Intelligence Conference 2026', 'AICON26', 'Machine learning and intelligent systems.', 'Almaty', 'Kazakhstan', '2026-12-15', '2026-12-16', '2026-11-01', '2026-11-22'),
    (3, 'Future Computing Forum 2027', 'FCF27', 'A future edition with no submissions yet.', 'Astana', 'Kazakhstan', '2027-01-20', '2027-01-21', '2026-12-20', '2027-01-10');

INSERT INTO conference_host (conference_id, host_name) VALUES
    (1, 'Steppe University'),
    (1, 'North Research Institute'),
    (2, 'Altai University'),
    (3, 'Caspian Institute');

INSERT INTO conference_reviewer (conference_id, reviewer_id) VALUES
    (1, 1),
    (1, 4),
    (1, 5),
    (1, 6),
    (1, 7),
    (1, 8),
    (1, 11),
    (2, 1),
    (2, 4),
    (2, 5),
    (2, 6),
    (2, 7),
    (2, 8),
    (2, 11),
    (3, 8),
    (3, 12);

INSERT INTO track (track_id, conference_id, name, description, research_area, coordinator_id) VALUES
    (1, 1, 'Data Management', 'Storage and query processing.', 'Databases', 6),
    (2, 1, 'Intelligent Data', 'Learning over structured data.', 'Machine Learning', 7),
    (3, 1, 'Emerging Databases', 'An intentionally empty track.', 'Databases', 8),
    (4, 2, 'Applied Learning', 'Practical learning methods.', 'Machine Learning', 4),
    (5, 2, 'Reliable Systems', 'Dependable intelligent services.', 'Distributed Systems', 5),
    (6, 3, 'Future Computing', 'Track in a conference with no papers.', 'Distributed Systems', 12);

INSERT INTO conference_session (session_id, conference_id, title, session_date, start_time, end_time, room_label, chair_id) VALUES
    (1, 1, 'Database Research', '2026-12-10', '09:00', '10:30', 'A101', 6),
    (2, 1, 'Emerging Topics', '2026-12-10', '11:00', '12:00', 'A102', 7),
    (3, 2, 'Learning Applications', '2026-12-15', '09:00', '10:30', 'B201', 4),
    (4, 2, 'Systems Posters', '2026-12-15', '11:00', '12:00', 'B202', 5),
    (5, 3, 'Future Directions', '2027-01-20', '09:00', '10:00', 'C101', 12);

INSERT INTO paper (paper_id, track_id, title, abstract, submission_date, status, session_id) VALUES
    (1, 1, 'Learning to Optimize Queries', 'Machine Learning improves query plan selection.', '2026-10-25', 'accepted', 1),
    (2, 2, 'Responsible Data Pipelines', 'A framework for reproducible data processing.', '2026-10-25', 'accepted', NULL),
    (3, 1, 'Adaptive Database Indexing', 'An adaptive indexing method for changing workloads.', '2026-10-25', 'under review', NULL),
    (4, 2, 'Graph Features for Classification', 'We study machine learning for graph classification.', '2026-10-25', 'submitted', NULL),
    (5, 1, 'Compact Transaction Logs', 'A compact log representation for transactions.', '2026-10-25', 'rejected', NULL),
    (6, 2, 'Withdrawn Learning Study', 'A withdrawn evaluation of learning methods.', '2026-10-25', 'withdrawn', NULL),
    (7, 4, 'Clinical Prediction Models', 'MACHINE LEARNING supports interpretable prediction.', '2026-10-25', 'accepted', 3),
    (8, 4, 'Small Sample Recognition', 'Recognition under limited training data.', '2026-10-25', 'rejected', NULL),
    (9, 5, 'Resilient Model Serving', 'A fault tolerant model serving architecture.', '2026-10-25', 'under review', NULL),
    (10, 5, 'Auditing Distributed Services', 'A proposed audit trail for distributed services.', '2026-10-25', 'submitted', NULL),
    (11, 1, 'Withdrawn Storage Benchmark', 'A withdrawn benchmark of storage engines.', '2026-10-25', 'withdrawn', NULL),
    (12, 5, 'Reliable Feature Stores', 'Reliable feature storage for production services.', '2026-10-25', 'accepted', NULL);

INSERT INTO paper_keyword (paper_id, keyword) VALUES
    (1, 'research'),
    (1, 'databases'),
    (2, 'research'),
    (2, 'computing'),
    (3, 'research'),
    (3, 'databases'),
    (4, 'research'),
    (4, 'computing'),
    (5, 'research'),
    (5, 'databases'),
    (6, 'research'),
    (6, 'computing'),
    (7, 'research'),
    (7, 'computing'),
    (8, 'research'),
    (8, 'computing'),
    (9, 'research'),
    (9, 'computing'),
    (10, 'research'),
    (10, 'computing'),
    (11, 'research'),
    (11, 'databases'),
    (12, 'research'),
    (12, 'computing');

INSERT INTO paper_author (paper_id, author_id, author_position, is_corresponding) VALUES
    (1, 1, 1, TRUE),
    (1, 3, 2, FALSE),
    (2, 4, 1, TRUE),
    (2, 9, 2, FALSE),
    (3, 2, 1, TRUE),
    (3, 3, 2, FALSE),
    (4, 9, 1, TRUE),
    (4, 10, 2, FALSE),
    (5, 5, 1, TRUE),
    (5, 1, 2, FALSE),
    (6, 2, 1, TRUE),
    (6, 10, 2, FALSE),
    (7, 3, 1, TRUE),
    (7, 11, 2, FALSE),
    (8, 9, 1, TRUE),
    (9, 10, 1, TRUE),
    (10, 11, 1, TRUE),
    (11, 2, 1, TRUE),
    (11, 4, 2, FALSE),
    (12, 5, 1, TRUE),
    (12, 3, 2, FALSE);

INSERT INTO paper_version (paper_id, version_no, file_location, uploaded_at, change_note) VALUES
    (1, 1, 'papers/1/v1.pdf', '2026-10-25 09:00:00+00', NULL),
    (2, 1, 'papers/2/v1.pdf', '2026-10-25 09:00:00+00', NULL),
    (3, 1, 'papers/3/v1.pdf', '2026-10-25 09:00:00+00', NULL),
    (4, 1, 'papers/4/v1.pdf', '2026-10-25 09:00:00+00', NULL),
    (5, 1, 'papers/5/v1.pdf', '2026-10-25 09:00:00+00', NULL),
    (6, 1, 'papers/6/v1.pdf', '2026-10-25 09:00:00+00', NULL),
    (7, 1, 'papers/7/v1.pdf', '2026-10-25 09:00:00+00', NULL),
    (8, 1, 'papers/8/v1.pdf', '2026-10-25 09:00:00+00', NULL),
    (9, 1, 'papers/9/v1.pdf', '2026-10-25 09:00:00+00', NULL),
    (10, 1, 'papers/10/v1.pdf', '2026-10-25 09:00:00+00', NULL),
    (11, 1, 'papers/11/v1.pdf', '2026-10-25 09:00:00+00', NULL),
    (12, 1, 'papers/12/v1.pdf', '2026-10-25 09:00:00+00', NULL),
    (1, 2, 'papers/1/v2.pdf', '2026-10-27 09:00:00+00', 'Revised experiments.'),
    (1, 4, 'papers/1/v4.pdf', '2026-10-29 09:00:00+00', 'Clarified query plans; version 3 was not submitted.'),
    (3, 2, 'papers/3/v2.pdf', '2026-10-28 10:00:00+00', 'Added workload analysis.'),
    (7, 2, 'papers/7/v2.pdf', '2026-10-28 11:00:00+00', 'Improved explanation.');

INSERT INTO review (review_id, paper_id, reviewer_id, overall_score, recommendation, comments_for_authors, confidential_comments, review_submission_date) VALUES
    (1, 1, 6, 5, 'accept', 'Completed review 1: The contribution is useful; clarify the evaluation.', NULL, '2026-11-15'),
    (2, 1, 7, 4, 'accept', 'Completed review 2: The contribution is useful; clarify the evaluation.', 'Please discuss the evaluation in the committee meeting.', '2026-11-15'),
    (3, 1, 8, 3, 'accept', 'Completed review 3: The contribution is useful; clarify the evaluation.', NULL, '2026-11-15'),
    (4, 2, 6, 4, 'accept', 'Completed review 4: The contribution is useful; clarify the evaluation.', 'Please discuss the evaluation in the committee meeting.', '2026-11-15'),
    (5, 2, 1, 5, 'accept', 'Completed review 5: The contribution is useful; clarify the evaluation.', NULL, '2026-11-15'),
    (6, 3, 6, 3, 'accept', 'Completed review 6: The contribution is useful; clarify the evaluation.', 'Please discuss the evaluation in the committee meeting.', '2026-11-15'),
    (7, 3, 7, 2, 'reject', 'Completed review 7: The evaluation needs substantial improvement.', NULL, '2026-11-15'),
    (8, 5, 6, 2, 'reject', 'Completed review 8: The evaluation needs substantial improvement.', 'Please discuss the evaluation in the committee meeting.', '2026-11-15'),
    (9, 5, 8, 1, 'reject', 'Completed review 9: The evaluation needs substantial improvement.', NULL, '2026-11-15'),
    (10, 6, 7, 2, 'reject', 'Completed review 10: The evaluation needs substantial improvement.', 'Please discuss the evaluation in the committee meeting.', '2026-11-15'),
    (11, 7, 6, 5, 'accept', 'Completed review 11: The contribution is useful; clarify the evaluation.', NULL, '2026-11-15'),
    (12, 7, 1, 4, 'accept', 'Completed review 12: The contribution is useful; clarify the evaluation.', 'Please discuss the evaluation in the committee meeting.', '2026-11-15'),
    (13, 8, 7, 2, 'reject', 'Completed review 13: The evaluation needs substantial improvement.', NULL, '2026-11-15'),
    (14, 9, 8, 3, 'accept', 'Completed review 14: The contribution is useful; clarify the evaluation.', 'Please discuss the evaluation in the committee meeting.', '2026-11-15'),
    (15, 11, 5, 1, 'reject', 'Completed review 15: The evaluation needs substantial improvement.', NULL, '2026-11-15'),
    (16, 12, 4, 4, 'accept', 'Completed review 16: The contribution is useful; clarify the evaluation.', 'Please discuss the evaluation in the committee meeting.', '2026-11-15');

-- Explicit seed IDs do not advance identity sequences. Set their NEXT values.

SELECT setval(pg_get_serial_sequence('app_user', 'user_id'), (SELECT max(user_id) FROM app_user), TRUE);

SELECT setval(pg_get_serial_sequence('conference', 'conference_id'), (SELECT max(conference_id) FROM conference), TRUE);

SELECT setval(pg_get_serial_sequence('track', 'track_id'), (SELECT max(track_id) FROM track), TRUE);

SELECT setval(pg_get_serial_sequence('conference_session', 'session_id'), (SELECT max(session_id) FROM conference_session), TRUE);

SELECT setval(pg_get_serial_sequence('paper', 'paper_id'), (SELECT max(paper_id) FROM paper), TRUE);

SELECT setval(pg_get_serial_sequence('review', 'review_id'), (SELECT max(review_id) FROM review), TRUE);


COMMIT;
