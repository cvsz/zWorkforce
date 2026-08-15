CREATE UNIQUE INDEX IF NOT EXISTS metrics_daily_brand_platform_date_idx
  ON metrics_daily(brand_id, platform, metric_date)
  WHERE publication_id IS NULL;

