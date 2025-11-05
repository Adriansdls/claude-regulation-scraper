-- Initial database schema for Regulation Scraping System
-- PostgreSQL DDL for core tables

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- Create custom types
CREATE TYPE document_type AS ENUM (
    'legislation', 'regulation', 'bill', 'act', 'directive', 
    'amendment', 'proposal', 'consultation', 'guidance', 
    'case_law', 'treaty', 'other'
);

CREATE TYPE document_status AS ENUM (
    'draft', 'proposed', 'under_review', 'enacted', 
    'in_force', 'amended', 'repealed', 'withdrawn', 'expired'
);

CREATE TYPE jurisdiction AS ENUM (
    'uk', 'eu', 'us', 'canada', 'australia', 
    'new_zealand', 'international', 'other'
);

CREATE TYPE extraction_status AS ENUM (
    'pending', 'in_progress', 'completed', 'failed', 'cancelled', 'retry'
);

CREATE TYPE extraction_method AS ENUM (
    'html_parsing', 'pdf_extraction', 'ocr', 'computer_vision', 
    'api', 'manual', 'hybrid'
);

CREATE TYPE content_type AS ENUM (
    'text', 'table', 'image', 'list', 'form', 'chart', 'diagram', 'other'
);

CREATE TYPE quality_level AS ENUM (
    'excellent', 'good', 'fair', 'poor'
);

-- Core regulations table
CREATE TABLE regulations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Core identification
    title TEXT NOT NULL,
    document_type document_type NOT NULL,
    status document_status NOT NULL,
    
    -- Official identifiers (stored as JSONB for flexibility)
    identifiers JSONB NOT NULL DEFAULT '{}',
    
    -- Authority and jurisdiction
    authority JSONB NOT NULL DEFAULT '{}',
    jurisdiction jurisdiction NOT NULL,
    
    -- Content
    abstract TEXT,
    full_text TEXT,
    key_provisions TEXT[] DEFAULT '{}',
    
    -- Document structure (stored as JSONB)
    structure JSONB DEFAULT '{}',
    
    -- Dates
    created_date TIMESTAMPTZ,
    published_date DATE,
    effective_date DATE,
    last_modified_date TIMESTAMPTZ,
    expiry_date DATE,
    review_date DATE,
    
    -- Metadata
    language VARCHAR(5) NOT NULL DEFAULT 'en',
    languages VARCHAR(5)[] DEFAULT '{}',
    page_count INTEGER,
    word_count INTEGER,
    file_size BIGINT,
    format VARCHAR(50),
    encoding VARCHAR(50),
    checksum VARCHAR(128),
    
    -- Extraction metadata
    extracted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    extraction_method extraction_method NOT NULL,
    confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    processing_time DECIMAL(8,3),
    agent_version VARCHAR(50),
    source_url TEXT NOT NULL,
    source_domain VARCHAR(255) NOT NULL,
    last_checked TIMESTAMPTZ,
    
    -- Relationships (stored as arrays of UUIDs for performance)
    parent_documents UUID[] DEFAULT '{}',
    child_documents UUID[] DEFAULT '{}',
    related_documents UUID[] DEFAULT '{}',
    superseded_by UUID,
    supersedes UUID,
    
    -- Topics and classification
    topics TEXT[] DEFAULT '{}',
    keywords TEXT[] DEFAULT '{}',
    classification_codes TEXT[] DEFAULT '{}',
    
    -- Quality metrics
    completeness_score DECIMAL(3,2) CHECK (completeness_score >= 0.0 AND completeness_score <= 1.0),
    quality_flags TEXT[] DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Website profiles table
