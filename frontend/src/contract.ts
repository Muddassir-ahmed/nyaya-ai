import { z } from 'zod';

// Mirrors the supplied backend app/schemas files. Validate at the HTTP boundary;
// TypeScript types alone cannot validate JSON received over the network.
const optionalText = z.string().nullable().default(null);
const texts = z.array(z.string()).default([]);
const emergencyType = z.enum(['police', 'fire', 'medical', 'women_safety', 'child_safety', 'disaster', 'cybercrime', 'other']);

const analysisSchema = z.object({
  original_query: z.string().min(1),
  intent: z.enum(['legal_information', 'legal_procedure', 'complaint_guidance', 'authority_lookup', 'document_guidance', 'emergency', 'general_civic', 'out_of_scope']),
  domain: z.enum(['criminal', 'civil', 'property', 'employment', 'consumer', 'cybercrime', 'traffic', 'family', 'constitutional', 'government_services', 'unknown']),
  jurisdiction: optionalText,
  urgency: z.enum(['normal', 'urgent', 'emergency']).default('normal'),
  keywords: texts,
  rewritten_queries: texts,
  requires_follow_up: z.boolean().default(false),
  missing_information: texts,
});

const legalAnswerSchema = z.object({
  summary: z.string(),
  legal_basis: texts,
  possible_options: texts,
  evidence_to_preserve: texts,
  next_steps: texts,
  caveats: texts,
  citations: texts,
});

const evidenceSchema = z.object({
  chunk_id: z.number().int(),
  content: z.string(),
  citation_id: optionalText,
  document_title: optionalText,
  document_type: optionalText,
  act_name: optionalText,
  act_short_name: optionalText,
  version_label: optionalText,
  section_number: optionalText,
  section_title: optionalText,
  subsection_number: optionalText,
  clause_number: optionalText,
  source_name: optionalText,
  source_publisher: optionalText,
  source_url: optionalText,
  publication_date: optionalText,
  retrieved_at: optionalText,
  citation_text: optionalText,
  is_verified: z.boolean().default(false),
});

const emergencySchema = z.object({
  is_emergency: z.boolean(),
  emergency_type: emergencyType.nullable().default(null),
  immediate_actions: texts,
  safety_warning: optionalText,
  verification_note: optionalText,
  contacts: z.array(z.object({
    name: z.string(),
    emergency_type: emergencyType,
    phone_number: z.string(),
    jurisdiction: z.string(),
    primary_source_name: z.string(),
    primary_source_url: z.string(),
    secondary_source_name: optionalText,
    secondary_source_url: optionalText,
    is_verified: z.boolean().default(false),
    is_active: z.boolean().default(true),
    verified_at: optionalText,
    verification_notes: optionalText,
  })).default([]),
});

const authoritySchema = z.object({
  service_key: z.string(),
  jurisdiction: optionalText,
  verification_note: optionalText,
  authorities: z.array(z.object({
    id: z.number().int(),
    name: z.string(),
    authority_type: z.enum(['police', 'cybercrime', 'consumer', 'labour', 'transport', 'revenue_land', 'municipal', 'district_administration', 'legal_services', 'other']),
    domain: z.string(),
    service_key: z.string(),
    service_name: z.string(),
    description: optionalText,
    jurisdiction_id: z.number().int(),
    jurisdiction_name: z.string(),
    jurisdiction_code: z.string(),
    official_portal_url: optionalText,
    complaint_url: optionalText,
    phone_number: optionalText,
    email: optionalText,
    primary_source_name: z.string(),
    primary_source_url: z.string(),
    secondary_source_name: optionalText,
    secondary_source_url: optionalText,
    is_verified: z.boolean(),
    is_active: z.boolean().default(true),
    verified_at: optionalText,
    verification_notes: optionalText,
  })).default([]),
});

export const queryResponseSchema = z.object({
  route: z.enum(['emergency', 'legal', 'follow_up', 'authority', 'civic', 'out_of_scope', 'non_rag']),
  analysis: analysisSchema,
  emergency_response: emergencySchema.nullable().default(null),
  authority_response: authoritySchema.nullable().default(null),
  legal_answer: legalAnswerSchema.nullable().default(null),
  evidence: z.array(evidenceSchema).default([]),
  validation: z.object({
    citation_valid: z.boolean().nullable().default(null),
    claim_grounding_valid: z.boolean().nullable().default(null),
    answer_integrity_valid: z.boolean().nullable().default(null),
    citation_completeness: z.number().min(0).max(1).nullable().default(null),
  }).nullable().default(null),
  retrieval_performed: z.boolean().default(false),
  routing_reason: optionalText,
  answer_blocked: z.boolean().default(false),
  safety_reason: optionalText,
  follow_up_question: optionalText,
});

export type QueryResponse = z.infer<typeof queryResponseSchema>;
export type Evidence = z.infer<typeof evidenceSchema>;
export type QueryRequest = { query: string; jurisdiction: string | null };
