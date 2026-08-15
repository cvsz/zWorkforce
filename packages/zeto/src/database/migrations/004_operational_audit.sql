CREATE OR REPLACE FUNCTION write_operational_audit() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
  old_payload jsonb;
  new_payload jsonb;
  payload jsonb;
  resource_uuid uuid;
  request_value text;
  actor_value uuid;
BEGIN
  old_payload := CASE WHEN TG_OP IN ('UPDATE', 'DELETE') THEN to_jsonb(OLD) ELSE NULL END;
  new_payload := CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN to_jsonb(NEW) ELSE NULL END;
  payload := COALESCE(new_payload, old_payload);
  IF payload->>'id' ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$' THEN
    resource_uuid := (payload->>'id')::uuid;
  END IF;
  request_value := NULLIF(current_setting('zeto.request_id', true), '');
  IF NULLIF(current_setting('zeto.actor_id', true), '') ~* '^[0-9a-f-]{36}$' THEN
    actor_value := current_setting('zeto.actor_id', true)::uuid;
  END IF;
  INSERT INTO audit_events(actor_id, action, resource_type, resource_id, request_id, before_state, after_state)
  VALUES (
    actor_value,
    TG_TABLE_NAME || '.' || lower(TG_OP),
    TG_TABLE_NAME,
    resource_uuid,
    COALESCE(request_value, 'database-trigger'),
    old_payload,
    new_payload
  );
  RETURN COALESCE(NEW, OLD);
END;
$$;

CREATE TRIGGER app_settings_audit AFTER INSERT OR UPDATE OR DELETE ON app_settings
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
CREATE TRIGGER facebook_pages_audit AFTER INSERT OR UPDATE OR DELETE ON facebook_pages
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
CREATE TRIGGER publication_queue_audit AFTER INSERT OR UPDATE OR DELETE ON publication_queue
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
CREATE TRIGGER post_history_audit AFTER INSERT OR UPDATE OR DELETE ON post_history
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
CREATE TRIGGER operational_schedules_audit AFTER INSERT OR UPDATE OR DELETE ON operational_schedules
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
CREATE TRIGGER user_sessions_audit AFTER INSERT OR UPDATE OR DELETE ON user_sessions
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
