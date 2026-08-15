CREATE TRIGGER provider_credentials_audit AFTER INSERT OR UPDATE OR DELETE ON provider_credentials
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
CREATE TRIGGER posts_audit AFTER INSERT OR UPDATE OR DELETE ON posts
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
CREATE TRIGGER schedules_audit AFTER INSERT OR UPDATE OR DELETE ON schedules
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
CREATE TRIGGER publications_audit AFTER INSERT OR UPDATE OR DELETE ON publications
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
CREATE TRIGGER metrics_daily_audit AFTER INSERT OR UPDATE OR DELETE ON metrics_daily
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
CREATE TRIGGER mentions_audit AFTER INSERT OR UPDATE OR DELETE ON mentions
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
CREATE TRIGGER sentiment_scores_audit AFTER INSERT OR UPDATE OR DELETE ON sentiment_scores
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
CREATE TRIGGER mention_escalations_audit AFTER INSERT OR UPDATE OR DELETE ON mention_escalations
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
CREATE TRIGGER competitors_audit AFTER INSERT OR UPDATE OR DELETE ON competitors
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
CREATE TRIGGER workflows_audit AFTER INSERT OR UPDATE OR DELETE ON workflows
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
CREATE TRIGGER workflow_runs_audit AFTER INSERT OR UPDATE OR DELETE ON workflow_runs
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
CREATE TRIGGER workflow_steps_audit AFTER INSERT OR UPDATE OR DELETE ON workflow_steps
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
CREATE TRIGGER approvals_audit AFTER INSERT ON approvals
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
CREATE TRIGGER model_routes_audit AFTER INSERT OR UPDATE OR DELETE ON model_routes
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
CREATE TRIGGER cost_events_audit AFTER INSERT OR UPDATE OR DELETE ON cost_events
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
CREATE TRIGGER alerts_audit AFTER INSERT OR UPDATE OR DELETE ON alerts
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
CREATE TRIGGER jobs_audit AFTER INSERT OR UPDATE OR DELETE ON jobs
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
