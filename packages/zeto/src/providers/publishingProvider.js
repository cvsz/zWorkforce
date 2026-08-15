class PublishingProvider {
  capabilities() {
    throw new Error("capabilities() must be implemented");
  }

  async validateAuth() {
    throw new Error("validateAuth() must be implemented");
  }

  async publish() {
    throw new Error("publish() must be implemented");
  }

  async delete() {
    throw new Error("delete() must be implemented");
  }

  async status() {
    throw new Error("status() must be implemented");
  }

  async metrics() {
    throw new Error("metrics() must be implemented");
  }
}

module.exports = { PublishingProvider };
