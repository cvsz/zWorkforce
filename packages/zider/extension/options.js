const gatewayInput = document.getElementById("gateway-url");
const modelInput = document.getElementById("default-model");
const saveBtn = document.getElementById("save-btn");
const saveStatus = document.getElementById("save-status");

// Load stored settings
chrome.storage.sync.get(["ziderGatewayUrl", "ziderDefaultModel"], (res) => {
  if (res.ziderGatewayUrl) gatewayInput.value = res.ziderGatewayUrl;
  if (res.ziderDefaultModel) modelInput.value = res.ziderDefaultModel;
});

saveBtn.addEventListener("click", () => {
  chrome.storage.sync.set({
    ziderGatewayUrl: gatewayInput.value.trim(),
    ziderDefaultModel: modelInput.value
  }, () => {
    saveStatus.textContent = "Saved successfully!";
    setTimeout(() => { saveStatus.textContent = ""; }, 2500);
  });
});
