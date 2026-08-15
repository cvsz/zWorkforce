const db = require("../db");

const toCSV = (data) => {
  if (!data || data.length === 0) return "";
  const headers = Object.keys(data[0]).join(",");
  const rows = data.map((obj) =>
    Object.values(obj)
      .map((v) => `"${String(v).replace(/"/g, '""')}"`)
      .join(","),
  );
  return [headers, ...rows].join("\n");
};

const exportHistory = async (req, res) => {
  const pageId = req.headers?.["x-page-id"] || "default";
  const history = await db.history.getAll(pageId, 1000);

  const csv = toCSV(history);

  res.setHeader("Content-Type", "text/csv");
  res.setHeader(
    "Content-Disposition",
    `attachment; filename="history-${pageId}.csv"`,
  );
  return res.status(200).send(csv);
};

module.exports = { exportHistory };
