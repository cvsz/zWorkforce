const { DateTime, IANAZone } = require("luxon");

function localSlotToUtc(localIso, timezone) {
  if (!IANAZone.isValidZone(timezone))
    throw new Error(`Invalid timezone: ${timezone}`);
  const requested = DateTime.fromISO(localIso, { zone: "UTC" });
  const zoned = DateTime.fromISO(localIso, { zone: timezone, setZone: true });
  if (!requested.isValid || !zoned.isValid)
    throw new Error("Invalid local time");
  if (
    zoned.year !== requested.year ||
    zoned.month !== requested.month ||
    zoned.day !== requested.day ||
    zoned.hour !== requested.hour ||
    zoned.minute !== requested.minute ||
    zoned.second !== requested.second
  ) {
    throw new Error(
      "Invalid local time in timezone (possible daylight-saving gap)",
    );
  }
  return zoned.toUTC().toISO({ suppressMilliseconds: false });
}

function recommendBestTime(rows) {
  if (!Array.isArray(rows) || rows.length === 0) return null;
  const hours = new Map();
  for (const row of rows) {
    if (
      !Number.isInteger(row.localHour) ||
      row.localHour < 0 ||
      row.localHour > 23
    )
      continue;
    const aggregate = hours.get(row.localHour) || {
      engagements: 0,
      impressions: 0,
      sampleSize: 0,
    };
    aggregate.engagements += Number(row.engagements) || 0;
    aggregate.impressions += Number(row.impressions) || 0;
    aggregate.sampleSize += 1;
    hours.set(row.localHour, aggregate);
  }
  const candidates = [...hours.entries()]
    .filter(([, value]) => value.impressions > 0)
    .map(([localHour, value]) => ({
      localHour,
      engagementRate: value.engagements / value.impressions,
      sampleSize: value.sampleSize,
    }))
    .sort(
      (a, b) =>
        b.engagementRate - a.engagementRate ||
        b.sampleSize - a.sampleSize ||
        a.localHour - b.localHour,
    );
  return candidates[0] || null;
}

module.exports = { localSlotToUtc, recommendBestTime };
