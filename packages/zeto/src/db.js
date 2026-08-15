const { OperationalStore } = require("./repositories/operationalStore");

let store;

function configure(pool) {
  store = new OperationalStore(pool);
  return store;
}

function current() {
  if (!store) throw new Error("PostgreSQL operational store is not configured");
  return store;
}

function facade(name) {
  return new Proxy(
    {},
    {
      get(_target, method) {
        const value = current()[name][method];
        return typeof value === "function"
          ? value.bind(current()[name])
          : value;
      },
    },
  );
}

module.exports = {
  configure,
  pages: facade("pages"),
  queue: facade("queue"),
  history: facade("history"),
  schedules: facade("schedules"),
  settings: facade("settings"),
  users: facade("users"),
  sessions: facade("sessions"),
};