CREATE TABLE website_profiles (
    domain VARCHAR(255) PRIMARY KEY,
    base_url TEXT NOT NULL,
    title TEXT,
    
    -- Technical characteristics
    has_semantic_markup BOOLEAN DEFAULT FALSE,
    js_dependent BOOLEAN DEFAULT FALSE,
    uses_spa BOOLEAN DEFAULT FALSE,
    pdf_ratio DECIMAL(3,2) DEFAULT 0.0,
    has_complex_tables BOOLEAN DEFAULT FALSE,
    has_forms BOOLEAN DEFAULT FALSE,
    
    -- Content characteristics
    content_types JSONB DEFAULT '{}',
    estimated_documents INTEGER,
    
    -- Language and accessibility
    language VARCHAR(5) DEFAULT 'en',
    languages VARCHAR(5)[] DEFAULT '{}',
    accessibility_score DECIMAL(3,2) DEFAULT 0.0,
    
    -- Legal framework
    jurisdiction jurisdiction,
    legal_framework TEXT,
    document_types document_type[] DEFAULT '{}',
    
    -- Technical details
    robots_allowed BOOLEAN DEFAULT TRUE,
    rate_limit_info JSONB DEFAULT '{}',
    last_updated TIMESTAMPTZ,
    
    -- Analysis metadata
    profiled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    profile_version VARCHAR(10) DEFAULT '1.0',
    confidence DECIMAL(3,2) DEFAULT 0.0,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Extraction jobs table
CREATE TABLE extraction_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    url TEXT NOT NULL,
    
    -- Job configuration
    extraction_methods extraction_method[] NOT NULL,
    target_content TEXT[] DEFAULT '{}',
    max_documents INTEGER,
    
    -- Status tracking
    status extraction_status DEFAULT 'pending',
    progress DECIMAL(3,2) DEFAULT 0.0,
    
    -- Timing
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    estimated_duration INTEGER,
    
    -- Metadata
    priority INTEGER DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    -- Results
    extracted_documents UUID[] DEFAULT '{}',
    error_messages TEXT[] DEFAULT '{}',
    
    -- Configuration
    user_agent TEXT,
    request_delay DECIMAL(4,1) DEFAULT 1.0,
    timeout INTEGER DEFAULT 30,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Extracted content table
CREATE TABLE extracted_content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES extraction_jobs(id) ON DELETE CASCADE,
    
    -- Content details
    content_type content_type NOT NULL,
    raw_content TEXT NOT NULL,
    processed_content TEXT,
    
    -- Source information
    source_url TEXT NOT NULL,
    source_element TEXT,
    xpath TEXT,
    bbox DECIMAL[] CHECK (array_length(bbox, 1) = 4), -- [x1,y1,x2,y2]
    
    -- Extraction metadata
    extraction_method extraction_method NOT NULL,
    confidence DECIMAL(3,2) NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    quality quality_level NOT NULL,
    
    -- Processing information
    extracted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processing_time DECIMAL(8,3),
    agent_id VARCHAR(100),
    
    -- Content attributes
    language VARCHAR(5),
    word_count INTEGER,
    character_count INTEGER,
    
    -- Relationships
    parent_content_id UUID REFERENCES extracted_content(id),
    related_content_ids UUID[] DEFAULT '{}',
    
    -- Quality indicators
    has_errors BOOLEAN DEFAULT FALSE,
    error_details TEXT[] DEFAULT '{}',
    validation_flags TEXT[] DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Regulation collections table
CREATE TABLE regulation_collections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    regulations UUID[] DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Agent metrics table
CREATE TABLE agent_metrics (
    agent_id VARCHAR(100) NOT NULL,
    agent_type VARCHAR(50) NOT NULL,
    metric_date DATE NOT NULL,
    
    -- Performance metrics
    jobs_processed INTEGER DEFAULT 0,
    content_extracted INTEGER DEFAULT 0,
    average_confidence DECIMAL(3,2) DEFAULT 0.0,
    success_rate DECIMAL(3,2) DEFAULT 0.0,
    
    -- Timing metrics
    average_processing_time DECIMAL(8,3) DEFAULT 0.0,
    total_processing_time DECIMAL(12,3) DEFAULT 0.0,
    
    -- Quality metrics
    quality_scores JSONB DEFAULT '{}',
    error_rate DECIMAL(3,2) DEFAULT 0.0,
    
    -- Resource usage
    memory_usage DECIMAL(8,2), -- MB
    cpu_usage DECIMAL(5,2),    -- %
    
    -- Activity
    last_active TIMESTAMPTZ,
    uptime INTEGER, -- seconds
    
    PRIMARY KEY (agent_id, metric_date)
);

-- Create indexes for performance
CREATE INDEX idx_regulations_document_type ON regulations(document_type);
CREATE INDEX idx_regulations_status ON regulations(status);
CREATE INDEX idx_regulations_jurisdiction ON regulations(jurisdiction);
CREATE INDEX idx_regulations_source_domain ON regulations(source_domain);
CREATE INDEX idx_regulations_extracted_at ON regulations(extracted_at);
CREATE INDEX idx_regulations_effective_date ON regulations(effective_date);
CREATE INDEX idx_regulations_published_date ON regulations(published_date);

-- Full-text search indexes
CREATE INDEX idx_regulations_title_fulltext ON regulations USING gin(to_tsvector('english', title));
CREATE INDEX idx_regulations_abstract_fulltext ON regulations USING gin(to_tsvector('english', coalesce(abstract, '')));
CREATE INDEX idx_regulations_full_text_fulltext ON regulations USING gin(to_tsvector('english', coalesce(full_text, '')));

-- JSONB indexes
CREATE INDEX idx_regulations_identifiers ON regulations USING gin(identifiers);
CREATE INDEX idx_regulations_authority ON regulations USING gin(authority);
CREATE INDEX idx_regulations_structure ON regulations USING gin(structure);

-- Array indexes  
CREATE INDEX idx_regulations_topics ON regulations USING gin(topics);
CREATE INDEX idx_regulations_keywords ON regulations USING gin(keywords);
CREATE INDEX idx_regulations_classification_codes ON regulations USING gin(classification_codes);

-- Extraction job indexes
CREATE INDEX idx_extraction_jobs_status ON extraction_jobs(status);
CREATE INDEX idx_extraction_jobs_created_at ON extraction_jobs(created_at);
CREATE INDEX idx_extraction_jobs_priority ON extraction_jobs(priority);
CREATE INDEX idx_extraction_jobs_url ON extraction_jobs(url);

-- Extracted content indexes
CREATE INDEX idx_extracted_content_job_id ON extracted_content(job_id);
CREATE INDEX idx_extracted_content_type ON extracted_content(content_type);
CREATE INDEX idx_extracted_content_quality ON extracted_content(quality);
CREATE INDEX idx_extracted_content_extracted_at ON extracted_content(extracted_at);

-- Website profile indexes
CREATE INDEX idx_website_profiles_jurisdiction ON website_profiles(jurisdiction);
CREATE INDEX idx_website_profiles_profiled_at ON website_profiles(profiled_at);

-- Agent metrics indexes
CREATE INDEX idx_agent_metrics_agent_type ON agent_metrics(agent_type);
CREATE INDEX idx_agent_metrics_metric_date ON agent_metrics(metric_date);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to automatically update updated_at
CREATE TRIGGER update_regulations_updated_at 
    BEFORE UPDATE ON regulations 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_website_profiles_updated_at 
    BEFORE UPDATE ON website_profiles 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_extraction_jobs_updated_at 
    BEFORE UPDATE ON extraction_jobs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_regulation_collections_updated_at 
    BEFORE UPDATE ON regulation_collections 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create views for common queries
CREATE VIEW active_regulations AS
SELECT * FROM regulations 
WHERE status IN ('enacted', 'in_force')
AND (expiry_date IS NULL OR expiry_date > CURRENT_DATE);

CREATE VIEW recent_extractions AS
SELECT r.*, ej.created_at as job_created_at, ej.status as job_status
FROM regulations r
JOIN extraction_jobs ej ON r.id = ANY(ej.extracted_documents)
WHERE ej.created_at > CURRENT_DATE - INTERVAL '7 days';

CREATE VIEW extraction_job_summary AS
SELECT 
    ej.id,
    ej.url,
    ej.status,
    ej.progress,
    ej.created_at,
    ej.started_at,
    ej.completed_at,
    array_length(ej.extracted_documents, 1) as documents_extracted,
    array_length(ej.error_messages, 1) as error_count
FROM extraction_jobs ej;

-- Create function for full-text search
CREATE OR REPLACE FUNCTION search_regulations(
    query_text TEXT,
    doc_types document_type[] DEFAULT NULL,
    jurisdictions jurisdiction[] DEFAULT NULL,
    limit_results INTEGER DEFAULT 20,
    offset_results INTEGER DEFAULT 0
)
RETURNS TABLE (
    id UUID,
    title TEXT,
    document_type document_type,
    jurisdiction jurisdiction,
    rank REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        r.id,
        r.title,
        r.document_type,
        r.jurisdiction,
        ts_rank(
            to_tsvector('english', r.title || ' ' || coalesce(r.abstract, '') || ' ' || coalesce(r.full_text, '')),
            plainto_tsquery('english', query_text)
        ) as rank
    FROM regulations r
    WHERE 
        to_tsvector('english', r.title || ' ' || coalesce(r.abstract, '') || ' ' || coalesce(r.full_text, ''))
        @@ plainto_tsquery('english', query_text)
        AND (doc_types IS NULL OR r.document_type = ANY(doc_types))
        AND (jurisdictions IS NULL OR r.jurisdiction = ANY(jurisdictions))
    ORDER BY rank DESC, r.created_at DESC
    LIMIT limit_results
    OFFSET offset_results;
END;
$$ LANGUAGE plpgsql;