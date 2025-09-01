-- Add webhooks table to track webhook events and their processing status
SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

BEGIN;

-- Create webhooks table
CREATE TABLE IF NOT EXISTS "public"."webhooks" (
    "id" integer NOT NULL,
    "webhook_type" text NOT NULL,
    "source" text NOT NULL,
    "payload" jsonb NOT NULL,
    "headers" jsonb DEFAULT '{}'::jsonb,
    "status" text DEFAULT 'pending'::text,
    "processed_at" timestamp with time zone,
    "error_message" text,
    "retry_count" integer DEFAULT 0,
    "created_at" timestamp with time zone DEFAULT now(),
    "updated_at" timestamp with time zone DEFAULT now()
);

-- Set table owner
ALTER TABLE "public"."webhooks" OWNER TO "postgres";

-- Create sequence for auto-incrementing ID
CREATE SEQUENCE IF NOT EXISTS "public"."webhooks_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE "public"."webhooks_id_seq" OWNER TO "postgres";

-- Set sequence ownership
ALTER SEQUENCE "public"."webhooks_id_seq" OWNED BY "public"."webhooks"."id";

-- Set default value for ID column
ALTER TABLE ONLY "public"."webhooks" ALTER COLUMN "id" SET DEFAULT nextval('"public"."webhooks_id_seq"'::regclass);

-- Add primary key constraint
ALTER TABLE ONLY "public"."webhooks"
    ADD CONSTRAINT "webhooks_pkey" PRIMARY KEY ("id");

-- Create indexes for efficient querying
CREATE INDEX "idx_webhooks_type" ON "public"."webhooks" USING btree ("webhook_type");
CREATE INDEX "idx_webhooks_status" ON "public"."webhooks" USING btree ("status");
CREATE INDEX "idx_webhooks_source" ON "public"."webhooks" USING btree ("source");
CREATE INDEX "idx_webhooks_created_at" ON "public"."webhooks" USING btree ("created_at" DESC);

COMMIT;