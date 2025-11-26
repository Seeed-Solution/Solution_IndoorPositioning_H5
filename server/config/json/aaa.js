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
  const inputFile = './dashboard_config.json.bk';      // 原始 JSON
  const outputFile = './data_processed.json'; // 处理后的 JSON

  const jsonObj = readJson(inputFile);
  // const processed = processData(jsonObj);
  // saveJson(outputFile, processed);

    // 统计每个地图的 范围
    for (let mapConfig of jsonObj.maps) {
        let entities = mapConfig.map.entities
        let Infinity = 50000
        let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
        for (let pointConfig of entities) {
            for (let point of pointConfig.points) {
                minX = Math.min(minX, point[0]);
                maxX = Math.max(maxX, point[0]);
                minY = Math.min(minY, point[1]);
                maxY = Math.max(maxY, point[1]);
            }
        }
        console.log(`地图: ${mapConfig.map.name}, minX: ${minX}, maxX: ${maxX}, minY: ${minY}, maxY: ${maxY}`)
    }
})();
