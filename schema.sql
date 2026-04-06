--
-- PostgreSQL database dump
--

\restrict a7e7UPCoTAE2VPNBUVNGir0ki0NUKI5Sjef45xW6fPDPQ5wqdvP8QfFYe831SZ3

-- Dumped from database version 16.13 (Ubuntu 16.13-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.13 (Ubuntu 16.13-0ubuntu0.24.04.1)

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

--
-- Name: job_statuses; Type: TYPE; Schema: public; Owner: kazi_admin
--

CREATE TYPE public.job_statuses AS ENUM (
    'pending',
    'accepted',
    'in_progress',
    'completed',
    'disputed',
    'cancelled'
);


ALTER TYPE public.job_statuses OWNER TO kazi_admin;

--
-- Name: notification_priorities; Type: TYPE; Schema: public; Owner: kazi_admin
--

CREATE TYPE public.notification_priorities AS ENUM (
    'high',
    'normal',
    'low'
);


ALTER TYPE public.notification_priorities OWNER TO kazi_admin;

--
-- Name: notification_statuses; Type: TYPE; Schema: public; Owner: kazi_admin
--

CREATE TYPE public.notification_statuses AS ENUM (
    'pending',
    'sent',
    'delivered',
    'failed'
);


ALTER TYPE public.notification_statuses OWNER TO kazi_admin;

--
-- Name: notification_types; Type: TYPE; Schema: public; Owner: kazi_admin
--

CREATE TYPE public.notification_types AS ENUM (
    'push',
    'sms',
    'ussd'
);


ALTER TYPE public.notification_types OWNER TO kazi_admin;

--
-- Name: payment_statuses; Type: TYPE; Schema: public; Owner: kazi_admin
--

CREATE TYPE public.payment_statuses AS ENUM (
    'held',
    'released',
    'refunded'
);


ALTER TYPE public.payment_statuses OWNER TO kazi_admin;

--
-- Name: sms_directions; Type: TYPE; Schema: public; Owner: kazi_admin
--

CREATE TYPE public.sms_directions AS ENUM (
    'inbound',
    'outbound'
);


ALTER TYPE public.sms_directions OWNER TO kazi_admin;

--
-- Name: sync_actions; Type: TYPE; Schema: public; Owner: kazi_admin
--

CREATE TYPE public.sync_actions AS ENUM (
    'create_job',
    'update_job',
    'upload_photo',
    'add_note'
);


ALTER TYPE public.sync_actions OWNER TO kazi_admin;

--
-- Name: sync_statuses; Type: TYPE; Schema: public; Owner: kazi_admin
--

CREATE TYPE public.sync_statuses AS ENUM (
    'pending',
    'processing',
    'completed',
    'failed'
);


ALTER TYPE public.sync_statuses OWNER TO kazi_admin;

--
-- Name: transaction_types; Type: TYPE; Schema: public; Owner: kazi_admin
--

CREATE TYPE public.transaction_types AS ENUM (
    'credit',
    'debit'
);


ALTER TYPE public.transaction_types OWNER TO kazi_admin;

--
-- Name: update_types; Type: TYPE; Schema: public; Owner: kazi_admin
--

CREATE TYPE public.update_types AS ENUM (
    'progress',
    'note',
    'photo',
    'status_change'
);


ALTER TYPE public.update_types OWNER TO kazi_admin;

--
-- Name: user_roles; Type: TYPE; Schema: public; Owner: kazi_admin
--

CREATE TYPE public.user_roles AS ENUM (
    'customer',
    'worker',
    'admin'
);


ALTER TYPE public.user_roles OWNER TO kazi_admin;

--
-- Name: verification_statuses; Type: TYPE; Schema: public; Owner: kazi_admin
--

CREATE TYPE public.verification_statuses AS ENUM (
    'pending',
    'verified',
    'rejected'
);


ALTER TYPE public.verification_statuses OWNER TO kazi_admin;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: kazi_admin
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO kazi_admin;

--
-- Name: categories; Type: TABLE; Schema: public; Owner: kazi_admin
--

CREATE TABLE public.categories (
    id character varying(36) NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    is_active boolean,
    created_at timestamp without time zone
);


ALTER TABLE public.categories OWNER TO kazi_admin;

--
-- Name: job_updates; Type: TABLE; Schema: public; Owner: kazi_admin
--

CREATE TABLE public.job_updates (
    id character varying(36) NOT NULL,
    job_id character varying(36) NOT NULL,
    user_id character varying(36) NOT NULL,
    update_type public.update_types NOT NULL,
    progress_percentage integer,
    note text,
    photo_urls json,
    old_status character varying(50),
    new_status character varying(50),
    created_offline boolean,
    synced_at timestamp without time zone,
    created_at timestamp without time zone
);


ALTER TABLE public.job_updates OWNER TO kazi_admin;

--
-- Name: jobs; Type: TABLE; Schema: public; Owner: kazi_admin
--

CREATE TABLE public.jobs (
    id character varying(36) NOT NULL,
    customer_id character varying(36) NOT NULL,
    worker_id character varying(36),
    category_id character varying(36) NOT NULL,
    title character varying(200) NOT NULL,
    description text NOT NULL,
    location character varying(200) NOT NULL,
    budget numeric(10,2) NOT NULL,
    status public.job_statuses,
    scheduled_date timestamp without time zone,
    completed_at timestamp without time zone,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.jobs OWNER TO kazi_admin;

--
-- Name: login_attempts; Type: TABLE; Schema: public; Owner: kazi_admin
--

CREATE TABLE public.login_attempts (
    id character varying(36) NOT NULL,
    user_id character varying(36),
    created_at timestamp without time zone,
    email character varying(120),
    ip_address character varying(45),
    user_agent character varying(255),
    success boolean DEFAULT false,
    failure_reason character varying(100)
);


ALTER TABLE public.login_attempts OWNER TO kazi_admin;

--
-- Name: notifications; Type: TABLE; Schema: public; Owner: kazi_admin
--

CREATE TABLE public.notifications (
    id character varying(36) NOT NULL,
    user_id character varying(36) NOT NULL,
    job_id character varying(36),
    type public.notification_types NOT NULL,
    title character varying(200),
    message text NOT NULL,
    status public.notification_statuses,
    priority public.notification_priorities,
    retry_count integer,
    max_retries integer,
    scheduled_at timestamp without time zone,
    sent_at timestamp without time zone,
    delivered_at timestamp without time zone,
    created_at timestamp without time zone,
    external_id character varying(100),
    error_message text
);


ALTER TABLE public.notifications OWNER TO kazi_admin;

--
-- Name: otp_verifications; Type: TABLE; Schema: public; Owner: kazi_admin
--

CREATE TABLE public.otp_verifications (
    id character varying(36) NOT NULL,
    user_id character varying(36) NOT NULL,
    phone character varying(20) NOT NULL,
    otp_code character varying(6) NOT NULL,
    is_verified boolean,
    expires_at timestamp without time zone NOT NULL,
    created_at timestamp without time zone,
    purpose character varying(20) DEFAULT 'registration'::character varying
);


ALTER TABLE public.otp_verifications OWNER TO kazi_admin;

--
-- Name: payments; Type: TABLE; Schema: public; Owner: kazi_admin
--

CREATE TABLE public.payments (
    id character varying(36) NOT NULL,
    job_id character varying(36) NOT NULL,
    amount numeric(10,2) NOT NULL,
    commission numeric(10,2) NOT NULL,
    worker_payout numeric(10,2) NOT NULL,
    status public.payment_statuses,
    paid_at timestamp without time zone,
    released_at timestamp without time zone,
    created_at timestamp without time zone
);


ALTER TABLE public.payments OWNER TO kazi_admin;

--
-- Name: reviews; Type: TABLE; Schema: public; Owner: kazi_admin
--

CREATE TABLE public.reviews (
    id character varying(36) NOT NULL,
    job_id character varying(36) NOT NULL,
    customer_id character varying(36) NOT NULL,
    worker_id character varying(36) NOT NULL,
    rating integer NOT NULL,
    comment text,
    created_at timestamp without time zone,
    CONSTRAINT rating_range CHECK (((rating >= 1) AND (rating <= 5)))
);


ALTER TABLE public.reviews OWNER TO kazi_admin;

--
-- Name: sms_logs; Type: TABLE; Schema: public; Owner: kazi_admin
--

CREATE TABLE public.sms_logs (
    id character varying(36) NOT NULL,
    phone character varying(20) NOT NULL,
    message text NOT NULL,
    direction public.sms_directions NOT NULL,
    status character varying(50),
    external_id character varying(100),
    created_at timestamp without time zone
);


ALTER TABLE public.sms_logs OWNER TO kazi_admin;

--
-- Name: sync_queue; Type: TABLE; Schema: public; Owner: kazi_admin
--

CREATE TABLE public.sync_queue (
    id character varying(36) NOT NULL,
    user_id character varying(36) NOT NULL,
    device_id character varying(100) NOT NULL,
    action_type public.sync_actions NOT NULL,
    payload json NOT NULL,
    client_timestamp timestamp without time zone NOT NULL,
    status public.sync_statuses,
    error_message text,
    retry_count integer,
    created_at timestamp without time zone,
    processed_at timestamp without time zone
);


ALTER TABLE public.sync_queue OWNER TO kazi_admin;

--
-- Name: transactions; Type: TABLE; Schema: public; Owner: kazi_admin
--

CREATE TABLE public.transactions (
    id character varying(36) NOT NULL,
    wallet_id character varying(36) NOT NULL,
    payment_id character varying(36),
    type public.transaction_types NOT NULL,
    amount numeric(10,2) NOT NULL,
    description character varying(255),
    balance_after numeric(10,2) NOT NULL,
    created_at timestamp without time zone
);


ALTER TABLE public.transactions OWNER TO kazi_admin;

--
-- Name: user_presence; Type: TABLE; Schema: public; Owner: kazi_admin
--

CREATE TABLE public.user_presence (
    id character varying(36) NOT NULL,
    user_id character varying(36) NOT NULL,
    is_online boolean,
    last_seen timestamp without time zone,
    last_heartbeat timestamp without time zone,
    device_id character varying(100),
    device_type character varying(50),
    app_version character varying(20),
    ip_address character varying(50),
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.user_presence OWNER TO kazi_admin;

--
-- Name: users; Type: TABLE; Schema: public; Owner: kazi_admin
--

CREATE TABLE public.users (
    id character varying(36) NOT NULL,
    email character varying(120) NOT NULL,
    password_hash character varying(255) NOT NULL,
    full_name character varying(100) NOT NULL,
    phone character varying(20) NOT NULL,
    phone_verified boolean,
    role public.user_roles NOT NULL,
    is_active boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.users OWNER TO kazi_admin;

--
-- Name: ussd_sessions; Type: TABLE; Schema: public; Owner: kazi_admin
--

CREATE TABLE public.ussd_sessions (
    id character varying(36) NOT NULL,
    session_id character varying(100) NOT NULL,
    phone character varying(20) NOT NULL,
    user_id character varying(36),
    state character varying(50),
    context_data json,
    is_active boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.ussd_sessions OWNER TO kazi_admin;

--
-- Name: wallets; Type: TABLE; Schema: public; Owner: kazi_admin
--

CREATE TABLE public.wallets (
    id character varying(36) NOT NULL,
    user_id character varying(36) NOT NULL,
    balance numeric(10,2) NOT NULL,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.wallets OWNER TO kazi_admin;

--
-- Name: worker_skills; Type: TABLE; Schema: public; Owner: kazi_admin
--

CREATE TABLE public.worker_skills (
    id character varying(36) NOT NULL,
    worker_id character varying(36) NOT NULL,
    category_id character varying(36) NOT NULL,
    experience_years integer,
    created_at timestamp without time zone
);


ALTER TABLE public.worker_skills OWNER TO kazi_admin;

--
-- Name: worker_verifications; Type: TABLE; Schema: public; Owner: kazi_admin
--

CREATE TABLE public.worker_verifications (
    id character varying(36) NOT NULL,
    worker_id character varying(36) NOT NULL,
    national_id_verified boolean,
    phone_verified boolean,
    face_verified boolean,
    skills_certified boolean,
    national_id_score integer,
    phone_score integer,
    face_score integer,
    skills_score integer,
    total_score integer,
    verification_status character varying(20),
    admin_notes text,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    overall_score integer DEFAULT 0,
    national_id_number character varying(50),
    national_id_front_url text,
    national_id_back_url text,
    id_verification_score integer DEFAULT 0,
    id_verified boolean DEFAULT false,
    phone_verification_date timestamp without time zone,
    selfie_url text,
    face_match_score double precision DEFAULT 0,
    skill_documents_url text[],
    skill_verification_score integer DEFAULT 0,
    skill_verified boolean DEFAULT false,
    auto_approved boolean DEFAULT false,
    manual_review_required boolean DEFAULT false,
    flagged boolean DEFAULT false,
    flag_reason text,
    reviewed_by character varying(36),
    reviewed_at timestamp without time zone
);


ALTER TABLE public.worker_verifications OWNER TO kazi_admin;

--
-- Name: workers; Type: TABLE; Schema: public; Owner: kazi_admin
--

CREATE TABLE public.workers (
    id character varying(36) NOT NULL,
    user_id character varying(36) NOT NULL,
    hourly_rate numeric(10,2) NOT NULL,
    location character varying(200) NOT NULL,
    bio text,
    availability boolean,
    verification_status public.verification_statuses,
    rating numeric(3,2),
    total_reviews integer,
    total_jobs_completed integer,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.workers OWNER TO kazi_admin;

--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: categories categories_pkey; Type: CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_pkey PRIMARY KEY (id);


--
-- Name: job_updates job_updates_pkey; Type: CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.job_updates
    ADD CONSTRAINT job_updates_pkey PRIMARY KEY (id);


--
-- Name: jobs jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (id);


--
-- Name: login_attempts login_attempts_pkey; Type: CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.login_attempts
    ADD CONSTRAINT login_attempts_pkey PRIMARY KEY (id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: otp_verifications otp_verifications_pkey; Type: CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.otp_verifications
    ADD CONSTRAINT otp_verifications_pkey PRIMARY KEY (id);


--
-- Name: payments payments_job_id_key; Type: CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_job_id_key UNIQUE (job_id);


--
-- Name: payments payments_pkey; Type: CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_pkey PRIMARY KEY (id);


--
-- Name: reviews reviews_job_id_key; Type: CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_job_id_key UNIQUE (job_id);


--
-- Name: reviews reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_pkey PRIMARY KEY (id);


--
-- Name: sms_logs sms_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.sms_logs
    ADD CONSTRAINT sms_logs_pkey PRIMARY KEY (id);


--
-- Name: sync_queue sync_queue_pkey; Type: CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.sync_queue
    ADD CONSTRAINT sync_queue_pkey PRIMARY KEY (id);


--
-- Name: transactions transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_pkey PRIMARY KEY (id);


--
-- Name: user_presence user_presence_pkey; Type: CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.user_presence
    ADD CONSTRAINT user_presence_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ussd_sessions ussd_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.ussd_sessions
    ADD CONSTRAINT ussd_sessions_pkey PRIMARY KEY (id);


--
-- Name: wallets wallets_pkey; Type: CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.wallets
    ADD CONSTRAINT wallets_pkey PRIMARY KEY (id);


--
-- Name: wallets wallets_user_id_key; Type: CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.wallets
    ADD CONSTRAINT wallets_user_id_key UNIQUE (user_id);


--
-- Name: worker_skills worker_skills_pkey; Type: CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.worker_skills
    ADD CONSTRAINT worker_skills_pkey PRIMARY KEY (id);


--
-- Name: worker_verifications worker_verifications_pkey; Type: CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.worker_verifications
    ADD CONSTRAINT worker_verifications_pkey PRIMARY KEY (id);


--
-- Name: worker_verifications worker_verifications_worker_id_key; Type: CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.worker_verifications
    ADD CONSTRAINT worker_verifications_worker_id_key UNIQUE (worker_id);


--
-- Name: workers workers_pkey; Type: CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.workers
    ADD CONSTRAINT workers_pkey PRIMARY KEY (id);


--
-- Name: workers workers_user_id_key; Type: CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.workers
    ADD CONSTRAINT workers_user_id_key UNIQUE (user_id);


--
-- Name: ix_categories_name; Type: INDEX; Schema: public; Owner: kazi_admin
--

CREATE UNIQUE INDEX ix_categories_name ON public.categories USING btree (name);


--
-- Name: ix_job_updates_created_at; Type: INDEX; Schema: public; Owner: kazi_admin
--

CREATE INDEX ix_job_updates_created_at ON public.job_updates USING btree (created_at);


--
-- Name: ix_job_updates_job_id; Type: INDEX; Schema: public; Owner: kazi_admin
--

CREATE INDEX ix_job_updates_job_id ON public.job_updates USING btree (job_id);


--
-- Name: ix_jobs_category_id; Type: INDEX; Schema: public; Owner: kazi_admin
--

CREATE INDEX ix_jobs_category_id ON public.jobs USING btree (category_id);


--
-- Name: ix_jobs_customer_id; Type: INDEX; Schema: public; Owner: kazi_admin
--

CREATE INDEX ix_jobs_customer_id ON public.jobs USING btree (customer_id);


--
-- Name: ix_jobs_status; Type: INDEX; Schema: public; Owner: kazi_admin
--

CREATE INDEX ix_jobs_status ON public.jobs USING btree (status);


--
-- Name: ix_jobs_worker_id; Type: INDEX; Schema: public; Owner: kazi_admin
--

CREATE INDEX ix_jobs_worker_id ON public.jobs USING btree (worker_id);


--
-- Name: ix_notifications_created_at; Type: INDEX; Schema: public; Owner: kazi_admin
--

CREATE INDEX ix_notifications_created_at ON public.notifications USING btree (created_at);


--
-- Name: ix_notifications_job_id; Type: INDEX; Schema: public; Owner: kazi_admin
--

CREATE INDEX ix_notifications_job_id ON public.notifications USING btree (job_id);


--
-- Name: ix_notifications_status; Type: INDEX; Schema: public; Owner: kazi_admin
--

CREATE INDEX ix_notifications_status ON public.notifications USING btree (status);


--
-- Name: ix_notifications_user_id; Type: INDEX; Schema: public; Owner: kazi_admin
--

CREATE INDEX ix_notifications_user_id ON public.notifications USING btree (user_id);


--
-- Name: ix_payments_status; Type: INDEX; Schema: public; Owner: kazi_admin
--

CREATE INDEX ix_payments_status ON public.payments USING btree (status);


--
-- Name: ix_reviews_worker_id; Type: INDEX; Schema: public; Owner: kazi_admin
--

CREATE INDEX ix_reviews_worker_id ON public.reviews USING btree (worker_id);


--
-- Name: ix_sms_logs_created_at; Type: INDEX; Schema: public; Owner: kazi_admin
--

CREATE INDEX ix_sms_logs_created_at ON public.sms_logs USING btree (created_at);


--
-- Name: ix_sms_logs_phone; Type: INDEX; Schema: public; Owner: kazi_admin
--

CREATE INDEX ix_sms_logs_phone ON public.sms_logs USING btree (phone);


--
-- Name: ix_sync_queue_created_at; Type: INDEX; Schema: public; Owner: kazi_admin
--

CREATE INDEX ix_sync_queue_created_at ON public.sync_queue USING btree (created_at);


--
-- Name: ix_sync_queue_status; Type: INDEX; Schema: public; Owner: kazi_admin
--

CREATE INDEX ix_sync_queue_status ON public.sync_queue USING btree (status);


--
-- Name: ix_sync_queue_user_id; Type: INDEX; Schema: public; Owner: kazi_admin
--

CREATE INDEX ix_sync_queue_user_id ON public.sync_queue USING btree (user_id);


--
-- Name: ix_transactions_created_at; Type: INDEX; Schema: public; Owner: kazi_admin
--

CREATE INDEX ix_transactions_created_at ON public.transactions USING btree (created_at);


--
-- Name: ix_transactions_wallet_id; Type: INDEX; Schema: public; Owner: kazi_admin
--

CREATE INDEX ix_transactions_wallet_id ON public.transactions USING btree (wallet_id);


--
-- Name: ix_user_presence_is_online; Type: INDEX; Schema: public; Owner: kazi_admin
--

CREATE INDEX ix_user_presence_is_online ON public.user_presence USING btree (is_online);


--
-- Name: ix_user_presence_user_id; Type: INDEX; Schema: public; Owner: kazi_admin
--

CREATE UNIQUE INDEX ix_user_presence_user_id ON public.user_presence USING btree (user_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: kazi_admin
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_ussd_sessions_phone; Type: INDEX; Schema: public; Owner: kazi_admin
--

CREATE INDEX ix_ussd_sessions_phone ON public.ussd_sessions USING btree (phone);


--
-- Name: ix_ussd_sessions_session_id; Type: INDEX; Schema: public; Owner: kazi_admin
--

CREATE UNIQUE INDEX ix_ussd_sessions_session_id ON public.ussd_sessions USING btree (session_id);


--
-- Name: ix_workers_location; Type: INDEX; Schema: public; Owner: kazi_admin
--

CREATE INDEX ix_workers_location ON public.workers USING btree (location);


--
-- Name: job_updates job_updates_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.job_updates
    ADD CONSTRAINT job_updates_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.jobs(id) ON DELETE CASCADE;


--
-- Name: job_updates job_updates_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.job_updates
    ADD CONSTRAINT job_updates_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: jobs jobs_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.categories(id) ON DELETE SET NULL;


--
-- Name: jobs jobs_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: jobs jobs_worker_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_worker_id_fkey FOREIGN KEY (worker_id) REFERENCES public.workers(id) ON DELETE SET NULL;


--
-- Name: login_attempts login_attempts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.login_attempts
    ADD CONSTRAINT login_attempts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: notifications notifications_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.jobs(id) ON DELETE CASCADE;


--
-- Name: notifications notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: otp_verifications otp_verifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.otp_verifications
    ADD CONSTRAINT otp_verifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: payments payments_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.jobs(id) ON DELETE CASCADE;


--
-- Name: reviews reviews_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: reviews reviews_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.jobs(id) ON DELETE CASCADE;


--
-- Name: reviews reviews_worker_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_worker_id_fkey FOREIGN KEY (worker_id) REFERENCES public.workers(id) ON DELETE CASCADE;


--
-- Name: sync_queue sync_queue_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.sync_queue
    ADD CONSTRAINT sync_queue_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: transactions transactions_payment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_payment_id_fkey FOREIGN KEY (payment_id) REFERENCES public.payments(id) ON DELETE SET NULL;


--
-- Name: transactions transactions_wallet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_wallet_id_fkey FOREIGN KEY (wallet_id) REFERENCES public.wallets(id) ON DELETE CASCADE;


--
-- Name: user_presence user_presence_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.user_presence
    ADD CONSTRAINT user_presence_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: ussd_sessions ussd_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.ussd_sessions
    ADD CONSTRAINT ussd_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: wallets wallets_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.wallets
    ADD CONSTRAINT wallets_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: worker_skills worker_skills_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.worker_skills
    ADD CONSTRAINT worker_skills_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.categories(id) ON DELETE CASCADE;


--
-- Name: worker_skills worker_skills_worker_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.worker_skills
    ADD CONSTRAINT worker_skills_worker_id_fkey FOREIGN KEY (worker_id) REFERENCES public.workers(id) ON DELETE CASCADE;


--
-- Name: worker_verifications worker_verifications_worker_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.worker_verifications
    ADD CONSTRAINT worker_verifications_worker_id_fkey FOREIGN KEY (worker_id) REFERENCES public.workers(id);


--
-- Name: workers workers_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: kazi_admin
--

ALTER TABLE ONLY public.workers
    ADD CONSTRAINT workers_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT ALL ON SCHEMA public TO kazi_admin;


--
-- PostgreSQL database dump complete
--

\unrestrict a7e7UPCoTAE2VPNBUVNGir0ki0NUKI5Sjef45xW6fPDPQ5wqdvP8QfFYe831SZ3

