/* Racing Bois offline LAN address display. No fetch, CDN, storage or telemetry. */
"use strict";
(function () {
  const data = JSON.parse(document.getElementById("address-data").textContent);
  const target = document.getElementById("addresses");
  const local = document.getElementById("local");
  local.href = data.localUrl;
  local.textContent = data.localUrl;
  if (!data.addresses.length) {
    const message = document.createElement("p");
    message.className = "empty";
    message.textContent = "Chưa tìm thấy địa chỉ LAN trên card mạng vật lý. Hãy kết nối Wi-Fi hoặc cáp mạng rồi chạy lại show-lan-addresses.bat. VPN và địa chỉ tự gán 169.254.x.x được bỏ qua.";
    target.appendChild(message);
  }
  for (const item of data.addresses) {
    const article = document.createElement("article");
    const heading = document.createElement("h2");
    heading.textContent = item.adapter;
    const link = document.createElement("a");
    link.className = "url";
    link.href = item.url;
    link.textContent = item.url;
    const box = document.createElement("div");
    box.className = "qr";
    box.setAttribute("aria-label", "Mã QR: " + item.url);
    const qr = qrcodegen.QrCode.encodeText(item.url, qrcodegen.QrCode.Ecc.MEDIUM);
    const border = 4, size = qr.size + border * 2;
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 " + size + " " + size);
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", "Quét để mở " + item.url);
    svg.setAttribute("shape-rendering", "crispEdges");
    const background = document.createElementNS(svg.namespaceURI, "rect");
    background.setAttribute("width", "100%"); background.setAttribute("height", "100%"); background.setAttribute("fill", "#fff");
    svg.appendChild(background);
    let pathData = "";
    for (let y = 0; y < qr.size; y++) for (let x = 0; x < qr.size; x++)
      if (qr.getModule(x, y)) pathData += "M" + (x + border) + "," + (y + border) + "h1v1h-1z";
    const path = document.createElementNS(svg.namespaceURI, "path");
    path.setAttribute("d", pathData); path.setAttribute("fill", "#000"); svg.appendChild(path);
    box.appendChild(svg); article.append(heading, box, link); target.appendChild(article);
  }
}());
