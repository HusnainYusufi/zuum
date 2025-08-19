

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


CREATE SCHEMA IF NOT EXISTS "public";


ALTER SCHEMA "public" OWNER TO "pg_database_owner";


COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE OR REPLACE FUNCTION "public"."get_check_ins_paginated"("page_num" integer DEFAULT 1, "page_size" integer DEFAULT 10, "filter_issue_flagged" boolean DEFAULT NULL::boolean, "filter_tags" "text" DEFAULT NULL::"text", "filter_call_status" "text" DEFAULT NULL::"text") RETURNS TABLE("id" integer, "load_id" "text", "ai_response_summary" "text", "ai_timestamp" timestamp with time zone, "call_status" "text", "user_picked_up" boolean, "form_type" "text", "forms" "jsonb", "created_at" timestamp with time zone, "updated_at" timestamp with time zone, "total_count" bigint)
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    offset_count INTEGER;
    total_records BIGINT;
BEGIN
    -- Calculate offset
    offset_count := (page_num - 1) * page_size;
    
    -- Get total count first
    SELECT COUNT(*)
    INTO total_records
    FROM check_ins ci
    WHERE 
        (filter_issue_flagged IS NULL OR ci.issue_flagged = filter_issue_flagged)
        AND (filter_tags IS NULL OR ci.tags::TEXT ILIKE '%' || filter_tags || '%')
        AND (filter_call_status IS NULL OR ci.call_status = filter_call_status);
    
    -- Return paginated results with total count
    RETURN QUERY
    SELECT 
        ci.id,
        ci.load_id,
        ci.ai_response_summary,
        ci.ai_timestamp,
        ci.call_status,
        ci.user_picked_up,
        ci."Form_type" as form_type,  -- Use correct column name with quotes
        ci.forms,
        ci.created_at,
        ci.updated_at,
        total_records as total_count
    FROM check_ins ci
    WHERE 
        (filter_issue_flagged IS NULL OR ci.issue_flagged = filter_issue_flagged)
        AND (filter_tags IS NULL OR ci.tags::TEXT ILIKE '%' || filter_tags || '%')
        AND (filter_call_status IS NULL OR ci.call_status = filter_call_status)
    ORDER BY ci.ai_timestamp DESC
    LIMIT page_size
    OFFSET offset_count;
END;
$$;


