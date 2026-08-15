class ObjectStorage {
  async put(_key, _body, _options) {
    throw new Error("Not implemented");
  }

  async get(_key) {
    throw new Error("Not implemented");
  }

  async delete(_key) {
    throw new Error("Not implemented");
  }
}

module.exports = { ObjectStorage };
