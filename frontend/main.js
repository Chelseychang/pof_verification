import { POFClient, getDecisionMessage } from './sdk/pof-sdk.js';

const $ = (id) => document.getElementById(id);

const modeRadios = document.querySelectorAll(
  'input[name="verifyMode"]'
);

modeRadios.forEach((radio) => {

  radio.addEventListener('change', () => {

    const selected = document.querySelector(
      'input[name="verifyMode"]:checked'
    ).value;

    $('demoScenarioWrapper').style.display =
      selected === 'demo'
        ? 'block'
        : 'none';
  });

});

const resultEl = $('result');
const statusBadge = $('statusBadge');

let selectedVideoFile = null;
let selectedPoiImageFile = null;

$('videoFile').addEventListener('change', (event) => {
  selectedVideoFile = event.target.files?.[0] || null;

  $('fileName').textContent = selectedVideoFile
    ? `${selectedVideoFile.name} · ${(selectedVideoFile.size / 1024 / 1024).toFixed(2)}MB`
    : '未选择视频';
});

$('poiImageFile').addEventListener('change', (event) => {
  selectedPoiImageFile = event.target.files?.[0] || null;

  $('poiImageName').textContent = selectedPoiImageFile
    ? `${selectedPoiImageFile.name} · ${(selectedPoiImageFile.size / 1024 / 1024).toFixed(2)}MB`
    : '未选择照片';
});

$('healthBtn').addEventListener('click', async () => {
  const client = new POFClient({
    baseUrl: $('apiUrl').value
  });

  showLoading('正在检查服务...');

  try {
    const data = await client.healthCheck();

    statusBadge.textContent = '服务正常';
    statusBadge.className = 'ok';

    showResult(
      'success',
      '健康检查通过',
      `服务状态：${data.status}`,
      data
    );
  } catch (error) {

  const networkErrors = [
    'Failed to fetch',
    'NetworkError',
    'Request timeout'
  ];

  const isNetworkError = networkErrors.some(
    (msg) => error.message.includes(msg)
  );

  const message = isNetworkError
    ? `${error.message}\n请确认服务地址可访问，浏览器允许跨域请求。`
    : error.message;

  showResult(
    'error',
    '提交失败',
    '健康检查失败',
    message
  );
}
});

$('verifyBtn').addEventListener('click', async () => {
  const client = new POFClient({
    baseUrl: $('apiUrl').value
  });

  showLoading('正在提交验证...');

  try {
    const result = await client.verify({
      userId: $('userId').value.trim(),
      brand: $('brand').value,
      scenario:
        document.querySelector(
          'input[name="verifyMode"]:checked'
        ).value === 'auto'
          ? 'auto'
          : $('scenario').value,
      videoFile: selectedVideoFile,
      poiImageFile: selectedPoiImageFile
    });

    const msg = getDecisionMessage(result);

    showResult(
      msg.type,
      msg.title,
      msg.message,
      result
    );
  } catch (error) {

      const networkErrors = [
        'Failed to fetch',
        'NetworkError',
        'Request timeout'
      ];

      const isNetworkError = networkErrors.some(
        (msg) => error.message.includes(msg)
      );

      const message = isNetworkError
        ? `${error.message}\n请确认服务地址可访问，浏览器允许跨域请求。`
        : error.message;

      showResult(
        'error',
        '提交失败',
        message
      );
    }
});

function showLoading(text) {
  resultEl.className = 'result loading';

  resultEl.innerHTML = `
    <h3>${escapeHtml(text)}</h3>
    <p>请稍候...</p>
  `;
}

function showResult(type, title, message, raw) {
  resultEl.className = `result ${type}`;

  const rawHtml = raw
    ? `<pre>${escapeHtml(JSON.stringify(raw, null, 2))}</pre>`
    : '';

  resultEl.innerHTML = `
    <h3>${escapeHtml(title)}</h3>
    <p>${escapeHtml(message).replace(/\n/g, '<br />')}</p>
    ${rawHtml}
  `;
}

function escapeHtml(str) {
  return String(str).replace(/[&<>'"]/g, (char) => {
    return {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      "'": '&#39;',
      '"': '&quot;'
    }[char];
  });
}