ALTER FUNCTION "public"."get_check_ins_paginated"("page_num" integer, "page_size" integer, "filter_issue_flagged" boolean, "filter_tags" "text", "filter_call_status" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_check_ins_paginated_enhanced"("page_num" integer DEFAULT 1, "page_size" integer DEFAULT 10, "filter_issue_flagged" boolean DEFAULT NULL::boolean, "filter_tags" "text" DEFAULT NULL::"text", "filter_call_status" "text" DEFAULT NULL::"text", "search_name" "text" DEFAULT NULL::"text", "search_phone" "text" DEFAULT NULL::"text", "search_load_id" "text" DEFAULT NULL::"text", "start_date" timestamp with time zone DEFAULT NULL::timestamp with time zone, "end_date" timestamp with time zone DEFAULT NULL::timestamp with time zone) RETURNS TABLE("id" integer, "load_id" "text", "ai_response_summary" "text", "ai_timestamp" timestamp with time zone, "call_status" "text", "user_picked_up" boolean, "form_type" "text", "forms" "jsonb", "created_at" timestamp with time zone, "updated_at" timestamp with time zone, "tags" "jsonb", "total_count" bigint)
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    offset_count INTEGER;
    total_records BIGINT;
    normalized_phone TEXT;
BEGIN
    offset_count := (page_num - 1) * page_size;
    
    -- Normalize phone number for search - keep original for partial matching
    IF search_phone IS NOT NULL THEN
        -- Remove all non-digit characters from search input
        normalized_phone := regexp_replace(search_phone, '[^0-9]', '', 'g');
    END IF;
    
    SELECT COUNT(*)
    INTO total_records
    FROM check_ins ci
    WHERE 
        (filter_issue_flagged IS NULL OR ci.issue_flagged = filter_issue_flagged)
        AND (filter_tags IS NULL OR 
            (ci.tags IS NOT NULL AND 
             ci.tags::TEXT ILIKE '%' || filter_tags || '%'))
        AND (filter_call_status IS NULL OR ci.call_status = filter_call_status)
        AND (search_name IS NULL OR 
            (ci.forms->>'pickup_trucker_name' ILIKE '%' || search_name || '%' OR
             ci.forms->>'pc_trucker_name' ILIKE '%' || search_name || '%' OR
             ci.forms->>'it_trucker_name' ILIKE '%' || search_name || '%' OR
             ci.forms->>'ad_trucker_name' ILIKE '%' || search_name || '%' OR
             ci.forms->>'del_trucker_name' ILIKE '%' || search_name || '%' OR
             ci.forms->>'pod_trucker_name' ILIKE '%' || search_name || '%'))
        AND (search_phone IS NULL OR 
            (regexp_replace(ci.forms->>'pickup_contact_phone', '[^0-9]', '', 'g') ILIKE '%' || normalized_phone || '%' OR
             regexp_replace(ci.forms->>'pc_contact_phone', '[^0-9]', '', 'g') ILIKE '%' || normalized_phone || '%' OR
             regexp_replace(ci.forms->>'it_contact_phone', '[^0-9]', '', 'g') ILIKE '%' || normalized_phone || '%' OR
             regexp_replace(ci.forms->>'ad_contact_phone', '[^0-9]', '', 'g') ILIKE '%' || normalized_phone || '%' OR
             regexp_replace(ci.forms->>'del_contact_phone', '[^0-9]', '', 'g') ILIKE '%' || normalized_phone || '%' OR
             regexp_replace(ci.forms->>'pod_contact_phone', '[^0-9]', '', 'g') ILIKE '%' || normalized_phone || '%'))
        AND (search_load_id IS NULL OR 
            (ci.load_id ILIKE '%' || search_load_id || '%' OR
             ci.forms->>'pickup_load_id' ILIKE '%' || search_load_id || '%' OR
             ci.forms->>'pc_load_id' ILIKE '%' || search_load_id || '%' OR
             ci.forms->>'it_load_id' ILIKE '%' || search_load_id || '%' OR
             ci.forms->>'ad_load_id' ILIKE '%' || search_load_id || '%' OR
             ci.forms->>'del_load_id' ILIKE '%' || search_load_id || '%' OR
             ci.forms->>'pod_load_id' ILIKE '%' || search_load_id || '%'))
        AND (start_date IS NULL OR ci.ai_timestamp >= start_date)
        AND (end_date IS NULL OR ci.ai_timestamp <= end_date);
    
    RETURN QUERY
    SELECT 
        ci.id,
        ci.load_id,
        ci.ai_response_summary,
        ci.ai_timestamp,
        ci.call_status,
        ci.user_picked_up,
        ci."Form_type" as form_type,
        ci.forms,
        ci.created_at,
        ci.updated_at,
        ci.tags,
        total_records as total_count
    FROM check_ins ci
    WHERE 
        (filter_issue_flagged IS NULL OR ci.issue_flagged = filter_issue_flagged)
        AND (filter_tags IS NULL OR 
            (ci.tags IS NOT NULL AND 
             ci.tags::TEXT ILIKE '%' || filter_tags || '%'))
        AND (filter_call_status IS NULL OR ci.call_status = filter_call_status)
        AND (search_name IS NULL OR 
            (ci.forms->>'pickup_trucker_name' ILIKE '%' || search_name || '%' OR
             ci.forms->>'pc_trucker_name' ILIKE '%' || search_name || '%' OR
             ci.forms->>'it_trucker_name' ILIKE '%' || search_name || '%' OR
             ci.forms->>'ad_trucker_name' ILIKE '%' || search_name || '%' OR
             ci.forms->>'del_trucker_name' ILIKE '%' || search_name || '%' OR
             ci.forms->>'pod_trucker_name' ILIKE '%' || search_name || '%'))
        AND (search_phone IS NULL OR 
            (regexp_replace(ci.forms->>'pickup_contact_phone', '[^0-9]', '', 'g') ILIKE '%' || normalized_phone || '%' OR
             regexp_replace(ci.forms->>'pc_contact_phone', '[^0-9]', '', 'g') ILIKE '%' || normalized_phone || '%' OR
             regexp_replace(ci.forms->>'it_contact_phone', '[^0-9]', '', 'g') ILIKE '%' || normalized_phone || '%' OR
             regexp_replace(ci.forms->>'ad_contact_phone', '[^0-9]', '', 'g') ILIKE '%' || normalized_phone || '%' OR
             regexp_replace(ci.forms->>'del_contact_phone', '[^0-9]', '', 'g') ILIKE '%' || normalized_phone || '%' OR
             regexp_replace(ci.forms->>'pod_contact_phone', '[^0-9]', '', 'g') ILIKE '%' || normalized_phone || '%'))
        AND (search_load_id IS NULL OR 
            (ci.load_id ILIKE '%' || search_load_id || '%' OR
             ci.forms->>'pickup_load_id' ILIKE '%' || search_load_id || '%' OR
             ci.forms->>'pc_load_id' ILIKE '%' || search_load_id || '%' OR
             ci.forms->>'it_load_id' ILIKE '%' || search_load_id || '%' OR
             ci.forms->>'ad_load_id' ILIKE '%' || search_load_id || '%' OR
             ci.forms->>'del_load_id' ILIKE '%' || search_load_id || '%' OR
             ci.forms->>'pod_load_id' ILIKE '%' || search_load_id || '%'))
        AND (start_date IS NULL OR ci.ai_timestamp >= start_date)
        AND (end_date IS NULL OR ci.ai_timestamp <= end_date)
    ORDER BY ci.ai_timestamp DESC
    LIMIT page_size
    OFFSET offset_count;
END;
$$;


ALTER FUNCTION "public"."get_check_ins_paginated_enhanced"("page_num" integer, "page_size" integer, "filter_issue_flagged" boolean, "filter_tags" "text", "filter_call_status" "text", "search_name" "text", "search_phone" "text", "search_load_id" "text", "start_date" timestamp with time zone, "end_date" timestamp with time zone) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_check_ins_paginated_with_tags"("page_num" integer DEFAULT 1, "page_size" integer DEFAULT 10, "filter_issue_flagged" boolean DEFAULT NULL::boolean, "filter_tags" "text" DEFAULT NULL::"text", "filter_call_status" "text" DEFAULT NULL::"text") RETURNS TABLE("id" integer, "load_id" "text", "ai_response_summary" "text", "ai_timestamp" timestamp with time zone, "call_status" "text", "user_picked_up" boolean, "form_type" "text", "forms" "jsonb", "created_at" timestamp with time zone, "updated_at" timestamp with time zone, "tags" "jsonb", "total_count" bigint)
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    offset_count INTEGER;
    total_records BIGINT;
BEGIN
    offset_count := (page_num - 1) * page_size;
    
    SELECT COUNT(*)
    INTO total_records
    FROM check_ins ci
    WHERE 
        (filter_issue_flagged IS NULL OR ci.issue_flagged = filter_issue_flagged)
        AND (filter_tags IS NULL OR ci.tags::TEXT ILIKE '%' || filter_tags || '%')
        AND (filter_call_status IS NULL OR ci.call_status = filter_call_status);
    
    RETURN QUERY
    SELECT 
        ci.id,
        ci.load_id,
        ci.ai_response_summary,
        ci.ai_timestamp,
        ci.call_status,
        ci.user_picked_up,
        ci."Form_type" as form_type,
        ci.forms,
        ci.created_at,
        ci.updated_at,
        ci.tags,
        total_records as total_count
    FROM check_ins ci
    WHERE 
        (filter_issue_flagged IS NULL OR ci.issue_flagged = filter_issue_flagged)
        AND (filter_tags IS NULL OR ci.tags::TEXT ILIKE '%' || filter_tags || '%')
        AND (filter_call_status IS NULL OR ci.call_status = filter_call_status)
    ORDER BY ci.ai_timestamp DESC
    LIMIT page_size
    OFFSET offset_count;
END;
$$;


ALTER FUNCTION "public"."get_check_ins_paginated_with_tags"("page_num" integer, "page_size" integer, "filter_issue_flagged" boolean, "filter_tags" "text", "filter_call_status" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_checkins_paginated"("page_num" integer DEFAULT 1, "per_page" integer DEFAULT 10, "issue_flagged_filter" boolean DEFAULT NULL::boolean, "call_status_filter" "text" DEFAULT NULL::"text", "tag_filter" "text" DEFAULT NULL::"text") RETURNS TABLE("id" integer, "load_id" "text", "ai_response_summary" "text", "ai_timestamp" timestamp with time zone, "tags" "jsonb", "issue_flagged" boolean, "exception_type" "text", "confidence_score" "text", "forms" "jsonb", "call_status" "text", "created_at" timestamp with time zone, "updated_at" timestamp with time zone, "total_count" bigint)
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    offset_val INTEGER;
    total_count_val BIGINT;
BEGIN
    offset_val := (page_num - 1) * per_page;
    
    -- Get total count for pagination
    SELECT COUNT(*) INTO total_count_val
    FROM check_ins ci
    WHERE (issue_flagged_filter IS NULL OR ci.Issue_Flagged = issue_flagged_filter)
      AND (call_status_filter IS NULL OR ci.call_status = call_status_filter)
      AND (tag_filter IS NULL OR ci.tags @> jsonb_build_array(tag_filter));
    
    -- Return paginated results
    RETURN QUERY
    SELECT 
        ci.id,
        ci.load_id,
        ci.AI_Response_Summary,
        ci.AI_Timestamp,
        ci.tags,
        ci.Issue_Flagged,
        ci.Exception_Type,
        ci.Confidence_score,
        ci.forms,
        ci.call_status,
        ci.created_at,
        ci.updated_at,
        total_count_val
    FROM check_ins ci
    WHERE (issue_flagged_filter IS NULL OR ci.Issue_Flagged = issue_flagged_filter)
      AND (call_status_filter IS NULL OR ci.call_status = call_status_filter)
      AND (tag_filter IS NULL OR ci.tags @> jsonb_build_array(tag_filter))
    ORDER BY ci.AI_Timestamp DESC
    LIMIT per_page
    OFFSET offset_val;
END;
$$;


ALTER FUNCTION "public"."get_checkins_paginated"("page_num" integer, "per_page" integer, "issue_flagged_filter" boolean, "call_status_filter" "text", "tag_filter" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_checkins_per_day_chart"() RETURNS TABLE("check_date" "date", "checkin_count" bigint, "issues_count" bigint, "transfers_count" bigint, "date_label" "text")
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    RETURN QUERY
    WITH date_series AS (
        SELECT generate_series(
            CURRENT_DATE - INTERVAL '29 days',
            CURRENT_DATE,
            INTERVAL '1 day'
        )::date as date
    ),
    daily_counts AS (
        SELECT 
            DATE(created_at) as check_date,
            COUNT(*) as total_checkins,
            COUNT(CASE WHEN issue_flagged = true THEN 1 END) as total_issues,
            COUNT(CASE WHEN call_status = 'transferred' THEN 1 END) as total_transfers
        FROM check_ins 
        WHERE DATE(created_at) >= CURRENT_DATE - INTERVAL '29 days'
        GROUP BY DATE(created_at)
    )
    SELECT 
        ds.date as check_date,
        COALESCE(dc.total_checkins, 0) as checkin_count,
        COALESCE(dc.total_issues, 0) as issues_count,
        COALESCE(dc.total_transfers, 0) as transfers_count,
        TO_CHAR(ds.date, 'MM/DD') as date_label
    FROM date_series ds
    LEFT JOIN daily_counts dc ON ds.date = dc.check_date
    ORDER BY ds.date;
END;
$$;


ALTER FUNCTION "public"."get_checkins_per_day_chart"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_dashboard_chart_data"() RETURNS "json"
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    result JSON;
BEGIN
    WITH daily_data AS (
        SELECT 
            DATE(ai_timestamp) as check_date,
            COUNT(*) as count,
            COUNT(*) FILTER (WHERE issue_flagged = TRUE) as issues,
            COUNT(*) FILTER (WHERE call_status = 'completed') as completed
        FROM check_ins 
        WHERE ai_timestamp >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY DATE(ai_timestamp)
        ORDER BY check_date
    ),
    date_series AS (
        SELECT generate_series(
            CURRENT_DATE - INTERVAL '30 days',
            CURRENT_DATE,
            INTERVAL '1 day'
        )::date as date
    ),
    complete_daily_data AS (
        SELECT 
            ds.date,
            COALESCE(dd.count, 0) as count,
            COALESCE(dd.issues, 0) as issues,
            COALESCE(dd.completed, 0) as completed
        FROM date_series ds
        LEFT JOIN daily_data dd ON ds.date = dd.check_date
    ),
    summary_stats AS (
        SELECT 
            COUNT(*) as total_count,
            COUNT(*) FILTER (WHERE issue_flagged = TRUE) as total_issues,
            COUNT(*) FILTER (WHERE call_status = 'completed') as total_completed
        FROM check_ins
    )
    SELECT json_build_object(
        'daily_checkins', json_agg(
            json_build_object(
                'date', to_char(date, 'MM/DD'),
                'count', count,
                'issues', issues,
                'completed', completed
            ) ORDER BY date
        ),
        'summary', json_build_object(
            'total_checkins', ss.total_count,
            'total_issues', ss.total_issues,
            'total_completed', ss.total_completed,
            'issue_rate', CASE 
                WHEN ss.total_count > 0 THEN ROUND((ss.total_issues::NUMERIC / ss.total_count) * 100, 2)
                ELSE 0 
            END,
            'completion_rate', CASE 
                WHEN ss.total_count > 0 THEN ROUND((ss.total_completed::NUMERIC / ss.total_count) * 100, 2)
                ELSE 0 
            END
        )
    ) INTO result
    FROM complete_daily_data, summary_stats ss;
    
    RETURN result;
END;
$$;


ALTER FUNCTION "public"."get_dashboard_chart_data"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_dashboard_statistics"() RETURNS TABLE("total_checkins" bigint, "total_issues" bigint, "pending_calls" bigint, "today_checkins" bigint, "avg_confidence_score" numeric)
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*) AS total_checkins,
        COUNT(*) FILTER (WHERE issue_flagged = TRUE) AS total_issues,
        COUNT(*) FILTER (WHERE call_status = 'pending') AS pending_calls,
        COUNT(*) FILTER (WHERE DATE(ai_timestamp) = CURRENT_DATE) AS today_checkins,
        COALESCE(AVG(confidence_score), 0) AS avg_confidence_score
    FROM check_ins;
END;
$$;


ALTER FUNCTION "public"."get_dashboard_statistics"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_dashboard_stats"() RETURNS TABLE("total_checkins" bigint, "total_issues" bigint, "call_transfers" bigint, "today_checkins" bigint, "avg_confidence" numeric)
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        (SELECT COUNT(*) FROM check_ins) as total_checkins,
        (SELECT COUNT(*) FROM check_ins WHERE issue_flagged = true) as total_issues,
        (SELECT COUNT(*) FROM check_ins WHERE call_status = 'transferred') as call_transfers,
        (SELECT COUNT(*) FROM check_ins WHERE DATE(created_at) = CURRENT_DATE) as today_checkins,
        (SELECT ROUND(AVG(confidence_score), 4) FROM check_ins WHERE confidence_score IS NOT NULL) as avg_confidence;
END;
$$;


ALTER FUNCTION "public"."get_dashboard_stats"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_feedback_with_images"("page_num" integer DEFAULT 1, "per_page" integer DEFAULT 10) RETURNS TABLE("id" integer, "feedback_type" "text", "user_name" "text", "user_email" "text", "description" "text", "created_at" timestamp with time zone, "updated_at" timestamp with time zone, "images" "jsonb", "total_count" bigint)
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    offset_val INTEGER;
    total_count_val BIGINT;
BEGIN
    offset_val := (page_num - 1) * per_page;
    
    -- Get total count
    SELECT COUNT(*) INTO total_count_val FROM feedback;
    
    -- Return feedback with aggregated images
    RETURN QUERY
    SELECT 
        f.id,
        f.feedback_type,
        f.user_name,
        f.user_email,
        f.description,
        f.created_at,
        f.updated_at,
        COALESCE(
            jsonb_agg(
                jsonb_build_object(
                    'id', fi.id,
                    'filename', fi.filename,
                    'original_filename', fi.original_filename,
                    'file_path', fi.file_path,
                    'storage_url', fi.storage_url,
                    'uploaded_at', fi.uploaded_at
                )
            ) FILTER (WHERE fi.id IS NOT NULL),
            '[]'::jsonb
        ) as images,
        total_count_val
    FROM feedback f
    LEFT JOIN feedback_images fi ON f.id = fi.feedback_id
    GROUP BY f.id, f.feedback_type, f.user_name, f.user_email, f.description, f.created_at, f.updated_at
    ORDER BY f.created_at DESC
    LIMIT per_page
    OFFSET offset_val;
END;
$$;


ALTER FUNCTION "public"."get_feedback_with_images"("page_num" integer, "per_page" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_notifications_paginated"("page_num" integer DEFAULT 1, "page_size" integer DEFAULT 10, "filter_read" boolean DEFAULT NULL::boolean, "filter_severity" "text" DEFAULT NULL::"text") RETURNS TABLE("id" integer, "message" "text", "notification_type" "text", "severity" "text", "check_in_id" integer, "metadata" "jsonb", "read" boolean, "created_at" timestamp with time zone, "total_count" bigint)
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    offset_val INT;
    total_records BIGINT;
BEGIN
    offset_val := (page_num - 1) * page_size;
    
    -- Get total count
    SELECT COUNT(*) INTO total_records
    FROM notifications n
    WHERE (filter_read IS NULL OR n.read = filter_read)
    AND (filter_severity IS NULL OR n.severity = filter_severity);
    
    -- Return paginated results
    RETURN QUERY
    SELECT 
        n.id,
        n.message,
        n.notification_type,
        n.severity,
        n.check_in_id,
        n.metadata,
        n.read,
        n.created_at,
        total_records
    FROM notifications n
    WHERE (filter_read IS NULL OR n.read = filter_read)
    AND (filter_severity IS NULL OR n.severity = filter_severity)
    ORDER BY n.created_at DESC
    LIMIT page_size OFFSET offset_val;
END;
$$;


ALTER FUNCTION "public"."get_notifications_paginated"("page_num" integer, "page_size" integer, "filter_read" boolean, "filter_severity" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_recent_checkins_with_calls"("limit_count" integer DEFAULT 10) RETURNS TABLE("checkin_id" integer, "load_id" "text", "ai_response_summary" "text", "ai_timestamp" timestamp with time zone, "issue_flagged" boolean, "call_status" "text", "call_id" "text", "recording_url" "text", "created_at" timestamp with time zone)
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id as checkin_id,
        c.load_id,
        c.ai_response_summary,
        c.ai_timestamp,
        c.issue_flagged,
        c.call_status,
        r.call_id,
        r.recording_url,
        c.created_at
    FROM check_ins c
    LEFT JOIN retell_calls r ON r.check_in_id = c.id
    ORDER BY c.created_at DESC
    LIMIT limit_count;
END;
$$;


ALTER FUNCTION "public"."get_recent_checkins_with_calls"("limit_count" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."mark_notification_read"("notification_id" integer) RETURNS boolean
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    UPDATE notifications 
    SET read = true, updated_at = NOW()
    WHERE id = notification_id;
    
    RETURN FOUND;
END;
$$;


ALTER FUNCTION "public"."mark_notification_read"("notification_id" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."mark_notifications_read"("notification_ids" integer[]) RETURNS integer
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE notifications 
    SET read = TRUE, updated_at = NOW()
    WHERE id = ANY(notification_ids) AND read = FALSE;
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$$;


ALTER FUNCTION "public"."mark_notifications_read"("notification_ids" integer[]) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."search_shipments_simple"("p_tenant_id" "text" DEFAULT NULL::"text", "p_shipment_id" "text" DEFAULT NULL::"text", "p_load_id" "text" DEFAULT NULL::"text", "p_fleet_phone" "text" DEFAULT NULL::"text", "p_fleet_name" "text" DEFAULT NULL::"text", "p_customer_name" "text" DEFAULT NULL::"text", "p_carrier_id" "text" DEFAULT NULL::"text", "p_job_id" "text" DEFAULT NULL::"text", "p_limit" integer DEFAULT 10, "p_offset" integer DEFAULT 0) RETURNS TABLE("long_id" "text", "tenant_id" "text", "shipment_id" "text", "load_id" "text", "fleet_phone" "text", "fleet_name" "text", "customer_name" "text", "carrier_id" "text", "job_id" "text", "data_id" "uuid", "total_count" bigint)
    LANGUAGE "sql" STABLE
    AS $$
  select
    s.long_id,
    s.tenant_id,
    s.shipment_id,
    s.load_id,
    s.fleet_phone,
    s.fleet_name,
    s.customer_name,
    s.carrier_id,
    s.job_id,
    s.data_id,
    count(*) over() as total_count
  from public.shipments s
  where (p_tenant_id is null     or s.tenant_id     = p_tenant_id)
    and (p_shipment_id is null   or s.shipment_id   = p_shipment_id)
    and (p_load_id is null       or s.load_id       = p_load_id)
    and (
      p_fleet_phone is null
      or s.fleet_phone = p_fleet_phone
      or regexp_replace(coalesce(s.fleet_phone, ''), '[^0-9]', '', 'g') = regexp_replace(p_fleet_phone, '[^0-9]', '', 'g')
    )
    and (
      p_fleet_name is null
      or btrim(p_fleet_name) = ''
      or s.fleet_name ilike ('%' || btrim(p_fleet_name) || '%')
    )
    and (
      p_customer_name is null
      or btrim(p_customer_name) = ''
      or s.customer_name ilike ('%' || btrim(p_customer_name) || '%')
    )
    and (p_carrier_id is null    or s.carrier_id    = p_carrier_id)
    and (p_job_id is null        or s.job_id        = p_job_id)
  order by s.long_id nulls last
  limit coalesce(p_limit, 10)
  offset coalesce(p_offset, 0);
$$;


ALTER FUNCTION "public"."search_shipments_simple"("p_tenant_id" "text", "p_shipment_id" "text", "p_load_id" "text", "p_fleet_phone" "text", "p_fleet_name" "text", "p_customer_name" "text", "p_carrier_id" "text", "p_job_id" "text", "p_limit" integer, "p_offset" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_updated_at_column"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_updated_at_column"() OWNER TO "postgres";

SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."check_ins" (
    "id" integer NOT NULL,
    "load_id" "text",
    "ai_response_summary" "text",
    "ai_timestamp" timestamp with time zone DEFAULT "now"(),
    "Form_type" "text",
    "issue_flagged" boolean DEFAULT false,
    "forms" "jsonb" DEFAULT '{}'::"jsonb",
    "call_status" "text" DEFAULT 'pending'::"text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "user_picked_up" boolean DEFAULT false NOT NULL,
    "confidence_score" numeric(5,4),
    "tags" "jsonb" DEFAULT '[]'::"jsonb"
);


ALTER TABLE "public"."check_ins" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."check_ins_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "public"."check_ins_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."check_ins_id_seq" OWNED BY "public"."check_ins"."id";



CREATE TABLE IF NOT EXISTS "public"."feedback" (
    "id" integer NOT NULL,
    "feedback_type" "text" NOT NULL,
    "user_name" "text" NOT NULL,
    "user_email" "text" NOT NULL,
    "description" "text" NOT NULL,
    "resolved" boolean DEFAULT false,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."feedback" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."feedback_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "public"."feedback_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."feedback_id_seq" OWNED BY "public"."feedback"."id";



CREATE TABLE IF NOT EXISTS "public"."feedback_images" (
    "id" integer NOT NULL,
    "feedback_id" integer NOT NULL,
    "filename" "text" NOT NULL,
    "original_filename" "text",
    "image_url" "text",
    "uploaded_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."feedback_images" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."feedback_images_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "public"."feedback_images_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."feedback_images_id_seq" OWNED BY "public"."feedback_images"."id";



CREATE TABLE IF NOT EXISTS "public"."notifications" (
    "id" integer NOT NULL,
    "message" "text" NOT NULL,
    "notification_type" "text" DEFAULT 'info'::"text",
    "severity" "text" DEFAULT 'info'::"text",
    "check_in_id" integer,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "read" boolean DEFAULT false,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."notifications" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."notifications_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "public"."notifications_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."notifications_id_seq" OWNED BY "public"."notifications"."id";



CREATE TABLE IF NOT EXISTS "public"."retell_calls" (
    "id" smallint NOT NULL,
    "check_in_id" integer,
    "call_transcript" "text",
    "recording_url" "text",
    "output_data" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "call_id" "text"
);


ALTER TABLE "public"."retell_calls" OWNER TO "postgres";


ALTER TABLE "public"."retell_calls" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."retell_calls_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);



CREATE TABLE IF NOT EXISTS "public"."shipment_data" (
    "data_id" "uuid" NOT NULL,
    "payload" "jsonb" NOT NULL
);


ALTER TABLE "public"."shipment_data" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."shipments" (
    "long_id" "text",
    "tenant_id" "text",
    "shipment_id" "text",
    "load_id" "text",
    "fleet_phone" "text",
    "fleet_name" "text",
    "customer_name" "text",
    "carrier_id" "text",
    "job_id" "text" NOT NULL,
    "data_id" "uuid"
);


ALTER TABLE "public"."shipments" OWNER TO "postgres";


ALTER TABLE ONLY "public"."check_ins" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."check_ins_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."feedback" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."feedback_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."feedback_images" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."feedback_images_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."notifications" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."notifications_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."check_ins"
    ADD CONSTRAINT "check_ins_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."feedback_images"
    ADD CONSTRAINT "feedback_images_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."feedback"
    ADD CONSTRAINT "feedback_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."notifications"
    ADD CONSTRAINT "notifications_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."retell_calls"
    ADD CONSTRAINT "retell_calls_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."shipment_data"
    ADD CONSTRAINT "shipment_data_pkey" PRIMARY KEY ("data_id");



ALTER TABLE ONLY "public"."shipments"
    ADD CONSTRAINT "shipments_pkey" PRIMARY KEY ("job_id");



CREATE INDEX "idx_check_ins_call_status" ON "public"."check_ins" USING "btree" ("call_status");



CREATE INDEX "idx_check_ins_issue_flagged" ON "public"."check_ins" USING "btree" ("issue_flagged");



CREATE INDEX "idx_check_ins_load_id" ON "public"."check_ins" USING "btree" ("load_id");



CREATE INDEX "idx_check_ins_timestamp" ON "public"."check_ins" USING "btree" ("ai_timestamp" DESC);



CREATE INDEX "idx_feedback_created_at" ON "public"."feedback" USING "btree" ("created_at" DESC);



CREATE INDEX "idx_feedback_images_feedback_id" ON "public"."feedback_images" USING "btree" ("feedback_id");



CREATE INDEX "idx_feedback_images_uploaded_at" ON "public"."feedback_images" USING "btree" ("uploaded_at" DESC);



CREATE INDEX "idx_feedback_resolved" ON "public"."feedback" USING "btree" ("resolved");



CREATE INDEX "idx_notifications_check_in_id" ON "public"."notifications" USING "btree" ("check_in_id");



CREATE INDEX "idx_notifications_created_at" ON "public"."notifications" USING "btree" ("created_at" DESC);



CREATE INDEX "idx_notifications_read" ON "public"."notifications" USING "btree" ("read");



CREATE INDEX "idx_retell_calls_check_in_id" ON "public"."retell_calls" USING "btree" ("check_in_id");



CREATE INDEX "idx_retell_calls_created_at" ON "public"."retell_calls" USING "btree" ("created_at" DESC);



CREATE INDEX "shipments_carrier_id_idx" ON "public"."shipments" USING "btree" ("carrier_id");



CREATE INDEX "shipments_customer_name_idx" ON "public"."shipments" USING "btree" ("customer_name");



CREATE INDEX "shipments_data_id_idx" ON "public"."shipments" USING "btree" ("data_id");



CREATE INDEX "shipments_fleet_name_idx" ON "public"."shipments" USING "btree" ("fleet_name");



CREATE INDEX "shipments_fleet_phone_idx" ON "public"."shipments" USING "btree" ("fleet_phone");



CREATE INDEX "shipments_load_id_idx" ON "public"."shipments" USING "btree" ("load_id");



CREATE UNIQUE INDEX "shipments_long_id_uk" ON "public"."shipments" USING "btree" ("long_id") WHERE ("long_id" IS NOT NULL);



CREATE INDEX "shipments_shipment_id_idx" ON "public"."shipments" USING "btree" ("shipment_id");



CREATE INDEX "shipments_tenant_id_idx" ON "public"."shipments" USING "btree" ("tenant_id");



CREATE OR REPLACE TRIGGER "update_feedback_updated_at" BEFORE UPDATE ON "public"."feedback" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



ALTER TABLE ONLY "public"."feedback_images"
    ADD CONSTRAINT "feedback_images_feedback_id_fkey" FOREIGN KEY ("feedback_id") REFERENCES "public"."feedback"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."notifications"
    ADD CONSTRAINT "notifications_check_in_id_fkey" FOREIGN KEY ("check_in_id") REFERENCES "public"."check_ins"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."retell_calls"
    ADD CONSTRAINT "retell_calls_check_in_id_fkey" FOREIGN KEY ("check_in_id") REFERENCES "public"."check_ins"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."shipments"
    ADD CONSTRAINT "shipments_data_fk" FOREIGN KEY ("data_id") REFERENCES "public"."shipment_data"("data_id");



GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";



GRANT ALL ON FUNCTION "public"."get_check_ins_paginated"("page_num" integer, "page_size" integer, "filter_issue_flagged" boolean, "filter_tags" "text", "filter_call_status" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."get_check_ins_paginated"("page_num" integer, "page_size" integer, "filter_issue_flagged" boolean, "filter_tags" "text", "filter_call_status" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_check_ins_paginated"("page_num" integer, "page_size" integer, "filter_issue_flagged" boolean, "filter_tags" "text", "filter_call_status" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_check_ins_paginated_enhanced"("page_num" integer, "page_size" integer, "filter_issue_flagged" boolean, "filter_tags" "text", "filter_call_status" "text", "search_name" "text", "search_phone" "text", "search_load_id" "text", "start_date" timestamp with time zone, "end_date" timestamp with time zone) TO "anon";
GRANT ALL ON FUNCTION "public"."get_check_ins_paginated_enhanced"("page_num" integer, "page_size" integer, "filter_issue_flagged" boolean, "filter_tags" "text", "filter_call_status" "text", "search_name" "text", "search_phone" "text", "search_load_id" "text", "start_date" timestamp with time zone, "end_date" timestamp with time zone) TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_check_ins_paginated_enhanced"("page_num" integer, "page_size" integer, "filter_issue_flagged" boolean, "filter_tags" "text", "filter_call_status" "text", "search_name" "text", "search_phone" "text", "search_load_id" "text", "start_date" timestamp with time zone, "end_date" timestamp with time zone) TO "service_role";



GRANT ALL ON FUNCTION "public"."get_check_ins_paginated_with_tags"("page_num" integer, "page_size" integer, "filter_issue_flagged" boolean, "filter_tags" "text", "filter_call_status" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."get_check_ins_paginated_with_tags"("page_num" integer, "page_size" integer, "filter_issue_flagged" boolean, "filter_tags" "text", "filter_call_status" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_check_ins_paginated_with_tags"("page_num" integer, "page_size" integer, "filter_issue_flagged" boolean, "filter_tags" "text", "filter_call_status" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_checkins_paginated"("page_num" integer, "per_page" integer, "issue_flagged_filter" boolean, "call_status_filter" "text", "tag_filter" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."get_checkins_paginated"("page_num" integer, "per_page" integer, "issue_flagged_filter" boolean, "call_status_filter" "text", "tag_filter" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_checkins_paginated"("page_num" integer, "per_page" integer, "issue_flagged_filter" boolean, "call_status_filter" "text", "tag_filter" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_checkins_per_day_chart"() TO "anon";
GRANT ALL ON FUNCTION "public"."get_checkins_per_day_chart"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_checkins_per_day_chart"() TO "service_role";



GRANT ALL ON FUNCTION "public"."get_dashboard_chart_data"() TO "anon";
GRANT ALL ON FUNCTION "public"."get_dashboard_chart_data"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_dashboard_chart_data"() TO "service_role";



GRANT ALL ON FUNCTION "public"."get_dashboard_statistics"() TO "anon";
GRANT ALL ON FUNCTION "public"."get_dashboard_statistics"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_dashboard_statistics"() TO "service_role";



GRANT ALL ON FUNCTION "public"."get_dashboard_stats"() TO "anon";
GRANT ALL ON FUNCTION "public"."get_dashboard_stats"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_dashboard_stats"() TO "service_role";



GRANT ALL ON FUNCTION "public"."get_feedback_with_images"("page_num" integer, "per_page" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."get_feedback_with_images"("page_num" integer, "per_page" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_feedback_with_images"("page_num" integer, "per_page" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."get_notifications_paginated"("page_num" integer, "page_size" integer, "filter_read" boolean, "filter_severity" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."get_notifications_paginated"("page_num" integer, "page_size" integer, "filter_read" boolean, "filter_severity" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_notifications_paginated"("page_num" integer, "page_size" integer, "filter_read" boolean, "filter_severity" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_recent_checkins_with_calls"("limit_count" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."get_recent_checkins_with_calls"("limit_count" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_recent_checkins_with_calls"("limit_count" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."mark_notification_read"("notification_id" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."mark_notification_read"("notification_id" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."mark_notification_read"("notification_id" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."mark_notifications_read"("notification_ids" integer[]) TO "anon";
GRANT ALL ON FUNCTION "public"."mark_notifications_read"("notification_ids" integer[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."mark_notifications_read"("notification_ids" integer[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."search_shipments_simple"("p_tenant_id" "text", "p_shipment_id" "text", "p_load_id" "text", "p_fleet_phone" "text", "p_fleet_name" "text", "p_customer_name" "text", "p_carrier_id" "text", "p_job_id" "text", "p_limit" integer, "p_offset" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."search_shipments_simple"("p_tenant_id" "text", "p_shipment_id" "text", "p_load_id" "text", "p_fleet_phone" "text", "p_fleet_name" "text", "p_customer_name" "text", "p_carrier_id" "text", "p_job_id" "text", "p_limit" integer, "p_offset" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."search_shipments_simple"("p_tenant_id" "text", "p_shipment_id" "text", "p_load_id" "text", "p_fleet_phone" "text", "p_fleet_name" "text", "p_customer_name" "text", "p_carrier_id" "text", "p_job_id" "text", "p_limit" integer, "p_offset" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "service_role";



GRANT ALL ON TABLE "public"."check_ins" TO "anon";
GRANT ALL ON TABLE "public"."check_ins" TO "authenticated";
GRANT ALL ON TABLE "public"."check_ins" TO "service_role";



GRANT ALL ON SEQUENCE "public"."check_ins_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."check_ins_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."check_ins_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."feedback" TO "anon";
GRANT ALL ON TABLE "public"."feedback" TO "authenticated";
GRANT ALL ON TABLE "public"."feedback" TO "service_role";



GRANT ALL ON SEQUENCE "public"."feedback_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."feedback_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."feedback_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."feedback_images" TO "anon";
GRANT ALL ON TABLE "public"."feedback_images" TO "authenticated";
GRANT ALL ON TABLE "public"."feedback_images" TO "service_role";



GRANT ALL ON SEQUENCE "public"."feedback_images_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."feedback_images_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."feedback_images_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."notifications" TO "anon";
GRANT ALL ON TABLE "public"."notifications" TO "authenticated";
GRANT ALL ON TABLE "public"."notifications" TO "service_role";



GRANT ALL ON SEQUENCE "public"."notifications_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."notifications_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."notifications_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."retell_calls" TO "anon";
GRANT ALL ON TABLE "public"."retell_calls" TO "authenticated";
GRANT ALL ON TABLE "public"."retell_calls" TO "service_role";



GRANT ALL ON SEQUENCE "public"."retell_calls_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."retell_calls_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."retell_calls_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."shipment_data" TO "anon";
GRANT ALL ON TABLE "public"."shipment_data" TO "authenticated";
GRANT ALL ON TABLE "public"."shipment_data" TO "service_role";



GRANT ALL ON TABLE "public"."shipments" TO "anon";
GRANT ALL ON TABLE "public"."shipments" TO "authenticated";
GRANT ALL ON TABLE "public"."shipments" TO "service_role";



ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "service_role";






RESET ALL;
