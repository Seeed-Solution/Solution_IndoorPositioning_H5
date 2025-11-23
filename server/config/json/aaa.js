const fs = require('fs');
const path = require('path');

// 1. 读取本地 JSON 文件
function readJson(filePath) {
  const absPath = path.resolve(__dirname, filePath);
  const content = fs.readFileSync(absPath, 'utf-8');
  return JSON.parse(content);
}

// 2. 保存 JSON 文件
function saveJson(filePath, data) {
  const absPath = path.resolve(__dirname, filePath);
  fs.writeFileSync(absPath, JSON.stringify(data, null, 2), 'utf-8');
  console.log(`✅ 已保存到 ${absPath}`);
}

// 3. 示例：处理 JSON 对象
function processData(data) {
    for (let config of data.maps){
        delete config.map.entities
    }

  // 如果是普通对象，也加一个字段
  return data
}

// --- 主流程 ---
(function main() {
  const inputFile = './dashboard_config.json';      // 原始 JSON
  const outputFile = './data_processed.json'; // 处理后的 JSON

  const jsonObj = readJson(inputFile);
  const processed = processData(jsonObj);
  saveJson(outputFile, processed);
})();
