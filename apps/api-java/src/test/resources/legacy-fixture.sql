-- Synthetic rows in every historical table, used only in an isolated test schema.
INSERT INTO projects(id,name,slug,is_active,created_at,updated_at) VALUES
('00000000-0000-4000-8000-000000000001','Synthetic Project','synthetic',true,'2026-01-02T03:04:05.123456Z','2026-01-02T03:04:05.123456Z');
INSERT INTO applications(id,project_id,name,slug,environment,is_active,created_at,updated_at) VALUES
('00000000-0000-4000-8000-000000000002','00000000-0000-4000-8000-000000000001','Synthetic App','synthetic','local',true,now(),now());
INSERT INTO api_keys(id,application_id,key_prefix,key_hash,is_active,created_at,updated_at) VALUES
('00000000-0000-4000-8000-000000000003','00000000-0000-4000-8000-000000000002','placeholder','synthetic-unusable-hash',true,now(),now());
INSERT INTO prompt_versions(id,project_id,application_id,name,version,content,is_active,created_at,updated_at) VALUES
('00000000-0000-4000-8000-000000000004','00000000-0000-4000-8000-000000000001','00000000-0000-4000-8000-000000000002','synthetic',1,'Synthetic mock prompt',true,now(),now());
INSERT INTO model_routes(id,project_id,application_id,environment,provider,model_name,priority,is_default,is_active,created_at,updated_at) VALUES
('00000000-0000-4000-8000-000000000005','00000000-0000-4000-8000-000000000001','00000000-0000-4000-8000-000000000002','local','mock','synthetic',100,true,true,now(),now());
INSERT INTO gateway_requests(id,request_id,project_id,application_id,api_key_id,prompt_version_id,model_route_id,status,estimated_cost_usd,external_event_id,external_metadata_json,created_at,updated_at) VALUES
('00000000-0000-4000-8000-000000000006','req_synthetic_legacy','00000000-0000-4000-8000-000000000001','00000000-0000-4000-8000-000000000002','00000000-0000-4000-8000-000000000003','00000000-0000-4000-8000-000000000004','00000000-0000-4000-8000-000000000005','succeeded',1.234567,'synthetic_event','{"payload_fingerprint":"synthetic-fingerprint","metadata.retry_count":1}',now(),now());
INSERT INTO cost_records(id,gateway_request_id,project_id,application_id,provider,model_name,input_tokens,output_tokens,estimated_cost_usd,currency,created_at,updated_at) VALUES
('00000000-0000-4000-8000-000000000007','00000000-0000-4000-8000-000000000006','00000000-0000-4000-8000-000000000001','00000000-0000-4000-8000-000000000002','mock','synthetic',100,20,1.234567,'USD',now(),now());
INSERT INTO audit_logs(id,project_id,application_id,actor_type,action,resource_type,metadata_json,created_at,updated_at) VALUES
('00000000-0000-4000-8000-000000000008','00000000-0000-4000-8000-000000000001','00000000-0000-4000-8000-000000000002','system','synthetic-fixture','database','{"synthetic":true}',now(),now());
